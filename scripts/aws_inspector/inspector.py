import boto3
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSResourceInspector:
    def __init__(self, region: str, dry_run: bool = True):
        self.region = region
        self.dry_run = dry_run
        self.session = boto3.Session(region_name=region)
        self.rg_client = self.session.client('resource-groups')
        self.tagging_client = self.session.client('resourcegroupstaggingapi')
        self.cw_client = self.session.client('cloudwatch')
        self.discovered_resources = []

    def get_group_query(self, group_name: str) -> str:
        """Retrieves the Tag filters from a Resource Group definition if possible."""
        try:
            response = self.rg_client.get_group_query(GroupName=group_name)
            return response.get('GroupQuery', {}).get('ResourceQuery', {}).get('Query')
        except Exception as e:
            logger.error(f"Error getting group query for {group_name}: {e}")
            return None

    def scan_resource_group(self, group_arn_or_name: str):
        """
        Scans for resources belonging to a specific Resource Group.
        If it's an ARN, we extract the name.
        """
        logger.info(f"Scanning Resource Group: {group_arn_or_name}")
        
        # resource-groups API often works with names, but let's handle ARNs
        if "arn:aws:resource-groups" in group_arn_or_name:
            group_name = group_arn_or_name.split("/")[-1]
        else:
            group_name = group_arn_or_name

        # Strategy 1: ListGroupResources
        # This is the most direct way to get resources in a group
        try:
            paginator = self.rg_client.get_paginator('list_group_resources')
            for page in paginator.paginate(GroupName=group_name):
                for res in page['Resources']:
                    self.discovered_resources.append({
                        'Arn': res['Identifier']['ResourceArn'],
                        'Type': res['Identifier']['ResourceType'],
                        'Status': res.get('Status', {}).get('Name', 'Unknown')
                    })
            logger.info(f"Found {len(self.discovered_resources)} resources in group {group_name}")
        except Exception as e:
            logger.error(f"Failed to list group resources: {e}")

    def enrich_resource_data(self):
        """
        Fetches tags and details for discovered resources to help with assessment.
        """
        if not self.discovered_resources:
            return

        # We can use get_resources logic from tagging API to get tags for these ARNs
        # Batched into 100s if needed, or just iterate one by one if list is small. 
        # For efficiency, let's use get_resources with ResourceARNList
        
        arns = [r['Arn'] for r in self.discovered_resources]
        
        # Split into chunks of 100 for get_resources
        chunk_size = 100
        for i in range(0, len(arns), chunk_size):
            chunk = arns[i:i + chunk_size]
            try:
                response = self.tagging_client.get_resources(ResourceARNList=chunk)
                for item in response['ResourceTagMappingList']:
                    arn = item['ResourceARN']
                    # efficient update
                    for r in self.discovered_resources:
                        if r['Arn'] == arn:
                            r['Tags'] = {t['Key']: t['Value'] for t in item['Tags']}
                            break
            except Exception as e:
                logger.error(f"Error enriching resources: {e}")

    def get_cw_metric_sum(self, namespace, metric_name, dimensions, days=7):
        """
        Gets the Sum of a metric over the last N days.
        """
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        end_time = datetime.now(timezone.utc)
        
        try:
            response = self.cw_client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=days * 86400, # Single datapoint for the whole period
                Statistics=['Sum']
            )
            datapoints = response.get('Datapoints', [])
            if datapoints:
                return datapoints[0]['Sum']
            return 0.0
        except Exception as e:
            logger.warning(f"Failed to get metric {metric_name}: {e}")
            return None

    def assess_relevance(self, active_project_tag: str = None) -> List[Dict]:
        """
        Analyzes resources to decide if they should be kept or deleted using specific usage metrics.
        """
        logger.info("Assessing resource relevance using CloudWatch metrics (7-day window)...")
        results = []
        
        # Helper: Group Task Definitions (Keep Logic)
        task_def_families = {}
        for r in self.discovered_resources:
            if r['Type'] == 'AWS::ECS::TaskDefinition':
                arn = r['Arn']
                try:
                    family_revision = arn.split('/')[-1]
                    family, revision = family_revision.split(':')
                    if family not in task_def_families:
                        task_def_families[family] = []
                    task_def_families[family].append({'arn': arn, 'rev': int(revision), 'resource': r})
                except:
                    continue

        stale_task_arns = set()
        for family, items in task_def_families.items():
            items.sort(key=lambda x: x['rev'], reverse=True)
            for item in items[2:]:
                stale_task_arns.add(item['arn'])

        # Check EIP associations
        unattached_eips = set()
        eip_resources = [r for r in self.discovered_resources if r['Type'] == 'AWS::EC2::EIP']
        if eip_resources:
            try:
                ec2 = self.session.client('ec2')
                addresses = ec2.describe_addresses()['Addresses']
                for addr in addresses:
                    if 'AssociationId' not in addr:
                        alloc_id = addr['AllocationId']
                        for r in eip_resources:
                            if alloc_id in r['Arn']:
                                unattached_eips.add(r['Arn'])
            except Exception as e:
                logger.error(f"Failed to check EIPs: {e}")

        for resource in self.discovered_resources:
            arn = resource['Arn']
            res_type = resource['Type']
            tags = resource.get('Tags', {})
            
            # Default to KEEP for safety
            relevance = "KEEP"
            justification = "Core Infrastructure / Active"

            # --- Heuristics ---

            # 1. NAT Gateway (Active Connections)
            if res_type == 'AWS::EC2::NatGateway':
                # ARN: arn:aws:ec2:region:account:natgateway/nat-xxxx
                nat_id = arn.split('/')[-1]
                connections = self.get_cw_metric_sum(
                    'AWS/NATGateway', 'ConnectionEstablishedCount', [{'Name': 'NatGatewayId', 'Value': nat_id}]
                )
                if connections is not None and connections == 0:
                    relevance = "DELETE"
                    justification = "Unused NAT Gateway (0 connections in 7 days)"
                elif connections is not None:
                    justification = f"Active NAT Gateway ({int(connections)} connections/7d)"

            # 2. Application Load Balancer (Request Count)
            elif res_type == 'AWS::ElasticLoadBalancingV2::LoadBalancer' and '/app/' in arn:
                # ARN: arn:aws:elasticloadbalancing:region:account:loadbalancer/app/name/id
                # Dimension needs "LoadBalancer" = "app/name/id"
                lb_dim_value = "/".join(arn.split(':')[-1].split('/')[1:]) # app/name/id
                requests = self.get_cw_metric_sum(
                    'AWS/ApplicationELB', 'RequestCount', [{'Name': 'LoadBalancer', 'Value': lb_dim_value}]
                )
                if requests is not None and requests == 0:
                    relevance = "DELETE"
                    justification = "Unused ALB (0 requests in 7 days)"
                elif requests is not None:
                    justification = f"Active ALB ({int(requests)} requests/7d)"

            # 3. ECS Task Definitions (Stale Revisions)
            elif res_type == 'AWS::ECS::TaskDefinition':
                if arn in stale_task_arns:
                    relevance = "DELETE"
                    justification = "Old Task Definition revision (kept last 2)"
                else:
                    justification = "Recent Task Definition revision"

            # 4. Unassociated EIPs
            elif res_type == 'AWS::EC2::EIP':
                if arn in unattached_eips:
                    relevance = "DELETE"
                    justification = "Unassociated Elastic IP"
                else:
                    justification = "EIP is attached to a resource"
            
            # 5. RDS Instances (DatabaseConnections)
            # (Assuming we might discover 'AWS::RDS::DBInstance')
            elif res_type == 'AWS::RDS::DBInstance':
                db_id = arn.split(':')[-1]
                conns = self.get_cw_metric_sum(
                    'AWS/RDS', 'DatabaseConnections', [{'Name': 'DBInstanceIdentifier', 'Value': db_id}]
                )
                if conns is not None and conns == 0:
                     relevance = "DELETE"
                     justification = "Unused RDS (0 connections in 7 days)"

            # 6. Explicit Active Tag (Overrides everything to KEEP)
            if active_project_tag:
                 if active_project_tag in tags.values() or active_project_tag in tags.keys():
                    relevance = "KEEP"
                    justification = f"Matched active identifier '{active_project_tag}'"

            resource['Relevance'] = relevance
            resource['Justification'] = justification
            results.append(resource)
        
        return results

    def cleanup(self, resources: List[Dict]):
        """
        Deletes resources marked for DELETE.
        """
        logger.info("Starting cleanup process...")
        for res in resources:
            if res['Relevance'] == 'DELETE':
                self.delete_resource(res)
    
    def delete_resource(self, resource: Dict):
        arn = resource['Arn']
        res_type = resource['Type']

        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete {res_type} - {arn}")
            return

        logger.info(f"Deleting {res_type} - {arn}")
        
        try:
            if "s3" in res_type:
                self.delete_s3_bucket(arn)
            elif "ec2" in res_type and "instance" in res_type:
                self.delete_ec2_instance(arn)
            elif "ecs" in res_type and "task-definition" in res_type:
                self.delete_task_definition(arn)
            elif "ec2" in res_type and "elastic-ip" in res_type:
                self.delete_eip(arn)
            else:
                logger.warning(f"No specific deletion handler for type {res_type}. Skipping {arn}")
        except Exception as e:
            logger.error(f"Failed to delete {arn}: {e}")

    def delete_task_definition(self, arn):
        ecs = self.session.client('ecs')
        ecs.deregister_task_definition(taskDefinition=arn)
        logger.info(f"Deregistered Task Definition {arn}")

    def delete_eip(self, arn):
        # Extract allocation ID
        alloc_id = arn.split('/')[-1]
        ec2 = self.session.client('ec2')
        ec2.release_address(AllocationId=alloc_id)
        logger.info(f"Released EIP {alloc_id}")

    def delete_s3_bucket(self, arn):
        bucket_name = arn.split(":::")[1]
        s3 = self.session.resource('s3')
        bucket = s3.Bucket(bucket_name)
        # Empty bucket first
        bucket.objects.all().delete()
        bucket.delete()
        logger.info(f"Deleted S3 bucket {bucket_name}")

    def delete_ec2_instance(self, arn):
        instance_id = arn.split("/")[-1]
        ec2 = self.session.client('ec2')
        ec2.terminate_instances(InstanceIds=[instance_id])
        logger.info(f"Terminated EC2 instance {instance_id}")

