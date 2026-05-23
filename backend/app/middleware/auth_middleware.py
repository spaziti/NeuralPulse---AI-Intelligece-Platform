import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
from backend.app.config import settings

logger = logging.getLogger("neuralpulse.audit")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract JWT from Authorization header for audit tracking
        user_context = "Anonymous"
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(
                    token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
                )
                email = payload.get("sub")
                token_type = payload.get("type")
                if email and token_type == "access":
                    user_context = email
            except JWTError:
                # Token expired, malformed or invalid is logged as Anonymous
                pass

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Exclude common system checks from logging to avoid noise
        if request.url.path not in ["/health", "/docs", "/openapi.json"]:
            logger.info(
                f"Audit Log: user={user_context} method={request.method} "
                f"path={request.url.path} status_code={response.status_code} "
                f"process_time={process_time:.4f}s"
            )
            
        return response
