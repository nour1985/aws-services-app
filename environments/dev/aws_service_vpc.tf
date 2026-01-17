module "vpc" {
  source = "../../modules/vpc"

  vpc_name    = local.naming.vpc
  environment = local.environment
}
