# Network module outputs
output "vpc_id" {
  description = "The ID of the custom VPC"
  value       = aws_vpc.main.id
}

output "subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "sg_id" {
  description = "The security group ID exposing web services"
  value       = aws_security_group.web.id
}
