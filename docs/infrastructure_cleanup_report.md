# VPC Investigation Report

## Findings
We scanned the `us-east-1` region for VPCs and analyzed their usage based on active network interfaces (ENIs), which indicate attached resources like EC2 instances, RDS databases, or Lambda functions.

### Summary Table
| VPC ID | Name | CIDR | Is Default | Status |
| :--- | :--- | :--- | :--- | :--- |
| `vpc-0f1c5703ae3954c9d` | N/A | 172.31.0.0/16 | **True** | **DELETED** |
| `vpc-0b99dbf83e8091f46` | `aws-service-liblib-dev-vpc` | 10.0.0.0/16 | False | ACTIVE |

### Action Taken
#### [DELETED] `vpc-0f1c5703ae3954c9d`
- **Reason:** Confirmed unused (0 active ENIs).
- **Resources Removed:**
    - 6 Subnets
    - 1 Internet Gateway
    - 1 Route Table
    - 3 Security Groups
    - 1 Network ACLs
    - The VPC itself

### Active VPCs
#### `vpc-0b99dbf83e8091f46` (aws-service-liblib-dev-vpc)
- This VPC remains active and untouched.

---

# ECS Task Definition Report

## Findings
We scanned all ECS Clusters and Task Definitions to identify active usage vs. stale revisions.

### Summary
| Family | Revision | Status | Description |
| :--- | :--- | :--- | :--- |
| `aws-service-liblib-app-dev` | **15** | **ACTIVE** | Currently running in Service |
| `liblib-digital-hall-5-dev-task` | 1 | **KEEP** | Inactive, but kept as backup |

### Stale Definitions (Candidates for Deletion)
Found **0** stale revisions.
(Previously identified 8 stale revisions were successfully deregistered).

### Action Taken
#### [PERMANENTLY DELETED] Stale Revisions
13 Revisions of `aws-service-liblib-app-dev` have been **permanently deleted**.
- Previously deregistered (inactive) revisions were included in this cleanup.
- They will no longer appear in the AWS Console or Resource Groups.

### Documentation Updated
#### `infrastructure_map.md`
- Verified active VPC references.
- Added note about automatic cleanup of stale Task Definition revisions.
- **Added Detailed Sections**: Included explicit details for **Route Tables** (Public vs Private) and **Security Groups** (ALB vs App) to provide a complete view of the network topology.

#### `naming_convention.md`
- **New File**: Documented the project's standard naming convention (`aws-service-[project]-[env]...`) derived from the Terraform naming patterns.

#### `scripts/aws_inspector/README.md`
- **New File**: Added simple documentation for all the cleanup and inspection scripts found in the `aws_inspector` directory.

#### [RENAMED] Network Resources
Running `apply_naming_tags.py` updated the following resources to match the naming convention:
- **IGW:** `aws-service-liblib-dev-vpc-igw`
- **NAT:** `aws-service-liblib-dev-vpc-nat`
- **Route Tables:** 
    - `aws-service-liblib-dev-vpc-public-rt`
    - `aws-service-liblib-dev-vpc-private-rt` (x2)

> [!NOTE]
> **Task Definition Deletion Status**: You may see deleted Task Definitions in the `DELETE_IN_PROGRESS` state. This is **normal**. AWS permanently deletes them asynchronously. `DELETE_IN_PROGRESS` confirms the deletion command was received and is being processed.
