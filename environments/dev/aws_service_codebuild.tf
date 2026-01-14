module "codebuild" {
  source = "../../modules/codebuild"

  project_name        = "aws-service-liblib-backend-build"
  github_url          = "https://github.com/nour1985/Liblib-Digital-Hall-5.git"
  ecr_repository_url  = module.ecr.repository_url
  ecr_repository_name = module.ecr.repository_name
}
