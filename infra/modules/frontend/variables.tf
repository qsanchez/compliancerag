variable "environment" {
  type = string
}

variable "aws_region" {
  description = "AWS region — included in bucket name to avoid cross-region name collisions"
  type        = string
}
