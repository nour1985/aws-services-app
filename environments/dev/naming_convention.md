# Naming Conventions

This document outlines the standard naming conventions used for infrastructure resources in the `liblib` project.

## Standard Pattern
The primary naming convention follows this structure:

`aws-service-[project]-[component]-[environment]-[resource_suffix]`

### Components
| Segment | Value | Description |
| :--- | :--- | :--- |
| **Prefix** | `aws-service` | Standard prefix for all AWS resources. |
| **Project** | `liblib` | The main project identifier. |
| **Component** | `app`, `digital-hall`, `pipeline` | The specific application or function. |
| **Environment** | `dev` | Deployment stage (e.g., `dev`, `prod`). |
| **Suffix** | `vpc`, `alb`, `cluster` | underlying resource type. |

## Resource Specifics

### Networking
*   **VPC**: `aws-service-liblib-dev-vpc`
    *   Pattern: `aws-service-[project]-[environment]-vpc`
*   **ALB**: `aws-service-liblib-dev-alb`
    *   Pattern: `aws-service-[project]-[environment]-alb`

### Compute (ECS/Fargate)
*   **Cluster**: `aws-service-liblib-dev-cluster`
    *   Pattern: `aws-service-[project]-[environment]-cluster`
*   **Service**: `aws-service-liblib-app-dev`
    *   Pattern: `aws-service-[project]-app-[environment]`
*   **Task Definition**: `aws-service-liblib-app-dev`
    *   Shape: Matches Service Name.

### Storage & Artifacts
*   **ECR Repository**: `aws-service-liblib-digital-hall-dev`
    *   Pattern: `aws-service-[project]-[app_name]-[environment]`

### CI/CD
*   **CodePipeline**: `aws-service-liblib-dev-pipeline`
    *   Pattern: `aws-service-[project]-[environment]-pipeline`
*   **CodeBuild**: `aws-service-liblib-dev-pipeline-build` (Inferred)

### Grouping
*   **Resource Group**: `service-liblib-dev-group`
    *   **Exception**: Starts with `service-` instead of `aws-service-`.
    *   Pattern: `service-[project]-[environment]-group`

## Tags
Resources should generally share the following tags (where supported via modules):
*   `Environment = "Development"`
*   `Project = "Liblib"` (or specific component name)
