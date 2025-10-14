from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import rss, articles
from app.services.rss_scheduler import get_scheduler
from app.core.database import AsyncSessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app"""
    # Startup
    logger.info("Starting RSS Feed API")

    # Start the RSS scheduler
    scheduler = get_scheduler(AsyncSessionLocal)
    scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down RSS Feed API")
    scheduler.shutdown()


# Create FastAPI app
app = FastAPI(
    title="RSS Feed API",
    description="Backend API for RSS Feed Reader with AI",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rss.router)
app.include_router(articles.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RSS Feed API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
