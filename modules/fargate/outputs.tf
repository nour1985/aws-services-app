output "service_name" {
  description = "Name of the ECS Service"
  value       = aws_ecs_service.this.name
}

output "service_arn" {
  description = "ARN of the ECS Service"
  value       = aws_ecs_service.this.id
}
