from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import get_settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        # Skip auth for health check
        if request.url.path == "/health":
            return await call_next(request)  # type: ignore[arg-type]

        settings = get_settings()
        # When no API key is configured, allow all requests (local dev)
        if not settings.api_key:
            return await call_next(request)  # type: ignore[arg-type]

        key = request.headers.get("X-API-Key", "")
        if key != settings.api_key:
            return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401)

        return await call_next(request)  # type: ignore[arg-type]
