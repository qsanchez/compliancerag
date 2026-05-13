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
