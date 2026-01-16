import boto3
import argparse
import sys
import time
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def delete_vpc(vpc_id, region='us-east-1', dry_run=True):
    session = boto3.Session(region_name=region)
    ec2 = session.resource('ec2')
    ec2_client = session.client('ec2')
    vpc = ec2.Vpc(vpc_id)

    try:
        # Verify VPC exists
        vpc.load()
    except ClientError:
        logger.error(f"VPC {vpc_id} not found in {region}.")
        return

    logger.info(f"Starting deletion process for VPC: {vpc_id} (Dry Run: {dry_run})")

    # 1. Check for Active Network Interfaces (Safety Check)
    # If there are ENIs, it means *something* is running (EC2, Lambda, RDS, ELB, etc.)
    enis = list(vpc.network_interfaces.all())
    if enis:
        logger.warning(f"CRITICAL: Found {len(enis)} active Network Interfaces in this VPC.")
        for eni in enis:
            logger.warning(f"  - ENI: {eni.id} ({eni.description}) attached to {eni.attachment.get('InstanceId', 'N/A') if eni.attachment else 'N/A'}")
        
        logger.error("ABORTING: Cannot delete VPC with active resources. Manually terminate instances/services first.")
        return

    # If dry run, we stop here before modifying anything (or simulate steps)
    if dry_run:
        logger.info("[DRY RUN] Safety check passed (0 active ENIs). The following actions would be performed:")
        logger.info(f"  - Delete {len(list(vpc.internet_gateways.all()))} Internet Gateways")
        logger.info(f"  - Delete {len(list(vpc.subnets.all()))} Subnets")
        logger.info(f"  - Delete {len(list(vpc.route_tables.all()))} Route Tables")
        logger.info(f"  - Delete {len(list(vpc.security_groups.all()))} Security Groups")
        logger.info(f"  - Delete {len(list(vpc.network_acls.all()))} Network ACLs")
        logger.info(f"  - Delete VPC {vpc_id}")
        return

    # ---------------- DELETION PHASE ----------------

    # 2. Delete VPC Peering Connections
    for peering in vpc.accepted_vpc_peering_connections.all():
        if peering.status['Code'] != 'deleted':
             logger.info(f"Deleting Peering Connection {peering.id}")
             peering.delete()
    
    for peering in vpc.requested_vpc_peering_connections.all():
        if peering.status['Code'] != 'deleted':
            logger.info(f"Deleting Peering Connection {peering.id}")
            peering.delete()

    # 3. Delete NAT Gateways
    # Need to use client for this usually
    nat_gateways = ec2_client.describe_nat_gateways(Filter=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NatGateways']
    for nat in nat_gateways:
        if nat['State'] != 'deleted':
            logger.info(f"Deleting NAT Gateway {nat['NatGatewayId']}")
            ec2_client.delete_nat_gateway(NatGatewayId=nat['NatGatewayId'])
            
            # Application must wait for NAT to be deleted before deleting subnets
            while True:
                time.sleep(5)
                check = ec2_client.describe_nat_gateways(NatGatewayIds=[nat['NatGatewayId']])
                state = check['NatGateways'][0]['State']
                logger.info(f"  Waiting for NAT {nat['NatGatewayId']} to delete... ({state})")
                if state == 'deleted':
                    break

    # 4. Detach and Delete Internet Gateways
    for igw in vpc.internet_gateways.all():
        logger.info(f"Detaching and Deleting Internet Gateway {igw.id}")
        igw.detach_from_vpc(VpcId=vpc_id)
        igw.delete()

    # 5. Delete VPC Endpoints
    params = {'Filters': [{'Name': 'vpc-id', 'Values': [vpc_id]}]}
    endpoints = ec2_client.describe_vpc_endpoints(**params)['VpcEndpoints']
    if endpoints:
        ids = [ep['VpcEndpointId'] for ep in endpoints]
        logger.info(f"Deleting VPC Endpoints: {ids}")
        ec2_client.delete_vpc_endpoints(VpcEndpointIds=ids)

    # 6. Delete Subnets
    for subnet in vpc.subnets.all():
        logger.info(f"Deleting Subnet {subnet.id}")
        subnet.delete()

    # 7. Delete Route Tables
    for rt in vpc.route_tables.all():
        is_main = False
        for assoc in rt.associations:
            if assoc.main:
                is_main = True
                break
        if not is_main:
            logger.info(f"Deleting Route Table {rt.id}")
            rt.delete()

    # 8. Delete Network ACLs
    for acl in vpc.network_acls.all():
        if not acl.is_default:
            logger.info(f"Deleting Network ACL {acl.id}")
            acl.delete()

    # 9. Delete Security Groups
    # First, revoke all ingress/egress rules to break dependencies between groups
    for sg in vpc.security_groups.all():
        if sg.group_name != 'default':
            logger.info(f"Revoking rules for Security Group {sg.id}")
            if sg.ip_permissions:
                sg.revoke_ingress(IpPermissions=sg.ip_permissions)
            if sg.ip_permissions_egress:
                sg.revoke_egress(IpPermissions=sg.ip_permissions_egress)

    for sg in vpc.security_groups.all():
        if sg.group_name != 'default':
            logger.info(f"Deleting Security Group {sg.id}")
            sg.delete()

    # 10. Delete VPC
    logger.info(f"Deleting VPC {vpc_id}...")
    vpc.delete()
    logger.info("VPC Deleted Successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Delete an AWS VPC and its dependencies.')
    parser.add_argument('--vpc-id', required=True, help='The ID of the VPC to delete')
    parser.add_argument('--region', default='us-east-1', help='AWS Region')
    parser.add_argument('--force', action='store_true', help='Execute deletion (disable dry-run)')

    args = parser.parse_args()

    delete_vpc(args.vpc_id, args.region, dry_run=not args.force)
