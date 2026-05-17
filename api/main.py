import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

app.include_router(health.router)
app.include_router(chat.router)

handler = Mangum(app, lifespan="off")
