output "dns_name" {
  description = "The DNS name of the load balancer"
  value       = module.alb.dns_name
}

output "arn" {
  description = "The ARN of the load balancer"
  value       = module.alb.arn
}

output "security_group_id" {
  description = "The ID of the security group created for the ALB"
  value       = module.alb.security_group_id
}

output "target_group_arns" {
  description = "ARNs of the target groups"
  value       = module.alb.target_groups
}
