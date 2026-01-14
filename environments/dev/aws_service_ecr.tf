module "ecr" {
  source = "../../modules/ecr"

  repository_name = "aws-service-liblib-backend-dev"
}
