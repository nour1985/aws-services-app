module "pipeline" {
  source = "../../modules/codepipeline"

  pipeline_name = "aws-service-liblib-dev-pipeline"
  full_repo_id  = "nour1985/Liblib-Digital-Hall-5" 
  branch        = "master"

  ecr_repository_url  = module.ecr.repository_url
  ecr_repository_name = module.ecr.repository_name
  cluster_name = module.ecs_cluster.cluster_name
  service_name = module.fargate.service_name
  ecr_repository_arn  = module.ecr.repository_arn
}
