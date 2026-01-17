import os
import boto3
import time
from botocore.exceptions import ClientError
import config

# Absolute path to the report file
REPORT_FILE = config.REPORT_FILE_PATH
REGION = config.AWS_REGION

# Priority map for deletion (Lower number = Earlier deletion)
# Priority map for deletion (Lower number = Earlier deletion)
DELETION_ORDER = {
    # App Layer
    "apprunner:service": 10,
    "apprunner:autoscalingconfiguration": 11,
    "lambda:function": 12,
    "ecs:service": 15,
    "ecs:task-definition": 16,
    "ec2:security-group-rule": 18, 
    
    # Load Balancing
    "elasticloadbalancing:listener": 20,
    "elasticloadbalancing:loadbalancer": 25,
    "elasticloadbalancing:targetgroup": 30,
    
    # Compute & Containers
    "ec2:instance": 35,
    "ecs:cluster": 40,
    
    # DevOps
    "codepipeline:pipeline": 45,
    "codebuild:project": 50,
    "codestar-connections:connection": 55,
    
    # Storage & DB
    "rds:db-instance": 60,
    "dynamodb:table": 61,
    
    # Network Assets - Active
    "ec2:natgateway": 70,
    "ec2:elastic-ip": 75,
    
    # Security & Network
    "ec2:security-group": 80,
    "ec2:network-acl": 85,
    "ec2:subnet": 90,
    "ec2:route-table": 95,
    "ec2:internet-gateway": 100,
    "ec2:vpc": 110,
    
    # Artifacts (Last)
    "ecr:repository": 120,
    "s3:bucket": 130,
    "logs:log-group": 140,
    "resource-groups:group": 150,
    "payments:payment-instrument": 999 
}

def clean_resource_id(service, rtype, raw_id):
    # Fix ID format: "vpc/vpc-123" -> "vpc-123"
    # "elastic-ip/eipalloc-123" -> "eipalloc-123"
    if '/' in raw_id and not raw_id.startswith('arn:'):
        # Specific overrides where we might want the prefix? 
        # Usually split works for: vpc/id, subnet/id, etc.
        # But NOT for "project/name" if name has slashes (unlikely for project name but possible)
        # For EC2 resources it is always safe.
        if service == 'ec2':
            return raw_id.split('/')[-1]
        if service == 'ecs' and rtype in ['cluster', 'task-definition']:
             return raw_id.split('/')[-1]
        if service == 'elasticloadbalancing' and rtype in ['loadbalancer', 'targetgroup']:
             # These are ARNs usually in the file or partials?
             # File: targetgroup/name/id. 
             # If we take last part, it's just ID. We need full ARN or Name?
             # Boto3 needs ARN for delete.
             # So we shouldn't strip too much if we search by containment.
             return raw_id
             
    return raw_id

def get_boto_session(region):
    return boto3.Session(region_name=region)

