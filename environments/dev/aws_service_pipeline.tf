module "pipeline" {
  source = "../../modules/codepipeline"

  pipeline_name = local.naming.code_pipeline
  full_repo_id  = "nour1985/Liblib-Digital-Hall-5" 
  branch        = "master"

  ecr_repository_url  = module.ecr.repository_url
  ecr_repository_name = module.ecr.repository_name
  cluster_name = module.ecs_cluster.cluster_name
  service_name = module.fargate.service_name
  ecr_repository_arn  = module.ecr.repository_arn
  
  connection_name      = local.naming.connection
  artifact_bucket_name = local.naming.s3_artifacts
  
  tags = local.common_tags
}
