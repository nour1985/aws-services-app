import boto3
import argparse
import logging
from typing import List, Dict, Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def apply_naming_tags(vpc_name: str, region: str = 'us-east-1', dry_run: bool = True):
    session = boto3.Session(region_name=region)
    ec2 = session.client('ec2')
    ec2_resource = session.resource('ec2')

    logger.info(f"Applying naming tags for VPC: {vpc_name} (Dry Run: {dry_run})")

    try:
        # 1. Find VPC by Name
        vpcs = list(ec2_resource.vpcs.filter(Filters=[{'Name': 'tag:Name', 'Values': [vpc_name]}]))
        
        if not vpcs:
            logger.error(f"VPC with name '{vpc_name}' not found!")
            return
        
        vpc = vpcs[0]
        vpc_id = vpc.id
        logger.info(f"Found VPC: {vpc_id}")

        # Helper to tag
        def tag_resource(resource_id, new_name):
            if dry_run:
                logger.info(f"[DRY RUN] Would rename {resource_id} -> {new_name}")
            else:
                try:
                    ec2.create_tags(Resources=[resource_id], Tags=[{'Key': 'Name', 'Value': new_name}])
                    logger.info(f"Renamed {resource_id} -> {new_name}")
                except ClientError as e:
                    logger.error(f"Failed to tag {resource_id}: {e}")

        # 2. Internet Gateway
        igws = list(vpc.internet_gateways.all())
        for igw in igws:
            new_name = f"{vpc_name}-igw"
            tag_resource(igw.id, new_name)

        # 3. NAT Gateways
        # VPC resource doesn't have nat_gateways collection directly, use client
        nats = ec2.describe_nat_gateways(Filter=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NatGateways']
        active_nats = [n for n in nats if n['State'] != 'deleted']
        
        for i, nat in enumerate(active_nats):
            # If multiple NATs, could append index, but usually 1 per AZ. 
            # For simplicity, if 1 use simple name, else append index.
            if len(active_nats) > 1:
                new_name = f"{vpc_name}-nat-{i+1}"
            else:
                new_name = f"{vpc_name}-nat"
            
            tag_resource(nat['NatGatewayId'], new_name)

        # 4. Route Tables
        # Logic: Check routes. If 0.0.0.0/0 -> igw, it's PUBLIC. Else PRIVATE.
        route_tables = list(vpc.route_tables.all())
        
        public_count = 0
        private_count = 0
        
        # Pre-scan to count for indexing if needed (though usually we name them uniquely if we can)
        # Terraform module usually creates one public, one private per AZ or one private total?
        # Let's just create generic names or try to be specific.
        
        # Better approach:
        # If Main -> Main
        # If Public -> Public
        # If Private -> Private
        
        for rt in route_tables:
            is_public = False
            for route in rt.routes:
                if route.destination_cidr_block == '0.0.0.0/0':
                    if route.gateway_id and route.gateway_id.startswith('igw-'):
                        is_public = True
                        break
            
            # Determine Name
            # We need to be careful not to overwrite if they are already distinct (diff AZs).
            # But the requirement is to standardize.
            
            # Use logic: {vpc_name}-{public|private}-rt
            # If multiple, AWS console might show same name multiple times, which is confusing.
            # Let's verify existing tags to see if we can preserve any uniqueness? 
            # Or just append unique ID suffix if we strictly have to?
            # Terraform module "public_route_table_tags" applies to ALL public RTs.
            
            suffix = "private-rt"
            if is_public:
                suffix = "public-rt"
            
            new_name = f"{vpc_name}-{suffix}"
            
            # Just simply name them. If duplicate names occur, that's what the TF module would do too.
            tag_resource(rt.id, new_name)

    except ClientError as e:
        logger.error(f"AWS Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Apply standard naming tags to VPC resources.')
    parser.add_argument('--vpc-name', required=True, help='The Name tag of the VPC')
    parser.add_argument('--region', default='us-east-1', help='AWS Region')
    parser.add_argument('--force', action='store_true', help='Execute tagging (disable dry-run)')

    args = parser.parse_args()

    apply_naming_tags(args.vpc_name, args.region, dry_run=not args.force)
