variable "alb_name" {
  description = "Name of the ALB"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where the ALB will be provisioned"
  type        = string
}

variable "public_subnets" {
  description = "List of public subnets for the ALB"
  type        = list(string)
}

variable "internal" {
  description = "Whether the ALB is internal or internet-facing"
  type        = bool
  default     = false
}

variable "target_group_port" {
  description = "Port for the ALB Target Group to forward traffic to"
  type        = number
  default     = 80
}

variable "target_group_name" {
  description = "Explicit name for the target group"
  type        = string
  default     = null 
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
