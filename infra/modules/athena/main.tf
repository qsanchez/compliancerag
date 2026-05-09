locals {
  name_prefix = "compliancerag-${var.environment}"
  common_tags = merge({ Project = "compliancerag", Environment = var.environment, ManagedBy = "terraform" }, var.tags)
}

# ── Athena workgroup ──────────────────────────────────────────────────────────
resource "aws_athena_workgroup" "this" {
  name          = local.name_prefix
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.athena_results_bucket}/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = local.common_tags
}

# ── Glue catalog database (used by Athena as its metastore) ──────────────────
resource "aws_glue_catalog_database" "this" {
  name        = var.database_name
  description = "ComplianceRAG analytics — GDPR enforcement data"
}

# ── Glue catalog table: gdpr_fines (Parquet, partitioned by country) ─────────
resource "aws_glue_catalog_table" "gdpr_fines" {
  name          = "gdpr_fines"
  database_name = aws_glue_catalog_database.this.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "classification"            = "parquet"
    "parquet.compression"       = "SNAPPY"
    "EXTERNAL"                  = "TRUE"
  }

  storage_descriptor {
    location      = "s3://${var.analytics_data_bucket}/analytics/gdpr_fines/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters            = { "serialization.format" = "1" }
    }

    columns {
      name = "decision_date"
      type = "date"
    }
    columns {
      name = "country"
      type = "string"
    }
    columns {
      name = "authority"
      type = "string"
    }
    columns {
      name = "fine_amount_eur"
      type = "bigint"
    }
    columns {
      name = "controller"
      type = "string"
    }
    columns {
      name = "sector"
      type = "string"
    }
    columns {
      name = "articles_violated"
      type = "string"
    }
    columns {
      name = "violation_type"
      type = "string"
    }
    columns {
      name = "summary"
      type = "string"
    }
  }
}
