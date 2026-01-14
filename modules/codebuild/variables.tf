variable "project_name" {
  description = "Name of the CodeBuild project"
  type        = string
}

variable "github_url" {
  description = "URL of the GitHub repository"
  type        = string
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository to push the image to"
  type        = string
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "build_timeout" {
  description = "Build timeout in minutes"
  type        = number
  default     = 60
}

variable "environment_compute_type" {
  description = "Compute type for the build environment"
  type        = string
  default     = "BUILD_GENERAL1_SMALL"
}

variable "environment_image" {
  description = "Docker image for the build environment"
  type        = string
  default     = "aws/codebuild/standard:7.0"
}
