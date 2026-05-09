output "workgroup_name" {
  description = "Athena workgroup name"
  value       = aws_athena_workgroup.this.name
}

output "database_name" {
  description = "Glue/Athena database name"
  value       = aws_glue_catalog_database.this.name
}
