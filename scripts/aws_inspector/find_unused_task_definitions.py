import boto3
import logging
from typing import Set, Dict, List
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def find_unused_task_definitions(region: str = 'us-east-1'):
    session = boto3.Session(region_name=region)
    ecs = session.client('ecs')

    try:
        # 1. Identify ALL Active Task Definitions (from Clusters -> Services & Tasks)
        active_task_arns: Set[str] = set()
        
        # Get Clusters
        clusters = ecs.list_clusters().get('clusterArns', [])
        logger.info(f"Scanning {len(clusters)} ECS Clusters for active usage...")

        for cluster in clusters:
            # Get Services
            paginator = ecs.get_paginator('list_services')
            for page in paginator.paginate(cluster=cluster):
                service_arns = page.get('serviceArns', [])
                if not service_arns:
                    continue
                    
                # Describe services to get Task Defs
                # describe_services has a limit of 10
                for i in range(0, len(service_arns), 10):
                    batch = service_arns[i:i+10]
                    services = ecs.describe_services(cluster=cluster, services=batch).get('services', [])
                    for svc in services:
                        active_task_arns.add(svc['taskDefinition'])
                        # Also check deployments if rolling update
                        for dep in svc.get('deployments', []):
                            active_task_arns.add(dep['taskDefinition'])

            # Get Running Tasks (Standalone)
            paginator = ecs.get_paginator('list_tasks')
            for page in paginator.paginate(cluster=cluster):
                task_arns = page.get('taskArns', [])
                if not task_arns:
                    continue
                
                # Describe tasks to get Task Defs
                for i in range(0, len(task_arns), 100):
                    batch = task_arns[i:i+100]
                    tasks = ecs.describe_tasks(cluster=cluster, tasks=batch).get('tasks', [])
                    for t in tasks:
                        active_task_arns.add(t['taskDefinitionArn'])

        logger.info(f"Found {len(active_task_arns)} uniquely active Task Definition Revisions.")
        logger.info("-" * 80)

        # 2. Analyze Task Definition Families
        paginator = ecs.get_paginator('list_task_definition_families')
        
        stale_candidates = []
        
        logger.info(f"{'Family':<40} | {'Rev':<5} | {'Status':<10} | {'Description'}")
        logger.info("-" * 80)

        for page in paginator.paginate(status='ACTIVE'):
            for family in page.get('families', []):
                # List all revisions for this family
                # list_task_definitions returns ARNs
                # By default returns most recent first? No, documentation says active.
                # We want to sort them to find the "tail".
                
                list_resp = ecs.list_task_definitions(familyPrefix=family, sort='DESC')
                all_arns = list_resp.get('taskDefinitionArns', [])
                
                # all_arns is sorted DESC (highest revision first)
                
                # Keep Policy:
                # 1. Any Active ARN -> KEEP
                # 2. Any ARN in top 2 (most recent) -> KEEP (Safety buffer)
                # 3. Rest -> CANDIDATE FOR DELETION
                
                for i, arn in enumerate(all_arns):
                    revision = int(arn.split(':')[-1])
                    status = "UNKNOWN"
                    desc = ""
                    
                    is_active = arn in active_task_arns
                    is_recent = i < 2 # Top 2 are indices 0, 1
                    
                    if is_active:
                        status = "ACTIVE"
                        desc = "Currently running"
                    elif is_recent:
                        status = "KEEP"
                        desc = "Recent backup (Safety)"
                    else:
                        status = "STALE"
                        desc = "Safe to delete"
                        stale_candidates.append(arn)

                    # Only log interesting ones (Active or Stale) - logging ALL might be spammy for 100s revisions
                    # Let's log if it's active or the very latest unused, or if it's stale.
                    if status == "ACTIVE" or (status == "KEEP" and i == 0):
                        logger.info(f"{family:<40} | {revision:<5} | {status:<10} | {desc}")
                    elif status == "STALE" and i == len(all_arns) - 1:
                         # Log the range of stale ones maybe?
                         # For now just log individual line if not too many
                         pass

        logger.info("-" * 80)
        logger.info(f"Found {len(stale_candidates)} STALE Task Definitions (older than top 2, not active).")
        
        if stale_candidates:
            logger.info("\nExample Stale Definitions:")
            for arn in stale_candidates[:10]:
                logger.info(f"  - {arn}")
            if len(stale_candidates) > 10:
                logger.info(f"  ... and {len(stale_candidates) - 10} more.")

    except ClientError as e:
        logger.error(f"AWS Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    find_unused_task_definitions()
