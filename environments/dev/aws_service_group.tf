module "resource_group" {
  source = "../../modules/resource_group"

  group_name       = "service-liblib-dev-group"
  project_name     = "DigitalHall"
  environment_name = "Development"
}
