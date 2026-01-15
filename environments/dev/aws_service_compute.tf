module "alb" {
  source = "../../modules/alb"

  alb_name       = "aws-service-liblib-dev-alb"
  vpc_id         = module.vpc.vpc_id
  public_subnets = module.vpc.public_subnets
  internal       = false

}

module "ecs_cluster" {
  source = "../../modules/ecs_cluster"

  cluster_name = "aws-service-liblib-dev-cluster"
}

module "fargate" {
  source = "../../modules/fargate"

  service_name = "aws-service-liblib-app-dev"
  cluster_id   = module.ecs_cluster.cluster_id
  vpc_id       = module.vpc.vpc_id
  
  # Networking
  private_subnets       = module.vpc.private_subnets
  alb_security_group_id = module.alb.security_group_id
  target_group_arn      = module.alb.target_group_arns["default-target-group"].arn

  # Task Definition
  task_family     = "aws-service-liblib-app-dev"
  container_image = "nginx:latest" # Placeholder until we build our own
  container_port  = 80
  cpu             = 1024
  memory          = 2048
  
  # IAM
  execution_role_arn = module.iam.ecs_execution_role_arn
}
