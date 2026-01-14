output "cli_user_arn" {
  description = "ARN of the CLI user"
  value       = module.iam.arn
}

output "cli_user_access_key" {
  description = "Access Key ID for the CLI user"
  value       = module.iam.access_key_id
}

output "cli_user_secret_key" {
  description = "Secret Key for the CLI user"
  value       = module.iam.secret_access_key
  sensitive   = true
}
