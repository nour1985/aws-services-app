module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.0"

  name = var.vpc_name
  cidr = var.cidr

  azs             = var.azs
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway = true
  single_nat_gateway = true

  # Explicit Naming to match convention
  igw_tags = {
    Name = "${var.vpc_name}-igw"
  }
  nat_gateway_tags = {
    Name = "${var.vpc_name}-nat"
  }
  public_route_table_tags = {
    Name = "${var.vpc_name}-public-rt"
  }
  private_route_table_tags = {
    Name = "${var.vpc_name}-private-rt"
  }

  tags = {
    Terraform = "true"
    Environment = var.environment
  }
}
