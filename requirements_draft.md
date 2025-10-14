# RSS Feed AI Reader - Requirements Draft

## Project Overview
A modern RSS feed aggregation platform with AI-powered content summarization, classification, and analysis. The system uses a decoupled frontend-backend architecture with asynchronous task processing for efficient content handling.

---

## Frontend Requirements

### Core Framework & Runtime
- **Framework**: Next.js 14+ (with App Router)
- **Runtime**: Node.js 20+ LTS
- **Package Manager**: pnpm 8+
- **React**: 18.3.1+

### UI & Styling
- **UI Component Library**: Shadcn/ui (latest)
  - Already includes Radix UI primitives (v1.x)
- **CSS Framework**: Tailwind CSS 3.4+
- **Icons**: Lucide React 0.487+
- **Theme Management**: next-themes 0.4+
- **Utility Libraries**:
  - class-variance-authority ^0.7.1
  - clsx (latest)
  - tailwind-merge (latest)

### State Management & Data Fetching
- **Global State**: Zustand 4+
- **Server State/Data Fetching**: TanStack Query (React Query) 5+
- **Form Management**:
  - React Hook Form 7.55+
  - Zod 3+ (for validation)

### Additional UI Components
- **Command Palette**: cmdk 1.1+
- **Carousel**: embla-carousel-react 8.6+
- **Charts**: recharts 2.15+
- **Toast Notifications**: sonner 2+
- **Drawer**: vaul 1.1+
- **Date Picker**: react-day-picker 8.10+
- **Resizable Panels**: react-resizable-panels 2.1+
- **OTP Input**: input-otp 1.4+

### Development Tools
- **TypeScript**: 5.3+
- **Build Tool**: Vite 6.3+ (currently using Vite instead of Next.js default)
- **React Plugin**: @vitejs/plugin-react-swc 3.10+

---

## Backend Requirements

### Core Framework & Runtime
- **Language**: Python 3.11+
- **Web Framework**: FastAPI 0.110+
- **ASGI Server**:
  - Uvicorn 0.27+ (development)
  - Gunicorn 21+ (production, with uvicorn workers)
- **Dependency Management**: Poetry 1.7+

### Database & ORM
- **Primary Database**: PostgreSQL 16+
  - Extensions: pg_trgm, uuid-ossp
- **ORM**: SQLAlchemy 2.0+ (with async support)
- **Migrations**: Alembic 1.13+
- **Database Driver**: asyncpg 0.29+ (async PostgreSQL driver)

### Data Validation & Serialization
- **Validation**: Pydantic V2 (2.5+)

### Async Task Processing
- **Task Queue**: Celery 5.3+
- **Message Broker**: Redis 7+
  - redis-py 5+ (Python Redis client)
- **Caching**: Redis (same instance or separate)

### RSS & Content Processing
- **RSS Parsing**: feedparser 6.0+
- **HTML Processing**: beautifulsoup4 4.12+
- **HTML to Text**: html2text 2024+ (optional)
- **HTTP Client**: httpx 0.27+ (async support)

### AI Integration
- **OpenAI**: openai 1.12+
- **Google Gemini**: google-generativeai 0.4+
- **Anthropic Claude**: anthropic 0.18+ (optional)
- **Self-Hosted Options**:
  - Ollama (development/testing)
  - vLLM (production deployment)

### Additional Backend Tools
- **Environment Management**: python-dotenv 1.0+
- **Async Support**: aioredis 2.0+ or redis[async]
- **CORS**: fastapi-cors (included in FastAPI)
- **Authentication** (future):
  - python-jose 3.3+ (JWT)
  - passlib 1.7+ (password hashing)
  - python-multipart 0.0.9+ (form data)

---

## Infrastructure Requirements

### Database
- **PostgreSQL 16+**
  - Connection pooling: PgBouncer (recommended for production)
  - Backup solution: pg_dump or continuous archiving

### Cache & Message Broker
- **Redis 7+**
  - Persistence: RDB + AOF (recommended)
  - Memory: At least 512MB allocated

### Scheduler
- **Cron Job Manager**:
  - Celery Beat (integrated with Celery)
  - Or system cron (simpler alternative)

