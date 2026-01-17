variable "cli_user_name" {
  description = "Name of the CLI user"
  type        = string
}

variable "execution_role_name" {
  description = "Name for the ECS execution role"
  type        = string
  default     = "ecs-execution-role"
}
