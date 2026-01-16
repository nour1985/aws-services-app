import argparse
import sys
import logging
from datetime import datetime
from tabulate import tabulate
from inspector import AWSResourceInspector

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="AWS Resource Inspector and Cleanup Tool")
    parser.add_argument("--region", required=True, help="AWS Region (e.g., us-east-1)")
    parser.add_argument("--group-arn", required=True, help="AWS Resource Group ARN or Name to inspect")
    parser.add_argument("--active-tag", help="Tag value (or key) to treat as 'Active/Keep' project identifier")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Enable dry-run mode (no deletion). Default is True.")
    parser.add_argument("--execute", action="store_true", help="Explicitly enable deletion (overrides default dry-run).")
    parser.add_argument("--report-only", action="store_true", help="Only generate report, do not attempt cleanup.")
    parser.add_argument("--output-file", help="Path to save the report file.")

    args = parser.parse_args()

    # Safety check: Default to dry run unless --execute is passed
    is_dry_run = not args.execute
    if args.dry_run and args.execute:
        logger.warning("Both --dry-run and --execute specified. Preferring EXECUTE mode (Real Deletion).")
        is_dry_run = False
    
    logger.info(f"Starting Inspector in {'DRY RUN' if is_dry_run else 'EXECUTION'} mode.")

    inspector = AWSResourceInspector(region=args.region, dry_run=is_dry_run)
    
    # 1. Discovery
    inspector.scan_resource_group(args.group_arn)
    inspector.enrich_resource_data()

    if not inspector.discovered_resources:
        logger.info("No resources found.")
        return

    # 2. Assessment
    # If active-tag is not provided, we might default to just listing everything or assume nothing is safe.
    # For safety, if no tag is provided, we default to DELETE but justify as "No active tag provided to match".
    analyzed_resources = inspector.assess_relevance(active_project_tag=args.active_tag)

    # 3. Reporting
    table_data = []
    for r in analyzed_resources:
        # Format tags for display
        tags_str = "\n".join([f"{k}={v}" for k, v in r.get('Tags', {}).items()])
        table_data.append([
            r['Type'], 
            r['Arn'], # Show full ARN
            tags_str,
            r.get('Relevance'), 
            r.get('Justification')
        ])
    
    print("\n" + "="*50)
    print("INSPECTION REPORT")
    print("="*50)
    print(tabulate(table_data, headers=["Type", "Resource ID", "Tags", "Action", "Justification"], tablefmt="grid"))
    print(f"Total Resources: {len(analyzed_resources)}")
    
    delete_count = sum(1 for r in analyzed_resources if r['Relevance'] == 'DELETE')
    print(f"Resources marked for deletion: {delete_count}")
    print("="*50 + "\n")

    if args.output_file:
        try:
            # Determine table format based on extension
            fmt = "github" if args.output_file.endswith(".md") else "grid"
            
            with open(args.output_file, 'w') as f:
                if fmt == "github":
                    f.write(f"# INSPECTION REPORT\n")
                    f.write(f"**Date**: {datetime.now().isoformat()}\n\n")
                    f.write(tabulate(table_data, headers=["Type", "Resource ID", "Tags", "Action", "Justification"], tablefmt=fmt))
                    f.write(f"\n\n**Total Resources**: {len(analyzed_resources)}\n")
                    f.write(f"**Resources marked for deletion**: {delete_count}\n")
                else:
                    f.write("INSPECTION REPORT\n")
                    f.write("="*50 + "\n")
                    f.write(tabulate(table_data, headers=["Type", "Resource ID", "Tags", "Action", "Justification"], tablefmt=fmt))
                    f.write(f"\nTotal Resources: {len(analyzed_resources)}\n")
                    f.write(f"Resources marked for deletion: {delete_count}\n")
            logger.info(f"Report saved to {args.output_file}")
        except Exception as e:
            logger.error(f"Failed to save report to file: {e}")

    if args.report_only:
        logger.info("Report only mode. Exiting.")
        return

    if delete_count > 0:
        if is_dry_run:
            logger.info("Dry run complete. No resources deleted. Use --execute to perform deletion.")
            # Call cleanup in dry run mode to show what would happen
            inspector.cleanup(analyzed_resources) 
        else:
            confirmation = input(f"WARNING: You are about to delete {delete_count} resources. Type 'CONFIRM' to proceed: ")
            if confirmation == "CONFIRM":
                inspector.cleanup(analyzed_resources)
            else:
                logger.info("Deletion cancelled by user.")
    else:
        logger.info("No resources marked for deletion.")

if __name__ == "__main__":
    main()
