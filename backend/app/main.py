from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .routers import auth, images, content, products, oauth, posts, platforms, preferences, sales, engagement, analytics, privacy
from .middleware import SecurityMiddleware, RequestValidationMiddleware, LoggingMiddleware, CSRFProtectionMiddleware
from .security_hardening import configure_security_middleware
import logging
import gc

# Configure basic logging (will be enhanced by structured logger)
logging.basicConfig(
    level=logging.WARNING if settings.environment == "production" else logging.INFO,  # Reduced logging for memory
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Simple application lifespan manager."""
    # Startup
    gc.collect()
    yield
    # Shutdown
    gc.collect()

app = FastAPI(
    title="Acrylican API",
    description="API for managing artisan product promotion across multiple platforms",
    version="1.0.0",
    debug=settings.environment == "development",
    lifespan=lifespan
)

# Add security middleware (temporarily simplified for debugging)
# app.add_middleware(SecurityMiddleware)
# app.add_middleware(RequestValidationMiddleware)
app.add_middleware(LoggingMiddleware)
# app.add_middleware(CSRFProtectionMiddleware)

# Configure security middleware for production (includes CORS)
app = configure_security_middleware(app)

# Include routers
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



# Basic endpoints
@app.get("/")
async def root():
    return {
        "message": "Acrylican API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "acrylican-api",
        "version": "1.0.0"
    }