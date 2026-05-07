import os

from config import Settings


def configure(settings: Settings) -> None:
    """Set LangSmith environment variables from settings so @traceable picks them up."""
    if settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        # LangChain older env var — kept for langchain_community compatibility
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)

    tracing = "true" if settings.langchain_tracing_v2 else "false"
    os.environ.setdefault("LANGSMITH_TRACING", tracing)
    os.environ.setdefault("LANGCHAIN_TRACING_V2", tracing)

    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
