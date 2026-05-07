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
    vector_store: str = "chroma"
    database_url: str = ""
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # LLMOps
    langsmith_api_key: str = ""
    langsmith_project: str = "compliancerag"
    langchain_tracing_v2: bool = False

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
