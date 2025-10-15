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
    title="RSS Feed Reader API",
    description="""
## RSS Feed Aggregator Backend API

A comprehensive REST API for managing RSS feed subscriptions and articles.

### Features

* **RSS Source Management**: Add, update, rename, and delete RSS feed sources
* **Article Aggregation**: Automatic fetching and storage of articles with deduplication
* **Custom Icons**: Support for emoji and image URL icons
* **Category Organization**: Organize sources by custom categories
* **Intelligent Caching**: Short-term cache to avoid duplicate feed fetching
* **Background Scheduler**: Automatic RSS feed updates every 15 minutes
* **Rich Metadata**: Favicon extraction, article content, cover images

### API Sections

* **RSS Sources** - Manage RSS feed subscriptions (add, list, update, delete)
* **Articles** - Access and manage fetched articles
* **Validation** - Validate RSS feed URLs before adding

### Authentication

Currently uses a default user ID. Full authentication system coming soon.

### Rate Limiting

Background fetching includes 2-minute delays between sources to respect rate limits.
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "RSS Feed Reader API Support",
        "url": "https://github.com/yourusername/rssfeed",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "RSS Sources",
            "description": "Operations for managing RSS feed subscriptions. Add new sources, update metadata (title, icon, category), and delete sources."
        },
        {
            "name": "Articles",
            "description": "Operations for accessing and managing aggregated articles from RSS feeds."
        },
        {
            "name": "Validation",
            "description": "Validate RSS feed URLs before adding them as sources."
        }
    ]
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
