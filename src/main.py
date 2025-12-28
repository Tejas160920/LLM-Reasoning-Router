"""FastAPI application entry point.

This module creates and configures the FastAPI application with
all routes, middleware, and lifecycle events.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.v1.router import api_router
from src.config import get_settings
from src.db.session import close_db, init_db

# Get the static files directory
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Handles startup and shutdown events:
    - Startup: Initialize database tables
    - Shutdown: Close database connections
    """
    settings = get_settings()
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Fast model: {settings.fast_model}")
    print(f"Complex model: {settings.complex_model}")
    print(f"Complexity thresholds: low={settings.complexity_threshold_low}, high={settings.complexity_threshold_high}")

    # Initialize database tables
    # In production, use Alembic migrations instead
    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        print("Make sure PostgreSQL is running and DATABASE_URL is correct")

    yield

    # Shutdown
    await close_db()
    print("Shutdown complete")


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI application.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
# Intelligent LLM Reasoning Router

An AI gateway that automatically routes prompts to appropriate models based on complexity analysis.

## Features

- **Smart Routing**: Analyzes prompt complexity and routes to fast or reasoning models
- **Quality Checking**: Validates response quality and escalates if needed
- **Cost Optimization**: Uses cheaper models for simple tasks
- **OpenAI Compatible**: Drop-in replacement for OpenAI chat completions API
- **Full Metrics**: Tracks latency, cost, escalation rates, and more

## How It Works

1. Analyze incoming prompt for complexity signals (keywords, code, math, etc.)
2. Route simple prompts to fast model, complex prompts to reasoning model
3. Check response quality for medium-complexity prompts
4. Automatically escalate to better model if quality is poor
5. Log all metrics for analysis and optimization
        """,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router)

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Root endpoint - serve the UI
    @app.get("/", tags=["root"])
    async def root():
        """Serve the demo UI."""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/v1/health",
            "ui": "UI not found. Place index.html in /static folder.",
        }

    # API info endpoint
    @app.get("/api", tags=["root"])
    async def api_info():
        """API information endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/v1/health",
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
