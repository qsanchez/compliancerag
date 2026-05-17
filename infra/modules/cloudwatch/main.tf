locals {
  name_prefix = "compliancerag-${var.environment}"
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = local.name_prefix
  dashboard_body = templatefile(
    "${path.root}/../observability/cloudwatch/dashboard.json",
    {
      environment    = var.environment
      aws_region     = var.aws_region
      api_id         = var.api_id
      lambda_name    = var.lambda_function_name
      rds_identifier = var.rds_instance_identifier
      lambda_memory  = var.lambda_memory_mb
    }
  )
}

# Extract per-request latency from structured chat logs → custom metric
resource "aws_cloudwatch_log_metric_filter" "chat_latency" {
  name           = "${local.name_prefix}-chat-latency"
  log_group_name = "/aws/lambda/${local.name_prefix}"
  pattern        = "{ $.latency_ms = * }"

  metric_transformation {
    name          = "ChatLatencyMs"
    namespace     = "ComplianceRAG/${var.environment}"
    value         = "$.latency_ms"
    default_value = "0"
  }
}

# Per-span latency filters (from pipeline_spans structured log)
resource "aws_cloudwatch_log_metric_filter" "retrieve_ms" {
  name           = "${local.name_prefix}-retrieve-ms"
  log_group_name = "/aws/lambda/${local.name_prefix}"
  pattern        = "{ $.retrieve_ms = * }"
  metric_transformation {
    name      = "RetrieveMs"
    namespace = "ComplianceRAG/${var.environment}"
    value     = "$.retrieve_ms"
  }
}

resource "aws_cloudwatch_log_metric_filter" "rerank_ms" {
  name           = "${local.name_prefix}-rerank-ms"
  log_group_name = "/aws/lambda/${local.name_prefix}"
  pattern        = "{ $.rerank_ms = * }"
  metric_transformation {
    name      = "RerankMs"
    namespace = "ComplianceRAG/${var.environment}"
    value     = "$.rerank_ms"
  }
}

resource "aws_cloudwatch_log_metric_filter" "generate_ms" {
  name           = "${local.name_prefix}-generate-ms"
  log_group_name = "/aws/lambda/${local.name_prefix}"
  pattern        = "{ $.generate_ms = * }"
  metric_transformation {
    name      = "GenerateMs"
    namespace = "ComplianceRAG/${var.environment}"
    value     = "$.generate_ms"
  }
}

# Token and cost filters
resource "aws_cloudwatch_log_metric_filter" "input_tokens" {
  name           = "${local.name_prefix}-input-tokens"
  log_group_name = "/aws/lambda/${local.name_prefix}"
  pattern        = "{ $.input_tokens = * }"
  metric_transformation {
    name      = "InputTokens"
    namespace = "ComplianceRAG/${var.environment}"
    value     = "$.input_tokens"
  }
}

resource "aws_cloudwatch_log_metric_filter" "output_tokens" {
  name           = "${local.name_prefix}-output-tokens"
  log_group_name = "/aws/lambda/${local.name_prefix}"
  pattern        = "{ $.output_tokens = * }"
  metric_transformation {
    name      = "OutputTokens"
    namespace = "ComplianceRAG/${var.environment}"
    value     = "$.output_tokens"
  }
}

resource "aws_cloudwatch_log_metric_filter" "cost_usd" {
  name           = "${local.name_prefix}-cost-usd"
  log_group_name = "/aws/lambda/${local.name_prefix}"
  pattern        = "{ $.cost_usd = * }"
  metric_transformation {
    name      = "CostUsd"
    namespace = "ComplianceRAG/${var.environment}"
    value     = "$.cost_usd"
  }
}

# Injection blocked and no-answer rate
resource "aws_cloudwatch_log_metric_filter" "injection_blocked" {
  name           = "${local.name_prefix}-injection-blocked"
  log_group_name = "/aws/lambda/${local.name_prefix}"
  pattern        = "{ $.injection_blocked IS TRUE }"
  metric_transformation {
    name          = "InjectionBlocked"
    namespace     = "ComplianceRAG/${var.environment}"
    value         = "1"
    default_value = "0"
  }
}

# Alarm: online RAGAS faithfulness < 0.80 over 1 hour
resource "aws_cloudwatch_metric_alarm" "online_faithfulness" {
  alarm_name          = "${local.name_prefix}-online-faithfulness-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  threshold           = 0.80
  alarm_description   = "Online RAGAS faithfulness dropped below 0.80 — retrieval or generation quality may have degraded"
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "faith"
    return_data = true
    metric {
      namespace   = "ComplianceRAG/${var.environment}"
      metric_name = "OnlineFaithfulness"
      period      = 3600
      stat        = "Average"
    }
  }

  tags = {
    Environment = var.environment
  }
}

# Alarm: Lambda error rate > 5% over two consecutive 5-minute windows
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  alarm_name          = "${local.name_prefix}-lambda-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 5
  alarm_description   = "Lambda error rate exceeded 5% for 2 consecutive 5-minute windows"
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "error_rate"
    expression  = "errors / MAX([errors, invocations]) * 100"
    label       = "Error Rate %"
    return_data = true
  }

  metric_query {
    id = "errors"
    metric {
      namespace   = "AWS/Lambda"
      metric_name = "Errors"
      dimensions  = { FunctionName = var.lambda_function_name }
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id = "invocations"
    metric {
      namespace   = "AWS/Lambda"
      metric_name = "Invocations"
      dimensions  = { FunctionName = var.lambda_function_name }
      period      = 300
      stat        = "Sum"
    }
  }

  tags = {
    Environment = var.environment
  }
}
