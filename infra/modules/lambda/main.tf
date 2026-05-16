locals {
  name_prefix = "compliancerag-${var.environment}"
}

# ── ECR repository ────────────────────────────────────────────────────────────

resource "aws_ecr_repository" "this" {
  name                 = local.name_prefix
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# ── IAM ───────────────────────────────────────────────────────────────────────

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name_prefix}-lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "lambda" {
  # CloudWatch Logs
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }

  # VPC — create/describe/delete ENIs for VPC-attached Lambda
  statement {
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface",
    ]
    resources = ["*"]
  }

  # Bedrock — invoke models for LLM generation, embeddings, and reranking
  statement {
    actions   = ["bedrock:InvokeModel", "bedrock:Rerank"]
    resources = ["*"]
  }

  # S3 — read/write Athena query results
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:GetBucketLocation", "s3:ListBucket"]
    resources = ["*"]
  }

  # Athena
  statement {
    actions   = ["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults"]
    resources = ["*"]
  }

  # Glue catalog (required by Athena)
  statement {
    actions   = ["glue:GetDatabase", "glue:GetTable", "glue:GetPartitions"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "compliancerag-lambda-policy"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda.json
}

# ── Security group ────────────────────────────────────────────────────────────

resource "aws_security_group" "lambda" {
  name        = "${local.name_prefix}-lambda"
  description = "ComplianceRAG Lambda - outbound to RDS and AWS services"
  vpc_id      = var.vpc_id

  egress {
    description = "PostgreSQL to RDS"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "HTTPS to AWS services (Bedrock, S3, Athena) and internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${local.name_prefix}-lambda"
    Environment = var.environment
  }
}

# Allow Lambda to connect to RDS
resource "aws_security_group_rule" "lambda_to_rds" {
  description              = "ComplianceRAG Lambda inbound"
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.lambda.id
  security_group_id        = var.rds_security_group_id
}

# ── CloudWatch log group ──────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name_prefix}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}

# ── Lambda function ───────────────────────────────────────────────────────────
# Deploy sequence:
#   1. terraform apply -target=module.lambda.aws_ecr_repository.this
#   2. task deploy:build && task deploy:push ECR_REPO=<ecr_repository_url>
#   3. terraform apply

resource "aws_lambda_function" "this" {
  function_name = local.name_prefix
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.this.repository_url}:latest"
  architectures = ["arm64"]
  timeout       = var.lambda_timeout_s
  memory_size   = var.lambda_memory_mb

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      VECTOR_STORE                 = "pgvector"
      AWS_REGION_NAME              = var.aws_region
      BEDROCK_MODEL_ID             = var.bedrock_model_id
      BEDROCK_EMBEDDING_MODEL_ID   = var.bedrock_embedding_model_id
      DATABASE_URL                 = var.database_url
      ATHENA_DATABASE              = var.athena_database
      ATHENA_TABLE_FINES           = var.athena_table_fines
      ATHENA_S3_OUTPUT             = var.athena_s3_output
      ATHENA_S3_DATA_BUCKET        = var.athena_s3_data_bucket
      API_KEY                      = var.api_key
      LANGSMITH_API_KEY            = var.langsmith_api_key
      LANGSMITH_PROJECT            = var.langsmith_project
      LANGCHAIN_TRACING_V2         = tostring(var.langchain_tracing_v2)
      RERANKER_ENABLED             = "true"
      LITELLM_LOCAL_MODEL_COST_MAP = "True"
      MPLCONFIGDIR                 = "/tmp"
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  # Image URI is managed by task deploy:update-lambda, not by Terraform
  lifecycle {
    ignore_changes = [image_uri]
  }

  tags = {
    Environment = var.environment
  }
}
