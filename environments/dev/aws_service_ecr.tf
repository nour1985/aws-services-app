module "ecr" {
  source = "../../modules/ecr"

  repository_name = local.naming.ecr_repository
}
