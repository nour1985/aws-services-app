output "arn" {
  value = aws_iam_user.cli_user.arn
}

output "access_key_id" {
  value = aws_iam_access_key.cli_user_key.id
}

output "secret_access_key" {
  value = aws_iam_access_key.cli_user_key.secret
  sensitive = true
}
