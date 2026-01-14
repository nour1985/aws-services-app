resource "aws_iam_user" "cli_user" {
  name = var.cli_user_name

  tags = {
    Description = "IAM user for CLI access"
  }
}

resource "aws_iam_access_key" "cli_user_key" {
  user = aws_iam_user.cli_user.name
}

resource "aws_iam_user_policy_attachment" "admin_access" {
  # BE CAREFUL: Granting AdministratorAccess. 
  # For production, strictly scope permissions (Least Privilege).
  user       = aws_iam_user.cli_user.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
