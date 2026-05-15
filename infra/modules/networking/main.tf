locals {
  name_prefix = "compliancerag-${var.environment}"
}

data "aws_availability_zones" "available" {
  state = "available"
}

# ── VPC ───────────────────────────────────────────────────────────────────────

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = local.name_prefix
    Environment = var.environment
  }
}

# ── Private subnets (one per AZ, no internet route) ──────────────────────────
# Lambda and RDS live here. AWS services are reached via VPC endpoints.

resource "aws_subnet" "private" {
  count             = var.az_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${local.name_prefix}-private-${count.index + 1}"
    Environment = var.environment
  }
}

# ── Route table (private — no internet gateway) ───────────────────────────────
# S3 gateway endpoint route is injected directly by aws_vpc_endpoint.s3
# in the root module via route_table_ids.

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name        = "${local.name_prefix}-private"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
