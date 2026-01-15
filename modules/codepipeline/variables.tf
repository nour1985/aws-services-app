variable "pipeline_name" {
  description = "Name of the CodePipeline"
  type        = string
}

variable "full_repo_id" {
  description = "GitHub repository ID in format owner/repo"
  type        = string
}

variable "branch" {
  description = "Branch name to build"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "ecr_repository_url" {
  description = "The URL of the ECR repository"
  type        = string
}

variable "ecr_repository_name" {
  description = "The name of the ECR repository"
  type        = string
}

variable "cluster_name" {
  description = "The ECS Cluster name"
  type        = string
}

variable "service_name" {
  description = "The ECS Service name"
  type        = string
}

variable "ecr_repository_arn" {
  description = "The ARN of the ECR repository"
  type        = string
}


