output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs (one per AZ)"
  value       = aws_subnet.private[*].id
}

output "private_route_table_id" {
  description = "Route table ID for the private subnets — used by the S3 gateway endpoint"
  value       = aws_route_table.private.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs (one per AZ, route to IGW) — used for publicly-accessible RDS"
  value       = aws_subnet.public[*].id
}
