import structlog
from fastapi import FastAPI

from api.middleware.auth import APIKeyMiddleware
from api.middleware.logging import LoggingMiddleware
from api.routers import chat, health

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

app = FastAPI(title="ComplianceRAG", version="0.1.0")

app.add_middleware(APIKeyMiddleware)
app.add_middleware(LoggingMiddleware)

app.include_router(health.router)
app.include_router(chat.router)
