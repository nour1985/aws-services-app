module "resource_group" {
  source = "../../modules/resource_group"

  group_name       = "service-liblib-prod-group"
  project_name     = "DigitalHall"
  environment_name = "Production"
}
