from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.logging_config import setup_logging
from backend.app.redis_client import redis_client
from backend.app.routers import auth, news, websocket
from backend.app.middleware.auth_middleware import AuditMiddleware

# Setup logging system
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lifecycle startup actions
    await redis_client.connect()
    yield
    # Lifecycle shutdown actions
    await redis_client.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade AI News Intelligence Platform API Backend",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS Middleware configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit log tracking middleware
app.add_middleware(AuditMiddleware)

# Register API Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(news.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")


@app.get("/health", tags=["System Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