### External Services
- **RSSHub** (optional): Self-hosted or public instance
- **LLM APIs**:
  - OpenAI API (GPT-4, GPT-3.5-turbo)
  - Google Gemini API (gemini-pro)
  - Anthropic Claude API (claude-3-sonnet)
  - Or self-hosted models via Ollama/vLLM

---

## Development Environment

### Frontend Development
```json
{
  "node": ">=20.0.0",
  "pnpm": ">=8.0.0",
  "typescript": ">=5.3.0"
}
```

### Backend Development
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0.0"}
asyncpg = "^0.29.0"
alembic = "^1.13.0"
pydantic = "^2.5.0"
celery = "^5.3.0"
redis = "^5.0.0"
feedparser = "^6.0.0"
beautifulsoup4 = "^4.12.0"
httpx = "^0.27.0"
python-dotenv = "^1.0.0"
openai = "^1.12.0"
google-generativeai = "^0.4.0"
```

### Database Setup
- PostgreSQL 16 with the following extensions:
  ```sql
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  CREATE EXTENSION IF NOT EXISTS "pg_trgm";
  ```

---

## Architecture Notes

### Frontend Architecture
- Currently using **Vite + React** instead of Next.js (as per package.json)
- **Migration Consideration**: The architecture design specifies Next.js, but current implementation uses Vite
- **Decision Required**:
  - Option A: Migrate to Next.js 14+ for SSR, API routes, and better SEO
  - Option B: Keep Vite and add a separate API layer

### Backend Services
1. **Main API Service** (FastAPI)
   - Handles REST API requests from frontend
   - CRUD operations for RSS feeds and articles
   - User management and authentication (future)

2. **RSS Scraper Service** (Celery Worker)
   - Scheduled task to fetch RSS feeds
   - Parse XML/JSON content
   - Create AI processing tasks

3. **AI Processing Service** (Celery Worker)
   - Consume tasks from queue
   - Call LLM APIs for summarization and classification
   - Store results in database

4. **Scheduler** (Celery Beat)
   - Trigger RSS scraping every 15 minutes
   - Cleanup old articles periodically

---

## Database Schema (Core Tables)

### feeds
- id (UUID, PK)
- url (TEXT, unique)
- title (VARCHAR)
- description (TEXT)
- last_fetched (TIMESTAMP)
- fetch_interval (INTEGER, minutes)
- is_active (BOOLEAN)
- created_at (TIMESTAMP)

### articles
- id (UUID, PK)
- feed_id (UUID, FK)
- title (VARCHAR)
- url (TEXT, unique)
- content (TEXT)
- summary (TEXT)
- category (VARCHAR)
- keywords (JSONB)
- published_at (TIMESTAMP)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

### processing_tasks
- id (UUID, PK)
- article_id (UUID, FK)
- status (ENUM: pending, processing, completed, failed)
- task_type (ENUM: summarize, classify, extract_keywords)
- result (JSONB)
- error (TEXT)
- created_at (TIMESTAMP)
- completed_at (TIMESTAMP)

---

## API Endpoints (Draft)

### Feeds
- `GET /api/feeds` - List all feeds
- `POST /api/feeds` - Add new feed
- `GET /api/feeds/{id}` - Get feed details
- `PUT /api/feeds/{id}` - Update feed
- `DELETE /api/feeds/{id}` - Delete feed

### Articles
- `GET /api/articles` - List articles (with pagination, filters)
- `GET /api/articles/{id}` - Get article details
- `PUT /api/articles/{id}` - Update article (mark as read, favorite)
- `DELETE /api/articles/{id}` - Delete article

### Processing
- `POST /api/process/scrape` - Manually trigger RSS scrape
- `GET /api/process/status` - Get processing queue status

---

## Environment Variables

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=RSS AI Reader
```

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/rss_feed

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# AI APIs
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...

# App Settings
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
DEBUG=true

