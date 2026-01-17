locals {
  # ------------------------------------------------------------------
  # Centralized Project Configuration
  # ------------------------------------------------------------------
  project_name = "Digital-Hall"
  environment  = "Dev"
  
  # Base Naming Pattern: [project]-[environment]
  naming_prefix = "${local.project_name}-${local.environment}"

  # ------------------------------------------------------------------
  # Resource Naming Convention (Hierarchical)
  # ------------------------------------------------------------------
  naming = {
    # --- Networking (Parent: VPC) ---
    vpc             = "${local.naming_prefix}-vpc"
    public_subnet   = "${local.naming_prefix}-vpc-subnet-pub"
    private_subnet  = "${local.naming_prefix}-vpc-subnet-priv"
    igw             = "${local.naming_prefix}-vpc-igw"
    nat_gateway     = "${local.naming_prefix}-vpc-nat"
    route_table     = "${local.naming_prefix}-vpc-rtb"
    
    # --- Security Groups (Parent: Component) ---
    alb_sg          = "${local.naming_prefix}-alb-sg"    
    app_sg          = "${local.naming_prefix}-app-sg"    
    rds_sg          = "${local.naming_prefix}-db-sg"     
    
    # --- Load Balancing (Parent: ALB) ---
    alb             = "${local.naming_prefix}-alb"       
    target_group    = "${local.naming_prefix}-alb-tg"    
    listener        = "${local.naming_prefix}-alb-listener"
    
    # --- Compute & Containers (Parent: Cluster) ---
    ecs_cluster     = "${local.naming_prefix}-cluster"
    ecs_service     = "${local.naming_prefix}-cluster-app"       
    task_definition = "${local.naming_prefix}-task"
    
    # --- Storage (Global/Regional) ---
    s3_assets       = "${local.naming_prefix}-s3-assets"    
    s3_artifacts    = "${local.naming_prefix}-s3-artifacts" 
    ecr_repository  = "${local.naming_prefix}-ecr-repo"
    
    # --- Databases ---
    rds_instance    = "${local.naming_prefix}-rds-db"
    dynamodb_table  = "${local.naming_prefix}-ddb-table"
    
    # --- IAM Roles (Parent: Service) ---
    execution_role  = "${local.naming_prefix}-ecs-exec-role" 
    task_role       = "${local.naming_prefix}-ecs-task-role"
    pipeline_role   = "${local.naming_prefix}-pipe-role"
    build_role      = "${local.naming_prefix}-build-role"
    
    # --- DevOps & CI/CD (Parent: Pipeline) ---
    code_pipeline   = "${local.naming_prefix}-pipeline"
    code_build      = "${local.naming_prefix}-pipeline-build"
    connection      = "${local.naming_prefix}-conn"
    
    # --- Monitoring (Logs) ---
    app_log_group   = "/aws/ecs/${local.naming_prefix}-cluster-app"
    build_log_group = "/aws/codebuild/${local.naming_prefix}-pipeline-build"
    
    # --- Grouping ---
    resource_group  = "${local.naming_prefix}-group" 
  }

  # ------------------------------------------------------------------
  # Common Tags
  # ------------------------------------------------------------------
  common_tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "Terraform"
  }
}
