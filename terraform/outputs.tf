# Root Terraform outputs
output "vpc_id" {
  description = "The ID of the custom VPC"
  value       = module.network.vpc_id
}

output "subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.network.subnet_ids
}

output "bucket_name" {
  description = "The S3 logs bucket name"
  value       = aws_s3_bucket.logs.bucket
}