# RSS Scraping
SCRAPE_INTERVAL_MINUTES=15
MAX_ARTICLES_PER_FEED=100
```

---

## Deployment Considerations

### Frontend
- **Platform**: Vercel, Netlify, or self-hosted
- **Build**: Static export or SSR depending on Next.js/Vite choice

### Backend
- **Platform**: Docker containers on VPS, AWS ECS, Google Cloud Run
- **Scaling**: Horizontal scaling for API and workers
- **Database**: Managed PostgreSQL (AWS RDS, Google Cloud SQL, Supabase)
- **Cache/Queue**: Managed Redis (AWS ElastiCache, Redis Cloud, Upstash)

### Monitoring & Logging
- **Application Logs**: structlog or loguru
- **Monitoring**: Sentry for error tracking
- **Metrics**: Prometheus + Grafana (optional)

---

## Security Considerations

1. **API Security**
   - CORS configuration
   - Rate limiting (slowapi)
   - API key authentication (future)
   - JWT tokens for user sessions (future)

2. **Database Security**
   - Connection encryption (SSL)
   - Parameterized queries (SQLAlchemy ORM)
   - Regular backups

3. **Secret Management**
   - Environment variables
   - Never commit secrets to git
   - Use secret management services in production (AWS Secrets Manager, etc.)

4. **Content Security**
   - Sanitize HTML content from RSS feeds
   - Prevent XSS attacks
   - Validate and escape user inputs

---

## Testing Requirements

### Frontend
- **Unit Tests**: Vitest or Jest
- **Component Tests**: React Testing Library
- **E2E Tests**: Playwright or Cypress

### Backend
- **Unit Tests**: pytest
- **API Tests**: pytest + httpx
- **Integration Tests**: pytest with test database

---

## Migration Path from Current State

### Immediate Actions
1. ✅ Frontend basic UI exists (Vite + React + Shadcn/ui)
2. ⚠️ **Decision Needed**: Migrate to Next.js or keep Vite?
3. 🔲 Initialize backend project with Poetry
4. 🔲 Set up PostgreSQL and Redis
5. 🔲 Create FastAPI application structure
6. 🔲 Implement database models with SQLAlchemy
7. 🔲 Set up Celery workers and beat scheduler
8. 🔲 Implement RSS scraping logic
9. 🔲 Integrate AI APIs
10. 🔲 Connect frontend to backend APIs

---

## Version Summary

| Component | Version | Notes |
|-----------|---------|-------|
| **Frontend** | | |
| Node.js | 20+ LTS | Runtime |
| Next.js | 14+ | Framework (if migrated) |
| React | 18.3+ | UI Library |
| TypeScript | 5.3+ | Type Safety |
| Tailwind CSS | 3.4+ | Styling |
| pnpm | 8+ | Package Manager |
| **Backend** | | |
| Python | 3.11+ | Language |
| FastAPI | 0.110+ | Web Framework |
| SQLAlchemy | 2.0+ | ORM (Async) |
| Celery | 5.3+ | Task Queue |
| Pydantic | 2.5+ | Validation |
| Poetry | 1.7+ | Dependency Manager |
| **Infrastructure** | | |
| PostgreSQL | 16+ | Database |
| Redis | 7+ | Cache & Broker |
| **AI/ML** | | |
| OpenAI | 1.12+ | GPT Models |
| Google Gen AI | 0.4+ | Gemini Models |
| Anthropic | 0.18+ | Claude Models (optional) |

---

## Next Steps

1. **Confirm architecture decisions**:
   - Vite vs Next.js for frontend
   - AI provider preferences
   - Hosting platform choices

2. **Initialize backend project**:
   ```bash
   poetry new rss-feed-backend
   cd rss-feed-backend
   poetry add fastapi uvicorn sqlalchemy asyncpg alembic pydantic celery redis feedparser beautifulsoup4 httpx python-dotenv openai google-generativeai
   ```

3. **Set up development databases**:
   ```bash
   docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
   docker run -d --name redis -p 6379:6379 redis:7
   ```

4. **Frontend package updates** (if staying with Vite):
   ```bash
   pnpm add @tanstack/react-query zustand zod
   ```

5. **Create project structure and start implementing core features**

---

*Generated: 2025-10-12*
*Project: RSS Feed AI Reader*
