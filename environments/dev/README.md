# Development Environment Infrastructure

## Overview
This directory defines the infrastructure for the **Development** environment of the AWS Services App (DigitalHall Project). The infrastructure is managed using Terraform and focuses on establishing a secure networking foundation and resource management strategy.

## Resources & Aims

The following resources are provisioned in this environment:

### 1. Virtual Private Cloud (VPC)
*   **Resource Name**: `aws-service-liblib-dev-vpc`
*   **Aim**: To provide an isolated virtual network environment for deploying secure applications.
*   **Configuration**:
    *   **CIDR Block**: `10.0.0.0/16`
    *   **Availability Zones**: `us-east-1a`
    *   **Subnets**:
        *   **Public Subnet** (`10.0.101.0/24`): Intended for resources that require direct public internet access (e.g., Load Balancers, Jump Hosts). Includes a NAT Gateway.
        *   **Private Subnet** (`10.0.1.0/24`): Intended for internal resources (e.g., Application Servers, Databases). Instances here can access the internet via the NAT Gateway but cannot be reached directly from the internet.
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
*   **Resource Name**: `aws-service-liblib-backend-dev`
*   **Aim**: To store and manage Docker container images for the application backend (Next.js).
*   **Configuration**:
    *   **Mutability**: `MUTABLE` (images can be overwritten).
    *   **Scan on Push**: `Enabled` (automatically scans images for vulnerabilities when pushed).

### 4. Application Load Balancer (ALB)
*   **Resource Name**: `aws-service-liblib-dev-alb`
*   **Aim**: To distribute incoming HTTP traffic across multiple targets (Fargate tasks) in different Availability Zones (currently single AZ for Dev).
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

### 6. AWS CodeBuild (CI/CD)
*   **Resource Name**: `aws-service-liblib-backend-build`
*   **Aim**: To automate the build and delivery pipeline for the application. It fetches code, builds the Docker image, and pushes it to ECR.
*   **Configuration**:
    *   **Source**: GitHub Repository (`https://github.com/nour1985/Liblib-Digital-Hall-5.git`).
    *   **Trigger**: Webhook enabled for `PUSH` events to the `master` branch.
    *   **Environment**: Linux container running Docker (Privileged Mode enabled).
    *   **Build Spec**: Inline YAML defining login, build, and push commands.


## Architecture & Connectivity

The infrastructure follows a standard tiered VPC network architecture:

1.  **Internet Access**: The **Internet Gateway** is attached to the VPC to handle traffic to and from the internet.
2.  **Public Zone**: The **Public Subnet** has a route table that directs external traffic to the Internet Gateway. It hosts the **NAT Gateway**.
3.  **Private Zone**: The **Private Subnet** uses a route table that directs internet-bound traffic to the **NAT Gateway** in the public subnet. This ensures private resources can update or connect to external APIs without being exposed.
4.  **Application Hosting**: The **ALB** sits in the Public Subnet to accept user traffic. It forwards requests to **Fargate Tasks** running securely in the Private Subnet.
4.  **Application Hosting**: The **ALB** sits in the Public Subnet to accept user traffic. It forwards requests to **Fargate Tasks** running securely in the Private Subnet.
5.  **CI/CD Pipeline**: **CodeBuild** is triggered by a push to GitHub. It builds the container and pushes the artifact to **ECR**. Fargate can then pull this new image (manual service update or automation required for auto-deploy).
6.  **Tag-based Management**: All resources created in this environment automatically inherit default tags (defined in `provider.tf`), which allows the **Resource Group** to automatically identify and include them.

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

        ECR[ECR: aws-service-liblib-backend-dev]
        style ECR fill:#e1bee7,stroke:#8e24aa

        CodeBuild[CodeBuild Project]
        style CodeBuild fill:#ffab91,stroke:#d84315

        
        %% Logical connection
        RG -.->|Groups by Tags| VPC
        RG -.->|Groups by Tags| NAT
        RG -.->|Groups by Tags| IGW
        RG -.->|Groups by Tags| ECR
        RG -.->|Groups by Tags| ALB
        RG -.->|Groups by Tags| Fargate
        
        %% Dependency
        Fargate -.->|Pulls Image| ECR

        %% CI/CD Flow
        Developer(Developer) -- Push --> GitHub(GitHub Repo)
        GitHub -- Webhook --> CodeBuild
        CodeBuild -- Push Image --> ECR
    end
```
