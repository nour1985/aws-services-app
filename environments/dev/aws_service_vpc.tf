module "vpc" {
  source = "../../modules/vpc"

  vpc_name    = "aws-service-liblib-dev-vpc"
  environment = "Development"
}
