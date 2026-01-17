module "resource_group" {
  source = "../../modules/resource_group"

  group_name       = local.naming.resource_group
  project_name     = local.project_name
  environment_name = local.environment
}
