from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AWS
    aws_region: str = "eu-west-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    bedrock_model_id: str = ""
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # Vector store
    database_url: str = ""

    # Analytics
    athena_database: str = "compliancerag"
    athena_table_fines: str = "gdpr_fines"
    athena_s3_output: str = ""
    athena_s3_data_bucket: str = ""

    # Reranker
    reranker_enabled: bool = True

    # Online evaluation
    online_eval_sample_rate: float = 0.1

    # API
    api_key: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def litellm_model(self) -> str:
        return f"bedrock/{self.bedrock_model_id}"

    @property
    def litellm_embedding_model(self) -> str:
        return f"bedrock/{self.bedrock_embedding_model_id}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
