module "alb" {
  source = "../../modules/alb"

  alb_name       = local.naming.alb
  vpc_id         = module.vpc.vpc_id
  public_subnets = module.vpc.public_subnets
  internal       = false
  target_group_port = 3000
  target_group_name = local.naming.target_group
  tags              = local.common_tags
}

module "ecs_cluster" {
  source = "../../modules/ecs_cluster"

  cluster_name = local.naming.ecs_cluster
}

module "fargate" {
  source = "../../modules/fargate"

  service_name = local.naming.ecs_service
  cluster_id   = module.ecs_cluster.cluster_id
  vpc_id       = module.vpc.vpc_id
  
  # Networking
  private_subnets       = module.vpc.private_subnets
  alb_security_group_id = module.alb.security_group_id
  target_group_arn      = module.alb.target_group_arns["default-target-group"].arn

  # Task Definition
  task_family     = local.naming.task_definition
  container_image = "${module.ecr.repository_url}:latest"
  container_port  = 3000
  cpu             = 256
  memory          = 512
  
  # IAM
  execution_role_arn = module.iam.ecs_execution_role_arn
  
  # Tags
  tags = local.common_tags
}
