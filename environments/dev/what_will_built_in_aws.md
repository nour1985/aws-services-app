# What Will Be Built in AWS (digital-hall-dev)

Based on the configuration in `environments/dev`, the following resources will be provisioned in **us-east-1**.

## 1. Networking (VPC)
**Goal:** Isolate the application in a secure network with internet access.
*   **VPC**: `digital-hall-dev-vpc` (CIDR: `10.0.0.0/16`)
    *   *Why*: Provides private IP space to launch AWS resources.
*   **Availability Zones**: **2** (`us-east-1a`, `us-east-1b`)
    *   *Why*: Required for ALB and Fargate. 2 AZs ensure if one datacenter acts up, the other works.
*   **NAT Gateway**: `digital-hall-dev-vpc-nat` (Single)
    *   *Why*: Allows private servers (Fargate) to reach the internet (e.g., to pull Docker images) without being exposed to the internet.
    *   *Config*: **One shared NAT** (Cost: ~$32/mo) instead of one per AZ (Cost: ~$64/mo), sufficient for Dev.
*   **Subnets**:
    *   **Public**: `digital-hall-dev-vpc-subnet-pub` (Hosts the ALB).
    *   **Private**: `digital-hall-dev-vpc-subnet-priv` (Hosts the Fargate App).

## 2. Compute (ECS & Fargate)
**Goal:** Run the application container without managing servers.
*   **Cluster**: `digital-hall-dev-cluster`
    *   *Config*: **FARGATE_SPOT** (Weight: 100).
    *   *Why*: Uses spare AWS capacity. **70% Cheaper** than standard Fargate.
*   **Service**: `digital-hall-dev-cluster-app-svc`
    *   *Why*: Ensures 1 copy of your app is *always* running. If it crashes, it restarts it.
*   **Task Definition**: `digital-hall-dev-cluster-app-task`
    *   *Why*: The "Recipe" for the app (Image, CPU, Memory).
    *   *Config*: **0.25 vCPU / 512 MB RAM**. Minimum size to save costs.

## 3. Load Balancing (ALB)
**Goal:** Distribute traffic and provide a single public entry point.
*   **ALB**: `digital-hall-dev-alb` (Internet Facing).
    *   *App URL*: `http://digital-hall-dev-alb-99537214.us-east-1.elb.amazonaws.com`
    *   *Why*: The only "Public Face" of the app. It accepts traffic and safely passes it to the private container.
*   **Target Group**: `digital-hall-dev-alb-tg`
    *   *Role*: **The "Dispatcher"**.
    *   *Why*: It acts as the "List of Active Apps". It connects the ALB (Port 80) to the specific private Fargate tasks (IPs) running your app.
    *   *Config*: **Health Check** (Interval: 15s). If an app task freezes, this Group spots it and tells the ALB to stop sending users there.
*   **Security Groups**:
    *   **ALB SG**: `digital-hall-dev-alb-sg`
        *   *Rule*: "Open Gate" (Allow 80 from World).
    *   **App SG**: `digital-hall-dev-cluster-app-svc-sg`
        *   *Rule*: "VIP Gate" (Allow 3000 **ONLY** from ALB SG).

## 4. DevOps (CI/CD Pipeline)
**Goal:** Automate deployment. "Push to Git -> Live on AWS".
*   **Pipeline**: `digital-hall-dev-pipeline`
    *   *Source*: **GitHub** (`nour1985/Liblib-Digital-Hall-5`) -> Branch: `master`.
    *   *Why*: Removes manual work/errors. Pushing code updates the site handling everything automatically.
*   **CodeBuild**: `digital-hall-dev-pipeline-build`
    *   *Why*: Computers necessary to compile the code and build the Docker image.
    *   *Config*: **Privileged Mode**. Required to run Docker-in-Docker.
*   **S3 Artifacts**: `digital-hall-dev-s3-artifacts`
    *   *Role*: **The "Handoff Area"**.
    *   *Why*: Stores the raw source code `.zip` passed from GitHub -> CodeBuild. It holds the "Ingredients".
*   **Connection**: `digital-hall-dev-conn`
    *   *Why*: Secure link between AWS and your GitHub repository.

## 5. Storage (ECR)
**Goal:** Store the built application images securely.
*   **Repository**: `digital-hall-dev-ecr-repo`
    *   *Role*: **The "Container Registry"**.
    *   *Why*: Stores the final, runnable Docker Image after CodeBuild is finished. It holds the "Cooked Meal" that Fargate runs.
    *   *Config*: **Scan on Push**. Automatically checks your code for security vulnerabilities.

## 6. Access Control (IAM)
**Goal:** Security & Permissions.
*   **CLI User**: `deployer`
    *   *Why*: The identity key for the automated tool/person deploying this infrastructure.
*   **Roles**:
    *   **Pipeline Role**: `digital-hall-dev-pipe-role` (Orchestrates the steps).
    *   **Build Role**: `digital-hall-dev-build-role` (Builds the image).
    *   **Execution Role**: `digital-hall-dev-ecs-exec-role` (Allows Fargate to pull images & write logs).

## 7. Monitoring & Logging
**Goal:** Observability. "What is happening right now?"
*   **App Logs**: `/aws/ecs/digital-hall-dev-cluster-app-svc`
    *   *Why*: Shows the "Console Output" (stdout) of your running application. Essential for debugging crashes.
*   **Build Logs**: `/aws/codebuild/digital-hall-dev-pipeline-build`
    *   *Why*: Shows the step-by-step progress (and errors) of your Docker build process.

## 8. Management
**Goal:** Organization.
*   **Resource Group**: `digital-hall-dev-resource-group`
    *   *Why*: "Shortcuts folder" in AWS Console. Shows only *this* project's resources.
    *   *Tags*: Matches `Project=digital-hall` AND `Environment=dev`.
