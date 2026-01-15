# Development Environment Infrastructure

## Overview
This directory defines the infrastructure for the **Development** environment of the AWS Services App (DigitalHall Project). The infrastructure is managed using Terraform and focuses on establishing a secure networking foundation and resource management strategy.

## File Organization

The Terraform configuration is organized by **logical function** rather than cost:

*   **`aws_service_vpc.tf`**: Network foundation (VPC, Subnets, NAT, IGW)
*   **`aws_service_compute.tf`**: Application runtime stack (ALB, ECS Cluster, Fargate Service)
*   **`aws_service_ecr.tf`**: Container image registry
*   **`aws_service_pipeline.tf`**: CI/CD automation (CodePipeline, CodeBuild)
*   **`aws_service_iam.tf`**: Identity and access management
*   **`aws_service_group.tf`**: Resource grouping and tagging

> **Why group ALB + ECS + Fargate together?**  
> These three components form a single **application delivery stack**: ALB routes traffic → ECS orchestrates → Fargate runs containers. Grouping them in `aws_service_compute.tf` makes the dependency chain clear and simplifies lifecycle management.

## Cost Breakdown

Understanding the monthly costs for this environment:

| Resource | Monthly Cost | Can Scale to Zero? | Notes |
|----------|-------------|-------------------|-------|
| **VPC, Subnets, IGW** | Free | N/A | Core networking has no charge |
| **NAT Gateway** | ~$32 | ❌ No | Charged per hour + data transfer |
| **Application Load Balancer** | ~$16 | ❌ No | Charged per hour + LCU usage |
| **Fargate Tasks** | ~$10-15 | ✅ Yes | Set `desired_count = 0` to stop |
| **ECR Storage** | Free* | N/A | First 500MB free, then $0.10/GB |
| **CodePipeline** | Free* | N/A | First pipeline free, runs on-demand |
| **Security Groups, IAM** | Free | N/A | No charge for these resources |

**Total Running Cost**: ~$58-63/month  
**Minimum Cost (scaled down)**: ~$16/month (ALB only, with Fargate at 0 and NAT deleted)

### Cost Optimization Tips

*   **Development Hours Only**: Scale Fargate to 0 when not actively developing
*   **Remove NAT Gateway**: Delete when not needed (saves $32/month, but breaks private subnet internet access)
*   **Keep ALB Running**: At $16/month, it's worth keeping for instant wake-up capability



## Resources & Aims

The following resources are provisioned in this environment:

### 1. Virtual Private Cloud (VPC)
*   **Resource Name**: `aws-service-liblib-dev-vpc`
*   **Aim**: To provide an isolated virtual network environment for deploying secure applications.
*   **Configuration**:
    *   **CIDR Block**: `10.0.0.0/16`
    *   **Availability Zones**: `us-east-1a`, `us-east-1b`
    *   **Subnets**:
        *   **Public Subnets** (`10.0.101.0/24`, `10.0.102.0/24`): Intended for resources that require direct public internet access (e.g., Load Balancers, Jump Hosts). Includes a NAT Gateway.
        *   **Private Subnets** (`10.0.1.0/24`, `10.0.2.0/24`): Intended for internal resources (e.g., Application Servers, Databases). Instances here can access the internet via the NAT Gateway but cannot be reached directly from the internet.
    *   **Gateways**:
        *   **Internet Gateway (IGW)**: Enables connectivity between the VPC and the internet.
        *   **NAT Gateway**: Located in the Public Subnet, it allows instances in the Private Subnet to initiate outbound traffic to the internet while preventing inbound traffic.

### 2. AWS Resource Group
*   **Resource Name**: `service-liblib-dev-group`
*   **Aim**: To logically group all resources associated with this project and environment for easier management, monitoring, and automation in the AWS Console.
*   **Mechanism**: It groups resources based on the following tags:
    *   `Project`: `DigitalHall`
    *   `Environment`: `Development`

### 3. Elastic Container Registry (ECR)
*   **Resource Name**: `aws-service-liblib-digital-hall-dev`
*   **Aim**: To store and manage Docker container images for the application backend (Next.js).
*   **Configuration**:
    *   **Mutability**: `MUTABLE` (images can be overwritten).
    *   **Scan on Push**: `Enabled` (automatically scans images for vulnerabilities when pushed).

### 4. Application Load Balancer (ALB)
*   **Resource Name**: `aws-service-liblib-dev-alb`
*   **Aim**: To distribute incoming HTTP traffic across multiple targets (Fargate tasks) in different Availability Zones (Multi-AZ).
*   **Configuration**:
    *   **Type**: `Application` (Layer 7).
    *   **Placement**: `Public Subnet` (Internet-facing).
    *   **Listener**: HTTP/80 forwarding to the Fargate service.

