# AWS Inspector & Cleanup Scripts

This directory contains utility scripts to help maintain, clean up, and standardize your AWS environment.

## 🛠️ Specialized Utilities

These stand-alone scripts are designed for specific cleanup tasks.

### 1. Naming & Standardization
*   **`apply_naming_tags.py`**
    *   **Purpose**: Rename network resources to match the project convention (`aws-service-liblib-dev-vpc-...`).
    *   **Target**: Internet Gateways, NAT Gateways, Route Tables.
    *   **Usage**: `python apply_naming_tags.py --vpc-name <your-vpc-name> [--force]`

### 2. VPC Cleanup
*   **`find_unused_vpcs.py`**
    *   **Purpose**: Scans for VPCs that appear unused (no active Network Interfaces).
    *   **Usage**: `python find_unused_vpcs.py`
*   **`delete_vpc.py`**
    *   **Purpose**: Safely deletes a specific VPC and all its dependencies (Subnets, IGWs, Route Tables).
    *   **Safety**: Aborts if active resources (ENIs) are found.
    *   **Usage**: `python delete_vpc.py --vpc-id <vpc-id> [--force]`

### 3. ECS Task Definition Cleanup
*   **`find_unused_task_definitions.py`**
    *   **Purpose**: Identifies Task Definitions that are active, recent (backups), or stale.
    *   **Usage**: `python find_unused_task_definitions.py`
*   **`delete_task_definitions.py`**
    *   **Purpose**: Permanently deletes stale Task Definition revisions to keep the console clean.
    *   **Logic**: Keeps Active revisions + Top 2 most recent revisions. Deletes the rest.
    *   **Usage**: `python delete_task_definitions.py [--force]`

---

## 🔍 Generic Resource Inspector

*   **`inspector.py`** (Class) & **`main.py`** (CLI)
    *   **Purpose**: A more advanced tool designed to scan specific **AWS Resource Groups**.
    *   **Logic**: uses CloudWatch metrics (connections, requests) to determine if resources in a group are actually being used.
    *   **Features**:
        *   Assess relevance (Keep vs Delete) based on usage heuristics.
        *   Supports Dry Run and Report generation.
