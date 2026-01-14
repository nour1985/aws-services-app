output "cli_user_arn" {
  description = "ARN of the CLI user"
  value       = aws_iam_user.cli_user.arn
}

output "cli_user_access_key" {
  description = "Access Key ID for the CLI user"
  value       = aws_iam_access_key.cli_user_key.id
}

output "cli_user_secret_key" {
  description = "Secret Key for the CLI user"
  value       = aws_iam_access_key.cli_user_key.secret
  sensitive   = true
}
