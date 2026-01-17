module "iam" {
  source = "../../modules/iam"

  cli_user_name       = var.cli_user_name
  execution_role_name = local.naming.execution_role
}
