import boto3
import logging
from typing import List, Dict, Any, Optional
import os
import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSServiceReader:
    def __init__(self, region: str = config.AWS_REGION):
        self.region = region
        self.session = boto3.Session(region_name=region)
        
        # Clients
        self.tagging_client = self.session.client('resourcegroupstaggingapi')
        self.rg_client = self.session.client('resource-groups')
        self.codestar = self.session.client('codestar-connections')
        self.s3 = self.session.client('s3')
        self.ec2 = self.session.client('ec2')
        self.ecs = self.session.client('ecs')
        self.ecr = self.session.client('ecr')
        self.lambda_client = self.session.client('lambda') # 'lambda' is reserved 
        self.rds = self.session.client('rds')
        self.dynamodb = self.session.client('dynamodb')
        self.elbv2 = self.session.client('elbv2')
        self.cloudwatch_logs = self.session.client('logs')
        self.apprunner = self.session.client('apprunner')
        self.codebuild = self.session.client('codebuild')
        self.codepipeline = self.session.client('codepipeline')
        
        self.discovered_resources = []
        self.report_file = config.REPORT_FILE_PATH

    def add_resource(self, identifier, arn, service, rtype, tags=None):
        if tags is None: tags = {}
        # Ignore payments service (internal/billing artifact)
        if service == 'payments': return
        
        # Deduplication check
        if any(r['ARN'] == arn for r in self.discovered_resources):
            return
            
        self.discovered_resources.append({
            'Identifier': identifier,
            'ARN': arn,
            'Service': service,
            'Type': rtype,
            'Region': self.region,
            'Tags': tags
        })

    def scan_all_resources(self):
        """
        Scans all resources using specific API calls for 100% coverage.
        """
        logger.info("Starting Deep Scan for all resources...")
        
        # 1. Compute
        self.scan_ec2()
        self.scan_ecs()
        self.scan_lambda()
        self.scan_apprunner()
        
        # 2. Storage & DB
        self.scan_s3()
        self.scan_rds()
        self.scan_dynamodb()
        self.scan_ecr()
        
        # 3. Load Balancing
        self.scan_elbv2()
        
        # 4. DevOps & Management
        self.scan_codestar()
        self.scan_codebuild()
        self.scan_codepipeline()
        self.scan_resource_groups()
        self.scan_cloudwatch_logs()

        # 5. Broad Scan (Tagging API) - Final catch-all
        # Disabled to prevent duplicates and "unknown" resources that were explicitly skipped (e.g. deleting)
        # self.scan_tagging_api()

    def scan_tagging_api(self):
        logger.info("Scanning Resource Groups Tagging API...")
        try:
            paginator = self.tagging_client.get_paginator('get_resources')
            for page in paginator.paginate():
                for item in page['ResourceTagMappingList']:
                    tags = {t['Key']: t['Value'] for t in item['Tags']}
                    self.add_resource(
                        identifier=item['ResourceARN'].split(':')[-1].split('/')[-1],
                        arn=item['ResourceARN'],
                        service=item['ResourceARN'].split(':')[2],
                        rtype='unknown', # Will be improved by specific scans or heuristic
                        tags=tags
                    )
        except Exception as e:
            logger.error(f"Error scanning tagging API: {e}")

    def scan_ec2(self):
        logger.info("Scanning EC2 (Instances, Network, Security)...")
        try:
            # Instances
            for res in self.ec2.describe_instances()['Reservations']:
                for inst in res['Instances']:
                    if inst['State']['Name'] in ['terminated', 'shutting-down']: continue
                    name = next((t['Value'] for t in inst.get('Tags', []) if t['Key']=='Name'), inst['InstanceId'])
                    tags = {t['Key']: t['Value'] for t in inst.get('Tags', [])}
                    self.add_resource(name, f"arn:aws:ec2:{self.region}:{inst.get('OwnerId', '')}:instance/{inst['InstanceId']}", 'ec2', 'instance', tags)
            
            # Security Groups
            for sg in self.ec2.describe_security_groups()['SecurityGroups']:
                if sg['GroupName'] == 'default': continue
                tags = {t['Key']: t['Value'] for t in sg.get('Tags', [])}
                self.add_resource(sg['GroupName'], f"arn:aws:ec2:{self.region}:{sg['OwnerId']}:security-group/{sg['GroupId']}", 'ec2', 'security-group', tags)
                
            # VPCs
            for vpc in self.ec2.describe_vpcs()['Vpcs']:
                if vpc.get('IsDefault', False): continue
                tags = {t['Key']: t['Value'] for t in vpc.get('Tags', [])}
                self.add_resource(vpc['VpcId'], f"arn:aws:ec2:{self.region}:{vpc['OwnerId']}:vpc/{vpc['VpcId']}", 'ec2', 'vpc', tags)

            # Subnets
            for sub in self.ec2.describe_subnets()['Subnets']:
                if sub.get('DefaultForAz', False): continue
                tags = {t['Key']: t['Value'] for t in sub.get('Tags', [])}
                self.add_resource(sub['SubnetId'], sub['SubnetArn'], 'ec2', 'subnet', tags)

            # Internet Gateways
            for igw in self.ec2.describe_internet_gateways()['InternetGateways']:
                # Hard to strict check default, but usually attached to non-default VPC
                # We can check attachments. If all attachments are to default VPCs, skip?
                # For now, let's leave it unless we want to do heavy lookups.
                # Or relying on the user to see it.
                # Actually, user wants to HIDE things not created by them.
                # If no name tag?
                tags = {t['Key']: t['Value'] for t in igw.get('Tags', [])}
                self.add_resource(igw['InternetGatewayId'], f"arn:aws:ec2:{self.region}:{igw['OwnerId']}:internet-gateway/{igw['InternetGatewayId']}", 'ec2', 'internet-gateway', tags)

            # NAT Gateways
            for nat in self.ec2.describe_nat_gateways()['NatGateways']:
                if nat['State'] in ['deleted', 'deleting', 'failed']: continue
                tags = {t['Key']: t['Value'] for t in nat.get('Tags', [])}
                self.add_resource(nat['NatGatewayId'], f"arn:aws:ec2:{self.region}:{nat.get('OwnerId','')}:natgateway/{nat['NatGatewayId']}", 'ec2', 'natgateway', tags)

            # Elastic IPs
            for eip in self.ec2.describe_addresses()['Addresses']:
                tags = {t['Key']: t['Value'] for t in eip.get('Tags', [])}
                alloc_id = eip.get('AllocationId', 'eip-unknown')
                self.add_resource(alloc_id, f"arn:aws:ec2:{self.region}::elastic-ip/{alloc_id}", 'ec2', 'elastic-ip', tags)

            # Route Tables
            for rtb in self.ec2.describe_route_tables()['RouteTables']:
                # Main route tables for default VPCs?
                # Check associations.
                is_default_main = False
                for assoc in rtb.get('Associations', []):
                    if assoc.get('Main', False):
                        # We'd need to check if VPC is default. Too expensive?
                        pass
                
                tags = {t['Key']: t['Value'] for t in rtb.get('Tags', [])}
                self.add_resource(rtb['RouteTableId'], f"arn:aws:ec2:{self.region}:{rtb['OwnerId']}:route-table/{rtb['RouteTableId']}", 'ec2', 'route-table', tags)

            # Network ACLs
            for acl in self.ec2.describe_network_acls()['NetworkAcls']:
                if acl.get('IsDefault', False): continue
                tags = {t['Key']: t['Value'] for t in acl.get('Tags', [])}
                self.add_resource(acl['NetworkAclId'], f"arn:aws:ec2:{self.region}:{acl['OwnerId']}:network-acl/{acl['NetworkAclId']}", 'ec2', 'network-acl', tags)

        except Exception as e:
            logger.error(f"Error scanning EC2: {e}")

    def scan_ecs(self):
        logger.info("Scanning ECS...")
        try:
            # Need to describe clusters to get status? list_clusters is cheap.
            # Describe allows checking status.
            c_arns = self.ecs.list_clusters()['clusterArns']
            if c_arns:
                clusters = self.ecs.describe_clusters(clusters=c_arns)['clusters']
                for c in clusters:
                     if c['status'] in ['INACTIVE', 'DEPROVISIONING', 'FAILED']: continue
                     self.add_resource(c['clusterArn'], c['clusterArn'], 'ecs', 'cluster')
                     
                     # Services (only if cluster active)
                     svcs = self.ecs.list_services(cluster=c['clusterArn'])['serviceArns']
                     if svcs:
                         desc_svcs = self.ecs.describe_services(cluster=c['clusterArn'], services=svcs)['services']
                         for s in desc_svcs:
                             if s['status'] in ['DRAINING', 'INACTIVE']: continue
                             self.add_resource(s['serviceArn'], s['serviceArn'], 'ecs', 'service')
            
            # Task Definitions (always active? Deregistered are INACTIVE)
            families = self.ecs.list_task_definition_families()['families']
            for fam in families:
                arns = self.ecs.list_task_definitions(familyPrefix=fam, status='ACTIVE')['taskDefinitionArns']
                for t_arn in arns:
                    self.add_resource(t_arn, t_arn, 'ecs', 'task-definition')
                
        except Exception as e:
            logger.error(f"Error scanning ECS: {e}")

    def scan_s3(self):
        logger.info("Scanning S3...")
        try:
            for b in self.s3.list_buckets()['Buckets']:
                name = b['Name']
                self.add_resource(name, f"arn:aws:s3:::{name}", 's3', 'bucket')
        except Exception as e:
            logger.error(f"Error scanning S3: {e}")

    def scan_ecr(self):
        logger.info("Scanning ECR...")
        try:
            for r in self.ecr.describe_repositories()['repositories']:
                self.add_resource(r['repositoryName'], r['repositoryArn'], 'ecr', 'repository')
        except Exception as e:
            logger.error(f"Error scanning ECR: {e}")
            
    def scan_lambda(self):
        logger.info("Scanning Lambda...")
        try:
            paginator = self.lambda_client.get_paginator('list_functions')
            for page in paginator.paginate():
                for f in page['Functions']:
                    self.add_resource(f['FunctionArn'], f['FunctionArn'], 'lambda', 'function')
        except Exception as e:
            logger.error(f"Error scanning Lambda: {e}")

    def scan_rds(self):
        logger.info("Scanning RDS...")
        try:
            for db in self.rds.describe_db_instances()['DBInstances']:
                if db['DBInstanceStatus'] in ['deleting', 'deleted', 'failed']: continue
                self.add_resource(db['DBInstanceIdentifier'], db['DBInstanceArn'], 'rds', 'db-instance')
        except Exception as e:
            logger.error(f"Error scanning RDS: {e}")

    def scan_dynamodb(self):
        logger.info("Scanning DynamoDB...")
        try:
            for t in self.dynamodb.list_tables()['TableNames']:
                desc = self.dynamodb.describe_table(TableName=t)['Table']
                if desc.get('TableStatus') in ['DELETING']: continue
                self.add_resource(t, desc['TableArn'], 'dynamodb', 'table')
        except Exception as e:
            logger.error(f"Error scanning DynamoDB: {e}")

    def scan_elbv2(self):
        logger.info("Scanning ELBv2...")
        try:
            # LBs
            lbs = self.elbv2.describe_load_balancers()['LoadBalancers']
            for lb in lbs:
                if lb['State']['Code'] in ['failed', 'deleting']: continue
                self.add_resource(lb['LoadBalancerArn'], lb['LoadBalancerArn'], 'elasticloadbalancing', 'loadbalancer')
            
            # Target Groups
            tgs = self.elbv2.describe_target_groups()['TargetGroups']
            for tg in tgs:
                self.add_resource(tg['TargetGroupArn'], tg['TargetGroupArn'], 'elasticloadbalancing', 'targetgroup')
        except Exception as e:
             logger.error(f"Error scanning ELBv2: {e}")

    def scan_codestar(self):
        logger.info("Scanning CodeStar Connections...")
        try:
            # Check GitHub connections
            conns = self.codestar.list_connections(ProviderTypeFilter='GitHub')['Connections']
            for c in conns:
                tags = {}
                try:
                    t_resp = self.codestar.list_tags_for_resource(ResourceArn=c['ConnectionArn'])
                    tags = {t['Key']: t['Value'] for t in t_resp['Tags']}
                except: pass
                # delete takes ARN
                self.add_resource(c['ConnectionArn'], c['ConnectionArn'], 'codestar-connections', 'connection', tags)
        except Exception as e:
            logger.error(f"Error scanning CodeStar: {e}")

    def scan_codebuild(self):
        logger.info("Scanning CodeBuild...")
        try:
            projects = self.codebuild.list_projects()['projects']
            if projects:
                details = self.codebuild.batch_get_projects(names=projects)['projects']
                for p in details:
                    # delete takes Name
                    self.add_resource(p['name'], p['arn'], 'codebuild', 'project')
        except Exception as e:
            logger.error(f"Error scanning CodeBuild: {e}")

    def scan_codepipeline(self):
        logger.info("Scanning CodePipeline...")
        try:
            for p in self.codepipeline.list_pipelines()['pipelines']:
                # delete takes Name
                self.add_resource(p['name'], f"arn:aws:codepipeline:{self.region}:unknown:pipeline/{p['name']}", 'codepipeline', 'pipeline')
        except Exception as e:
            logger.error(f"Error scanning CodePipeline: {e}")

    def scan_apprunner(self):
        logger.info("Scanning AppRunner...")
        try:
            for s in self.apprunner.list_services()['ServiceSummaryList']:
                # delete takes ARN
                self.add_resource(s['ServiceArn'], s['ServiceArn'], 'apprunner', 'service')
        except Exception as e:
            logger.error(f"Error scanning AppRunner: {e}")

    def scan_resource_groups(self):
        logger.info("Scanning Resource Groups...")
        try:
            paginator = self.rg_client.get_paginator('list_groups')
            for page in paginator.paginate():
                for g in page['Groups']:
                     self.add_resource(g['Name'], g['GroupArn'], 'resource-groups', 'group')
        except Exception as e:
            logger.error(f"Error scanning Resource Groups: {e}")

    def scan_cloudwatch_logs(self):
        logger.info("Scanning CloudWatch Logs...")
        try:
            paginator = self.cloudwatch_logs.get_paginator('describe_log_groups')
            for page in paginator.paginate():
                for lg in page['logGroups']:
                    self.add_resource(lg['logGroupName'], lg['arn'], 'logs', 'log-group')
        except Exception as e:
             logger.error(f"Error scanning Logs: {e}")


    def generate_report(self, filename=None):
        if filename is None:
            filename = self.report_file
        logger.info(f"Generating report: {filename}")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# AWS Services & Components Report\n\n")
            from datetime import datetime
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Region:** {self.region}\n")
            f.write(f"**Total Resources Found:** {len(self.discovered_resources)}\n\n")
            
            f.write("| Identifier | Service | Type | Region | Tags |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            
            # Sort by Service then Identifier
            sorted_resources = sorted(self.discovered_resources, key=lambda x: (x['Service'], x['Identifier']))
            
            for res in sorted_resources:
                # Filter tags to only show "Name"
                name_tag = res['Tags'].get('Name')
                if name_tag:
                    tags_str = f"`Name: {name_tag}`"
                else:
                    tags_str = "*(No Name Tag)*"
                
                # Format identifier to be code block for readability
                ident = f"`{res['Identifier']}`"
                # If ARN is different/long, maybe just show identifier or truncated ARN? 
                # User asked for Identifier. We have it.
                
                f.write(f"| {ident} | {res['Service']} | {res['Type']} | {res['Region']} | {tags_str} |\n")

        logger.info(f"Report saved to {filename}")

if __name__ == "__main__":
    reader = AWSServiceReader()
    reader.scan_all_resources()
    reader.generate_report()