### 5. Amazon ECS & Fargate
*   **Cluster Name**: `aws-service-liblib-dev-cluster`
*   **Service Name**: `aws-service-liblib-app-dev`
*   **Aim**: To orchestrate and run the application containers without managing servers.
*   **Configuration**:
    *   **Launch Type**: `FARGATE_SPOT` (Cost-optimized serverless compute).
    *   **Placement**: `Private Subnet` (Secure, no direct internet access).
    *   **Container Insights**: `Enabled` (For monitoring).
    *   **Task Definition**: Configured for `nginx` (placeholder) with 256 CPU / 512 MB Memory.

### 6. CodePipeline (CI/CD)
*   **Pipeline Name**: `aws-service-liblib-dev-pipeline`
*   **Aim**: To automate the delivery of application updates from code commit to deployment.
*   **Workflow**:
    1.  **Source**: Triggers on push to `master` branch in GitHub.
    2.  **Build**: Uses **CodeBuild** (`aws-service-liblib-dev-pipeline-build`) to build the Docker image using `buildspec.yml`, push it to ECR, and trigger an ECS deployment.

## Architecture & Connectivity

The infrastructure follows a standard tiered VPC network architecture with a fully automated CI/CD pipeline:

1.  **Internet Access**: The **Internet Gateway** is attached to the VPC to handle traffic to and from the internet.
2.  **Public Zone**: The **Public Subnet** has a route table that directs external traffic to the Internet Gateway. It hosts the **NAT Gateway**.
3.  **Private Zone**: The **Private Subnet** uses a route table that directs internet-bound traffic to the **NAT Gateway** in the public subnet. This ensures private resources can update or connect to external APIs without being exposed.
4.  **Application Hosting**: The **ALB** sits in the Public Subnet to accept user traffic. It forwards requests to **Fargate Tasks** running securely in the Private Subnet.
5.  **Tag-based Management**: All resources created in this environment automatically inherit default tags (defined in `provider.tf`), which allows the **Resource Group** to automatically identify and include them.
6.  **Continuous Deployment**: Any push to the `master` branch triggers **CodePipeline**. **CodeBuild** builds the Docker container, pushes it to **ECR**, and forces **ECS Fargate** to update the service with the new image.

### Architecture Diagram

```mermaid
graph TB
    subgraph AWS_Cloud [AWS Cloud (us-east-1)]
        style AWS_Cloud fill:#f9f9f9,stroke:#333,stroke-width:2px
        
        subgraph VPC [VPC: aws-service-liblib-dev-vpc]
            style VPC fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
            
            IGW[Internet Gateway]
            style IGW fill:#ffcc80,stroke:#e65100
            
            subgraph Public_Subnet [Public Subnet (10.0.101.0/24)]
                style Public_Subnet fill:#e0f2f1,stroke:#00695c
                NAT[NAT Gateway]
                style NAT fill:#ffeb3b,stroke:#fbc02d
                ALB[ALB: aws-service-liblib-dev-alb]
                style ALB fill:#64b5f6,stroke:#1565c0
            end
            
            subgraph Private_Subnet [Private Subnet (10.0.1.0/24)]
                style Private_Subnet fill:#fff3e0,stroke:#ef6c00
                Fargate[Fargate Service: aws-service-liblib-app-dev]
                style Fargate fill:#ffcc80,stroke:#e65100,stroke-dasharray: 5 5
            end
            
            %% Routing connections
            IGW <--> Public_Subnet
            Public_Subnet -- Route to IGW --> IGW
            Private_Subnet -- Route to NAT --> NAT
            NAT -- Outbound Traffic --> IGW
            
            %% App Flow
            Internet((User)) --> IGW
            IGW --> ALB
            ALB --> Fargate
        end
        
        subgraph Management
            RG[Resource Group: service-liblib-dev-group]
            style RG fill:#e8eaf6,stroke:#3f51b5
        end

        ECR[ECR: aws-service-liblib-digital-hall-dev]
        style ECR fill:#e1bee7,stroke:#8e24aa

        subgraph CI_CD [CI/CD Pipeline]
            style CI_CD fill:#fff3e0,stroke:#e65100,stroke-dasharray: 5 5
            Pipeline[CodePipeline]
            style Pipeline fill:#ffcc80,stroke:#e65100
            Build[CodeBuild]
            style Build fill:#ffab91,stroke:#d84315
        end
        
        %% Logical connection
        RG -.->|Groups by Tags| VPC
        RG -.->|Groups by Tags| NAT
        RG -.->|Groups by Tags| IGW
        RG -.->|Groups by Tags| ECR
        RG -.->|Groups by Tags| ALB
        RG -.->|Groups by Tags| Fargate
        RG -.->|Groups by Tags| Pipeline
        
        %% Dependency
        Fargate -.->|Pulls Image| ECR

        %% CI/CD Flow
        Developer(Developer) -- Push --> GitHub(GitHub Repo)
        GitHub -- Triggers --> Pipeline
        Pipeline -- Orchestrates --> Build
        Build -- Pushes Image --> ECR
        Build -- Updates Service --> Fargate
    end
```
