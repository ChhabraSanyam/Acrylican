from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .routers import auth, images, content, products, oauth, posts, platforms, preferences, sales, engagement, analytics, privacy, health, monitoring
from .middleware import SecurityMiddleware, RequestValidationMiddleware, LoggingMiddleware, CSRFProtectionMiddleware
from .monitoring_middleware import MonitoringMiddleware, DatabaseMonitoringMiddleware, SecurityMonitoringMiddleware
from .monitoring import initialize_monitoring, shutdown_monitoring
from .monitoring_config import logger, metrics_collector
from .security_hardening import configure_security_middleware
import logging

# Configure basic logging (will be enhanced by structured logger)
logging.basicConfig(
    level=logging.INFO if settings.environment == "production" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Artisan Promotion Platform API")
    await initialize_monitoring()
    logger.info("Monitoring system initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Artisan Promotion Platform API")
    await shutdown_monitoring()
    logger.info("Monitoring system shutdown complete")

app = FastAPI(
    title="Artisan Promotion Platform API",
    description="API for managing artisan product promotion across multiple platforms",
    version="1.0.0",
    debug=settings.environment == "development",
    lifespan=lifespan
)

# Add monitoring middleware (order matters - most specific first)
app.add_middleware(MonitoringMiddleware)
app.add_middleware(DatabaseMonitoringMiddleware)
app.add_middleware(SecurityMonitoringMiddleware)

# Add security middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CSRFProtectionMiddleware)

# Configure CORS (after security middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Explicit methods for security
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],  # Explicit headers
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
)

# Configure security middleware for production
app = configure_security_middleware(app)

# Include routers
app.include_router(health.router)  # Health checks first
app.include_router(monitoring.router)  # Production monitoring endpoints
app.include_router(auth.router)
app.include_router(images.router)
app.include_router(content.router)
app.include_router(products.router)
app.include_router(oauth.router)
app.include_router(posts.router)
app.include_router(platforms.router)
app.include_router(preferences.router)
app.include_router(sales.router)
app.include_router(engagement.router)
app.include_router(analytics.router)
app.include_router(privacy.router)



# Basic health endpoint (detailed health checks are in /health router)
@app.get("/")
async def root():
    return {
        "message": "Artisan Promotion Platform API",
        "version": "1.0.0",
        "status": "running"
    }