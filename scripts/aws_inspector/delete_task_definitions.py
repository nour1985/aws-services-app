import boto3
import argparse
import logging
from typing import Set, Dict, List
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def delete_task_definitions(region: str = 'us-east-1', dry_run: bool = True):
    session = boto3.Session(region_name=region)
    ecs = session.client('ecs')

    logger.info(f"Starting Task Definition Cleanup in {region} (Dry Run: {dry_run})")
    
    try:
        # 1. Identify ALL Active Task Definitions
        active_task_arns: Set[str] = set()
        
        clusters = ecs.list_clusters().get('clusterArns', [])
        logger.info(f"Scanning {len(clusters)} clusters for active usage...")

        for cluster in clusters:
            # Services
            paginator = ecs.get_paginator('list_services')
            for page in paginator.paginate(cluster=cluster):
                service_arns = page.get('serviceArns', [])
                if not service_arns: continue
                
                for i in range(0, len(service_arns), 10):
                    batch = service_arns[i:i+10]
                    services = ecs.describe_services(cluster=cluster, services=batch).get('services', [])
                    for svc in services:
                        active_task_arns.add(svc['taskDefinition'])
                        for dep in svc.get('deployments', []):
                            active_task_arns.add(dep['taskDefinition'])

            # Tasks
            paginator = ecs.get_paginator('list_tasks')
            for page in paginator.paginate(cluster=cluster):
                task_arns = page.get('taskArns', [])
                if not task_arns: continue
                
                for i in range(0, len(task_arns), 100):
                    batch = task_arns[i:i+100]
                    tasks = ecs.describe_tasks(cluster=cluster, tasks=batch).get('tasks', [])
                    for t in tasks:
                        active_task_arns.add(t['taskDefinitionArn'])

        logger.info(f"Found {len(active_task_arns)} active revisions.")

        # 2. Find Candidates for Deletion
        paginator = ecs.get_paginator('list_task_definition_families')
        stale_candidates = []

        for page in paginator.paginate(status='ACTIVE'):
            for family in page.get('families', []):
                # Fetch ACTIVE
                actives = ecs.list_task_definitions(familyPrefix=family, status='ACTIVE', sort='DESC').get('taskDefinitionArns', [])
                # Fetch INACTIVE
                inactives = ecs.list_task_definitions(familyPrefix=family, status='INACTIVE', sort='DESC').get('taskDefinitionArns', [])
                
                # Merge and Sort High to Low (Newest Revision First)
                all_arns = sorted(set(actives + inactives), key=lambda x: int(x.split(':')[-1]), reverse=True)
                
                # Keep Policy: Active OR Top 2 Most Recent
                for i, arn in enumerate(all_arns):
                    is_active = arn in active_task_arns
                    # Top 2 most recent revisions (regardless of status) are "Recent Backups"
                    is_recent = i < 2 
                    
                    if not is_active and not is_recent:
                        stale_candidates.append(arn)

        logger.info(f"Found {len(stale_candidates)} stale revisions eligible for deregistration.")

        # 3. Executing Deletion
        if not stale_candidates:
            logger.info("No stale definitions found.")
            return

        # 3. Executing Deletion
        if not stale_candidates:
            logger.info("No stale definitions found.")
            return

        # Step A: Deregister all candidates first (Required before deletion)
        # Even if already INACTIVE, deregistering again is generally safe/idempotent or we can catch exceptions
        if not dry_run:
            logger.info("Step 1: Deregistering candidates to ensure INACTIVE state...")
        
        for arn in stale_candidates:
            if dry_run:
                logger.info(f"[DRY RUN] Would deregister and then PERMANENTLY DELETE: {arn}")
            else:
                try:
                    # We must ensure it is inactive.
                    ecs.deregister_task_definition(taskDefinition=arn)
                except ClientError as e:
                    # If it's already inactive, that's fine, but let's log other errors
                    logger.warning(f"Deregister warning for {arn}: {e}")

        if dry_run:
             logger.info("\n[DRY RUN COMPLETE] No changes were made. Run with --force to PERMANENTLY DELETE.")
             return

        # Step B: Permanent Deletion (Batch of 10)
        logger.info("Step 2: Permanently Deleting candidates...")
        
        # Batch into chunks of 10
        chunk_size = 10
        for i in range(0, len(stale_candidates), chunk_size):
            batch = stale_candidates[i:i + chunk_size]
            try:
                response = ecs.delete_task_definitions(taskDefinitions=batch)
                failed = response.get('failures', [])
                for f in failed:
                    logger.error(f"Failed to delete {f['arn']}: {f['reason']}")
                
                deleted = response.get('taskDefinitions', [])
                for d in deleted:
                    logger.info(f"Permanently Deleted: {d['taskDefinitionArn']}")
            except ClientError as e:
                 logger.error(f"Batch delete failed: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error during deletion: {e}")

        logger.info("\n[CLEANUP COMPLETE] Stale definitions permanently deleted.")

    except ClientError as e:
        logger.error(f"AWS Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Deregister stale ECS Task Definitions.')
    parser.add_argument('--region', default='us-east-1', help='AWS Region')
    parser.add_argument('--force', action='store_true', help='Execute deletion (disable dry-run)')

    args = parser.parse_args()

    delete_task_definitions(region=args.region, dry_run=not args.force)
