# Infrastructure Map (Digital Hall - Dev)

**Built on:** 2026-01-17
**Region:** us-east-1
**Environment:** Dev
**Status:** ✅ Fully Deployed & Tagged

## 🚀 App URL
**[Click Here to Open App](http://digital-hall-dev-alb-99537214.us-east-1.elb.amazonaws.com/)**
*(Note: Use HTTP, not HTTPS)*

## 🏛️ Architecture Overview

```mermaid
graph TD
    User((User)) --> ALB[Load Balancer]
    ALB --> TG[Target Group]
    TG --> ECS[Fargate Service (Private)]
    
    subgraph VPC
        ALB
        ECS
    end
    
    GitHub --> Pipeline
    Pipeline --> CodeBuild
    CodeBuild --> ECR[ECR Registry]
    ECR --> ECS
```

## 1. Network Layer (VPC)
| Resource Type | Name (ID) | Console Link |
| :--- | :--- | :--- |
| **VPC** | `digital-hall-dev-vpc` | [View VPC](https://us-east-1.console.aws.amazon.com/vpc/home?region=us-east-1#vpcs:search=digital-hall-dev-vpc) |
| **Public Subnets** | `digital-hall-dev-vpc-subnet-pub` (x2) | [View Subnets](https://us-east-1.console.aws.amazon.com/vpc/home?region=us-east-1#subnets:search=digital-hall-dev-vpc-subnet-pub) |
| **Private Subnets** | `digital-hall-dev-vpc-subnet-priv` (x2) | [View Subnets](https://us-east-1.console.aws.amazon.com/vpc/home?region=us-east-1#subnets:search=digital-hall-dev-vpc-subnet-priv) |
| **Internet Gateway** | `digital-hall-dev-vpc-igw` | [View IGW](https://us-east-1.console.aws.amazon.com/vpc/home?region=us-east-1#igws:search=digital-hall-dev-vpc-igw) |
| **NAT Gateway** | `digital-hall-dev-vpc-nat` | [View NAT GW](https://us-east-1.console.aws.amazon.com/vpc/home?region=us-east-1#NatGateways:search=digital-hall-dev-vpc-nat) |
| **Route Tables** | `digital-hall-dev-vpc-public-rt`<br>`digital-hall-dev-vpc-private-rt`<br>`digital-hall-dev-vpc-default` | [View Route Tables](https://us-east-1.console.aws.amazon.com/vpc/home?region=us-east-1#RouteTables:search=digital-hall-dev) |

## 2. Access Layer (Load Balancing)
| Resource Type | Name | Console Link |
| :--- | :--- | :--- |
| **ALB** | `digital-hall-dev-alb` | [View Load Balancer](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#LoadBalancers:search=digital-hall-dev-alb) |
| **Public URL** | `digital-hall-dev-alb-99537214.us-east-1.elb.amazonaws.com` | [Open App](http://digital-hall-dev-alb-99537214.us-east-1.elb.amazonaws.com) |
| **Listener** | HTTP:80 (ARN-based identifier) | [View Listeners](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#LoadBalancers:search=digital-hall-dev-alb) |
| **Target Group** | `digital-hall-dev-alb-tg` | [View Target Group](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#TargetGroups:search=digital-hall-dev-alb-tg) |
| **ALB Security Group** | `digital-hall-dev-alb-sg` | [View Security Group](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#SecurityGroups:search=digital-hall-dev-alb-sg) |
| ↳ Ingress Rule | Allow HTTP (80) from `0.0.0.0/0` | *Sub-resource (not taggable)* |
| ↳ Egress Rule | Allow All to `0.0.0.0/0` | *Sub-resource (not taggable)* |

## 3. Compute Layer (Container)
| Resource Type | Name | Console Link |
| :--- | :--- | :--- |
| **ECS Cluster** | `digital-hall-dev-cluster` | [View Cluster](https://us-east-1.console.aws.amazon.com/ecs/v2/clusters/digital-hall-dev-cluster/services?region=us-east-1) |
| **ECS Service** | `digital-hall-dev-cluster-app-svc` | [View Service](https://us-east-1.console.aws.amazon.com/ecs/v2/clusters/digital-hall-dev-cluster/services/digital-hall-dev-cluster-app-svc?region=us-east-1) |
| **Task Definition** | `digital-hall-dev-app-task` | [View Task Def](https://us-east-1.console.aws.amazon.com/ecs/v2/task-definitions/digital-hall-dev-app-task?region=us-east-1) |
| **App Security Group** | `digital-hall-dev-cluster-app-svc-sg` | [View Security Group](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#SecurityGroups:search=digital-hall-dev-cluster-app-svc-sg) |
| ↳ Ingress Rule | Allow TCP (3000) from ALB SG only | *Sub-resource (not taggable)* |
| ↳ Egress Rule | Allow All to `0.0.0.0/0` | *Sub-resource (not taggable)* |

## 4. Pipeline Layer (CI/CD)
| Resource Type | Name | Console Link |
| :--- | :--- | :--- |
| **CodePipeline** | `digital-hall-dev-pipeline` | [View Pipeline](https://us-east-1.console.aws.amazon.com/codesuite/codepipeline/pipelines/digital-hall-dev-pipeline/view?region=us-east-1) |
| **CodeBuild Project** | `digital-hall-dev-pipeline-build` | [View Build Project](https://us-east-1.console.aws.amazon.com/codesuite/codebuild/projects/digital-hall-dev-pipeline-build/history?region=us-east-1) |
| **CodeStar Connection** | `digital-hall-dev-conn` | [View Connection](https://us-east-1.console.aws.amazon.com/codesuite/settings/connections?region=us-east-1) |
| ↳ GitHub Repo | `nour1985/Liblib-Digital-Hall-5` (master) | [View on GitHub](https://github.com/nour1985/Liblib-Digital-Hall-5) |
| **S3 Artifacts Bucket** | `digital-hall-dev-s3-artifacts` | [View S3 Bucket](https://s3.console.aws.amazon.com/s3/buckets/digital-hall-dev-s3-artifacts?region=us-east-1) |

## 5. Storage Layer (Container Registry)
| Resource Type | Name | Console Link |
| :--- | :--- | :--- |
| **ECR Repository** | `digital-hall-dev-ecr-repo` | [View ECR Repo](https://us-east-1.console.aws.amazon.com/ecr/repositories/private/216989128401/digital-hall-dev-ecr-repo?region=us-east-1) |

## 6. Observability (Monitoring & Logs)
| Resource Type | Name | Console Link |
| :--- | :--- | :--- |
| **App Logs** | `/aws/ecs/digital-hall-dev-cluster-app-svc` | [View Logs](https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Fecs$252Fdigital-hall-dev-cluster-app-svc) |
| **Build Logs** | `/aws/codebuild/digital-hall-dev-pipeline-build` | [View Logs](https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Fcodebuild$252Fdigital-hall-dev-pipeline-build) |

## 7. Access Control (IAM)
| Resource Type | Name | Purpose |
| :--- | :--- | :--- |
| **CLI User** | `deployer` | Terraform deployment user |
| **ECS Execution Role** | `digital-hall-dev-ecs-exec-role` | Allows Fargate to pull images & write logs |
| **Pipeline Role** | `digital-hall-dev-pipeline-role` | Orchestrates CI/CD stages |
| **Build Role** | `digital-hall-dev-pipeline-codebuild-role` | Builds Docker images & pushes to ECR |

## 8. Management (Organization)
| Resource Type | Name | Console Link |
| :--- | :--- | :--- |
| **Resource Group** | `digital-hall-dev-resource-group` | [View Resource Group](https://us-east-1.console.aws.amazon.com/resource-groups/group/digital-hall-dev-resource-group?region=us-east-1) |

---

## 📝 Notes

### Tagging Status
- ✅ **All major resources** are properly tagged with `Name`, `Project`, `Environment`, and `ManagedBy`
- ⚠️ **Sub-resources** (Security Group Rules, Route Table Associations) show as "not tagged" - this is normal AWS behavior

### Resource Naming Convention
All resources follow the pattern: `digital-hall-dev-{resource-type}`

### Cost Optimization
- Using **FARGATE_SPOT** (70% cheaper than standard Fargate)
- **Single NAT Gateway** (~$32/mo vs ~$64/mo for multi-AZ)
- **Minimal compute** (0.25 vCPU / 512 MB RAM)
