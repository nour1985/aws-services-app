import boto3
import logging
from botocore.exceptions import ClientError
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_vpc_details(region: str = 'us-east-1'):
    session = boto3.Session(region_name=region)
    ec2 = session.client('ec2')

    try:
        # Get all VPCs
        vpcs_response = ec2.describe_vpcs()
        vpcs = vpcs_response.get('Vpcs', [])
        
        logger.info(f"Found {len(vpcs)} VPCs in {region}")
        logger.info("-" * 80)
        logger.info(f"{'VPC ID':<20} | {'Name':<25} | {'CIDR':<15} | {'Is Default':<10} | {'Status'}")
        logger.info("-" * 80)

        unused_candidates = []

        for vpc in vpcs:
            vpc_id = vpc['VpcId']
            is_default = vpc['IsDefault']
            cidr = vpc['CidrBlock']
            
            # Get Name tag
            name = "N/A"
            if 'Tags' in vpc:
                for tag in vpc['Tags']:
                    if tag['Key'] == 'Name':
                        name = tag['Value']

            # Check for active resources
            
            # 1. Network Interfaces (ENIs)
            # ENIs are attached to EC2, RDS, ELB, Lambda, NAT Gateways, etc.
            # This is the single best indicator of "active usage".
            enis = ec2.describe_network_interfaces(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NetworkInterfaces']
            eni_count = len(enis)

            # 2. Subnets
            subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']
            subnet_count = len(subnets)

            # 3. Internet Gateways
            igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])['InternetGateways']
            igw_count = len(igws)
            
            # 4. NAT Gateways
            nat_gateways = ec2.describe_nat_gateways(Filter=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NatGateways']
            active_nats = [n for n in nat_gateways if n['State'] != 'deleted']
            nat_count = len(active_nats)

            # 5. Route Tables
            rts = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['RouteTables']
            rt_count = len(rts)

            # Determine if unused
            # Basic heuristic: No ENIs typically means nothing is running inside.
            # However, it might have structural components (subnets, gateways) but no compute.
            status = "ACTIVE"
            details = []
            
            if eni_count == 0:
                status = "LIKELY UNUSED"
                details.append("No Active Interfaces")
            else:
                details.append(f"{eni_count} ENIs")
                
            if active_nats:
                details.append(f"{nat_count} NATs")
            
            logger.info(f"{vpc_id:<20} | {name:<25} | {cidr:<15} | {str(is_default):<10} | {status}")
            
            if status == "LIKELY UNUSED":
                unused_candidates.append({
                    'id': vpc_id,
                    'name': name,
                    'is_default': is_default,
                    'resources': {
                        'subnets': subnet_count,
                        'igws': igw_count,
                        'route_tables': rt_count,
                        'nats': nat_count
                    }
                })

        logger.info("-" * 80)
        
        if unused_candidates:
            logger.info("\n[!] DETAILED ANALYSIS OF UNUSED VPCs:")
            for candidate in unused_candidates:
                c = candidate
                logger.info(f"VPC: {c['id']} ({c['name']})")
                logger.info(f"  - Default VPC: {c['is_default']}")
                logger.info(f"  - Subnets: {c['resources']['subnets']}")
                logger.info(f"  - Route Tables: {c['resources']['route_tables']}")
                logger.info(f"  - Internet Gateways: {c['resources']['igws']}")
                logger.info(f"  - NAT Gateways: {c['resources']['nats']}")
                logger.info("  - Recommendation: CHECK IF REQUIRED. If just empty scaffolding, safe to delete.")
                logger.info("")
        else:
            logger.info("\nNo completely empty VPCs found (all have active network interfaces).")

    except ClientError as e:
        logger.error(f"AWS Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    get_vpc_details()