def delete_resource(session, service, rtype, resource_id):
    """
    Dispatches to specific deletion functions based on service and type.
    Returns True if deleted or already gone, False if failed.
    """
    print(f"Attempting to delete {service} {rtype} : {resource_id}")
    try:
        if service == 'ec2':
            ec2 = session.client('ec2')
            if rtype == 'elastic-ip':
                # ID is eipalloc-xxx
                ec2.release_address(AllocationId=resource_id)
            elif rtype == 'internet-gateway':
                # Detach first (try to find VPCs) then delete
                igw = boto3.resource('ec2', region_name=REGION).InternetGateway(resource_id)
                try:
                    for vpc in igw.attachments:
                        igw.detach_from_vpc(VpcId=vpc['VpcId'])
                except Exception as e:
                    print(f"  Warning detaching IGW: {e}")
                ec2.delete_internet_gateway(InternetGatewayId=resource_id)
            elif rtype == 'natgateway':
                ec2.delete_nat_gateway(NatGatewayId=resource_id)
                wait_for_deletion(ec2, 'nat_gateway_deleted', {'NatGatewayIds': [resource_id]})
            elif rtype == 'network-acl':
                ec2.delete_network_acl(NetworkAclId=resource_id)
            elif rtype == 'route-table':
                # Dissociate subnets first if needed? AWS handles simple associations usually?
                ec2.delete_route_table(RouteTableId=resource_id)
            elif rtype == 'security-group':
                ec2.delete_security_group(GroupId=resource_id)
            # elif rtype == 'security-group-rule':
            #     # Not supported in older boto3 or unnecessary
            #     pass
            elif rtype == 'subnet':
                ec2.delete_subnet(SubnetId=resource_id)
            elif rtype == 'vpc':
                ec2.delete_vpc(VpcId=resource_id)
            elif rtype == 'instance':
                ec2.terminate_instances(InstanceIds=[resource_id])
            elif rtype == 'unknown' and service == 'ec2':
                # Try to guess from ID
                if resource_id.startswith('sg-'):
                    ec2.delete_security_group(GroupId=resource_id)
                elif resource_id.startswith('acl-'):
                    ec2.delete_network_acl(NetworkAclId=resource_id)
                elif resource_id.startswith('rtb-'):
                    ec2.delete_route_table(RouteTableId=resource_id)
                elif resource_id.startswith('subnet-'):
                    ec2.delete_subnet(SubnetId=resource_id)
                elif resource_id.startswith('nat-'):
                    ec2.delete_nat_gateway(NatGatewayId=resource_id)
                elif resource_id.startswith('igw-'):
                    ec2.delete_internet_gateway(InternetGatewayId=resource_id)
                elif resource_id.startswith('eipalloc-'):
                    ec2.release_address(AllocationId=resource_id)
                else:
                    print(f"  Skipping unknown EC2 resource {resource_id}")
                    return False
        
        elif service == 's3':
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(resource_id)
            # Delete all objects first
            try:
                bucket.objects.all().delete()
                bucket.object_versions.all().delete()
                bucket.delete()
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchBucket':
                    pass
                else:
                    raise

        elif service == 'ecr':
            ecr = session.client('ecr')
            # Extract repo name from "repository/name" or just name
            repo_name = resource_id.split('/')[-1]
            ecr.delete_repository(repositoryName=repo_name, force=True)

        elif service == 'codebuild':
            cb = session.client('codebuild')
            # id might be project/name
            name = resource_id.split('/')[-1]
            cb.delete_project(name=name)

        elif service == 'codepipeline':
            cp = session.client('codepipeline')
            name = resource_id.split('/')[-1]
            cp.delete_pipeline(name=name)
        
        elif service == 'codestar-connections':
            cs = session.client('codestar-connections')
            # Needs ARN? The ID in file is usually the ARN or ID. 
            # If ID is connection/uuid, we might need full ARN.
            # Assuming resource_id is the ARN or we can verify.
            # If input is 'connection/uuid', assume we need to query or it is the ARN suffix?
            # Actually, `aws codeconnections delete-connection --connection-arn ...`
            # If we don't have the ARN, we can't delete easily. 
            # Check if identifier IS the ARN (it usually is for this report).
            # The report showed: `connection/36d4bc55-f22c-4c59-828a-c7d2171c9b0c`
            # Valid ARN format: arn:aws:codestar-connections:us-east-1:account:connection/uuid
            # We might need to construct the ARN or list to find it.
            # For now, try deleting if it looks like an ARN, else try to find it.
            if resource_id.startswith('arn:'):
                arn = resource_id
            else:
                 # Try to construct or find
                 # This is risky without account ID. 
                 # Let's list connections and match ID.
                 conns = cs.list_connections()['Connections']
                 arn = next((c['ConnectionArn'] for c in conns if resource_id in c['ConnectionArn']), None)
            
            if arn:
                cs.delete_connection(ConnectionArn=arn)
            else:
                print(f"  Skipping connection {resource_id}: Could not resolve ARN")
                return False

        elif service == 'ecs':
            ecs = session.client('ecs')
            if rtype == 'cluster':
                 # id might be cluster/name
                 name = resource_id.split('/')[-1]
                 ecs.delete_cluster(cluster=name)
            elif rtype == 'service':
                 # service/cluster/servicename or similar
                 # Report gave: service/aws-service-liblib-dev-cluster/aws-service-liblib-app-dev
                 parts = resource_id.split('/')
                 if len(parts) >= 3:
                     cluster = parts[1]
                     svc_name = parts[2]
                     ecs.delete_service(cluster=cluster, service=svc_name, force=True)
            elif rtype == 'task-definition':
                 # id: task-definition/name
                 # deregister needs full name:revision or arn
                 # If id has no revision, list families?
                 # Report string: task-definition/aws-service-liblib-app-dev
                 # This might just be family. We need to deregister revisions.
                 family = resource_id.split('/')[-1]
                 # list tasks
                 arns = ecs.list_task_definitions(familyPrefix=family, status='ACTIVE')['taskDefinitionArns']
                 for arn in arns:
                     ecs.deregister_task_definition(taskDefinition=arn)

        elif service == 'elasticloadbalancing':
            elbv2 = session.client('elbv2')
            if rtype == 'targetgroup':
                # Needs ARN
                if resource_id.startswith('arn:'):
                    arn = resource_id
                else:
                    # Construct or search. Report usually has ID part.
                    # Identifier: targetgroup/h12026/91bf...
                    # Valid ARN: arn:aws:elasticloadbalancing:region:acc:targetgroup/name/id
                    # Search
                    tgs = elbv2.describe_target_groups()['TargetGroups']
                    arn = next((t['TargetGroupArn'] for t in tgs if resource_id in t['TargetGroupArn']), None)
                if arn: elbv2.delete_target_group(TargetGroupArn=arn)
            elif rtype == 'loadbalancer':
                # Needs ARN
                if resource_id.startswith('arn:'):
                    arn = resource_id
                else:
                    lbs = elbv2.describe_load_balancers()['LoadBalancers']
                    arn = next((l['LoadBalancerArn'] for l in lbs if resource_id in l['LoadBalancerArn']), None)
                if arn: 
                    # Disable deletion protection if enabled
                    try:
                        elbv2.modify_load_balancer_attributes(
                            LoadBalancerArn=arn,
                            Attributes=[{'Key': 'deletion_protection.enabled', 'Value': 'false'}]
                        )
                        print(f"  Disabled deletion protection for {arn}")
                    except Exception as e:
                        print(f"  Warning: Could not disable deletion protection: {e}")

                    elbv2.delete_load_balancer(LoadBalancerArn=arn)
                    # wait?
                    time.sleep(5)
            elif rtype == 'listener':
                # Needs ARN
                if resource_id.startswith('arn:'):
                    arn = resource_id
                else:
                    # Hard to find listener without LB. 
                    # But if we iterate all LBs we can find it.
                    # Or assume it deletes with LB. Listener deletion is 20, LB is 30.
                    # Explicit delete:
                    # Identifier: listener/app/lbname/id/listenerid
                    pass # Usually deleted with LB, but we can try if we find arn.
                    # Since LB delete cascades to listeners, we can potentially skip or try.
                    # Let's try to find it.
                    pass 

        elif service == 'logs':
            logs = session.client('logs')
            # Identifier should be log group name (or ARN, but delete_log_group needs name)
            # The Resolve Identifier helper tries to find Name from tags if id is generic.
            # reader now produces log group name or ARN? reader produces ARN for some, but logs were 'logs | log-group | ...'
            # reader.py now produces name?
            # Let's assume resource_id is the name or we try to extract it
            # if resource_id starts with arn, split
            log_group_name = resource_id
            if resource_id.startswith('arn:'):
                 # arn:aws:logs:region:account:log-group:NAME:*
                 parts = resource_id.split(':log-group:')
                 if len(parts) > 1:
                     log_group_name = parts[1].split(':')[0]
            
            logs.delete_log_group(logGroupName=log_group_name)

        elif service == 'resource-groups':
            rg = session.client('resource-groups')
            # Identifier: group/name
            name = resource_id.split('/')[-1]
            rg.delete_group(Group=name)
            
        elif service == 'apprunner':
            ap = session.client('apprunner')
            if rtype == 'autoscalingconfiguration':
                # Need ARN. Identifier: autoscalingconfiguration/name/rev/id
                # Search
                arn = None
                cw = ap.list_auto_scaling_configurations()
                # Pagination needed?
                for c in cw['AutoScalingConfigurationSummaryList']:
                    if resource_id in c['AutoScalingConfigurationArn']:
                        arn = c['AutoScalingConfigurationArn']
                        break
                if arn: ap.delete_auto_scaling_configuration(AutoScalingConfigurationArn=arn)
            elif rtype == 'service':
                ap.delete_service(ServiceArn=resource_id)

        elif service == 'lambda':
            lam = session.client('lambda')
            lam.delete_function(FunctionName=resource_id)

        elif service == 'rds':
            rds = session.client('rds')
            rds.delete_db_instance(DBInstanceIdentifier=resource_id, SkipFinalSnapshot=True)

        elif service == 'dynamodb':
            ddb = session.client('dynamodb')
            ddb.delete_table(TableName=resource_id)
            
        else:
            print(f"  Failed: Unhandled service/type {service}:{rtype}")
            return False

        print(f"  Deleted {service} {rtype}")
        return True

    except ClientError as e:
        code = e.response['Error']['Code']
        msg = str(e)
        if 'NotFound' in code or 'DependencyViolation' in code:
             print(f"  Error deleting {resource_id}: {code}")
             if 'DependencyViolation' in code:
                 return False # Retry later?
        elif 'CannotDelete' in code and 'default' in msg:
             print(f"  Skipping default resource {resource_id} (cannot be deleted)")
             return True # Treat as success so we don't retry forever
        elif 'InvalidParameterValue' in code and 'default' in msg:
             print(f"  Skipping default (ACL/SG) {resource_id}")
             return True 
             
        print(f"  Failed: {e}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def wait_for_deletion(client, waiter_name, params):
    try:
        waiter = client.get_waiter(waiter_name)
        waiter.wait(**params)
    except Exception:
        pass

def mark_as_deleted(text):
    if '<span style="color:red">' in text:
        return text
    return f'<span style="color:red">{text}</span>'

def resolve_identifier(res_dict, tag_str):
    """
    Helper to resolve ambiguous identifiers like 'log-group' using Tags or other hints.
    """
    rid = res_dict['id_raw'].strip('`')
    
    # CASE: Logs with generic identifier "log-group"
    # Also useful if we want to use Name tag for other generic IDs if implemented
    if res_dict['service'] == 'logs' and 'log-group' in rid:
        # Clean backticks from simplified report
        clean_tags = tag_str.replace('`', '')
        
        # Tags format: Name: Value<br>... or just Name: Value
        if 'Name: ' in clean_tags:
            # Extract Name
            # Split by <br> or newline just in case
            parts = clean_tags.replace('<br>', '\n').split('\n')
            for p in parts:
                if 'Name: ' in p:
                    # p is "Name: Value"
                    return p.split('Name: ')[1].strip()
    
    return rid

def main():
    if not os.path.exists(REPORT_FILE):
        print(f"Error: File {REPORT_FILE} not found.")
        return

    session = get_boto_session(REGION)
    
    print(f"Reading {REPORT_FILE}...")
    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    resources = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith('|'): continue
        parts = [p.strip() for p in stripped.split('|')]
        if len(parts) < 5: continue
        if 'Identifier' in parts[1] or '---' in parts[1]: continue
        
        id_raw = parts[1]
        service = parts[2].lower().strip()
        rtype = parts[3].lower().strip()
        tags = parts[5] if len(parts) > 5 else ""

        # Strip HTML tags if present (handling previously simulated deletions)
        clean_id_raw = id_raw.replace('<span style="color:red">', '').replace('</span>', '').strip()
        clean_service = service.replace('<span style="color:red">', '').replace('</span>', '').strip()
        clean_type = rtype.replace('<span style="color:red">', '').replace('</span>', '').strip()

        # Get priority
        key = f"{clean_service}:{clean_type}"
        prio = DELETION_ORDER.get(key, DELETION_ORDER.get(clean_service, 999))
        
        resources.append({
            "index": i,
            "parts": parts,
            "id_raw": clean_id_raw,
            "service": clean_service,
            "type": clean_type,
            "priority": prio,
            "tags": tags
        })

    resources.sort(key=lambda x: x['priority'])

    if not resources:
        print("No active resources found to delete.")
        return

    print(f"Found {len(resources)} active resources. Starting deletion...")

    for res in resources:
        clean_id = resolve_identifier(res, res['tags'])
        clean_id = clean_resource_id(res['service'], res['type'], clean_id)
        
        # Safety check: Don't delete payments or critical things blindly if not targeted
        if res['service'] == 'payments':
            print(f"Skipping payment instrument: {clean_id}")
            continue

        print(f"[{res['priority']}] Deleting {res['service']} {res['type']} - {clean_id}")
        
        # Retry logic for dependencies
        max_retries = 3
        success = False
        for attempt in range(max_retries):
            success = delete_resource(session, res['service'], res['type'], clean_id)
            if success:
                break
            if attempt < max_retries - 1:
                print(f"  Retrying {clean_id} in 5s...")
                time.sleep(5)
        
        if success:
            # Mark as deleted in memory
            cols = res['parts']
            cols[1] = mark_as_deleted(cols[1])
            cols[2] = mark_as_deleted(cols[2])
            cols[3] = mark_as_deleted(cols[3])
            lines[res['index']] = " | ".join(cols) + "\n"
            
            # Save progress immediately in case of crash
            with open(REPORT_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # Rate limit slightly
            time.sleep(1)

    print("Deletion process complete.")

if __name__ == "__main__":
    main()
