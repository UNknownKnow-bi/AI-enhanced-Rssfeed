# RSS Feed Reader - Project Documentation

## Quick Start

**Status:** Fully functional RSS feed aggregator with AI-powered content classification and summarization.

**Tech Stack:** FastAPI + PostgreSQL + React + TypeScript + DeepSeek AI

**URLs:**
- Frontend: http://localhost:5174
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Start All Services

```bash
# 1. Database
docker-compose up -d

# 2. Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# 3. Frontend
cd frontend
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
npm run dev
```

---

## System Architecture

### Three-Tier Architecture
```
Frontend (React + Vite) ←→ Backend API (FastAPI) ←→ Database (PostgreSQL)
                                    ↓
                          RSS Scheduler + AI Services
```

**Backend:** FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL, APScheduler, feedparser, OpenAI SDK + DeepSeek API

**Frontend:** React 18, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS, Radix UI, react-markdown

**Database:** `users`, `rss_sources` (with categories/icons), `articles` (with AI labels/summaries)

---

## Core Features

### 1. RSS Feed Management

- **Smart Validation**: Real-time URL validation with automatic metadata extraction (title, description, favicon)
- **Intelligent Caching**: 3-minute TTL cache eliminates duplicate fetches (~95% hit rate)
- **Hierarchical Navigation**: 3-level tree (All → Categories → Sources) with unread counts
- **Context Menus**:
  - Sources: Copy link, rename, customize icon, delete (CASCADE)
  - Categories: Batch rename with optimistic UI updates
- **Auto-fetch**: APScheduler runs every 15 minutes with GUID deduplication

**Implementation:** See `backend/app/services/rss_*.py`, `frontend/src/components/FeedSourceList.tsx`

---

### 2. Article Browsing

- **Four-Panel Layout**: Resizable panels (Sources | Tags | Articles | Detail)
- **Infinite Scroll**: 50 articles per page with Intersection Observer auto-loading
- **Multi-Mode Filtering**: All/Category/Source/Tags with real-time updates
- **Status Views**: "全部" (All), "收藏夹" (Favorites), "回收站" (Trash)
- **Security**: DOMPurify sanitization on frontend + backend

**Implementation:** See `frontend/src/components/ArticleList.tsx`, `backend/app/api/articles.py`

---

### 3. AI Content Classification

**DeepSeek Integration** (model: `deepseek-chat`)

- **Automatic Labeling**: Triggered after RSS fetch, processes 3 articles per batch (~2-3s)
- **Three-Tier Tag System**:
  - Identity: #独立开发必备, #博主素材, #双重价值, #可忽略
  - Themes (1-2): #模型动态, #技术教程, #深度洞察, #经验分享, #AI应用, #趣味探索
  - Extra (up to 2): Custom tags (≤6 chars)
  - Special: #VibeCoding (gradient purple)
- **Status Tracking**: pending → processing → done/error
- **Auto Retry**: Every 15 minutes for failed articles

**Configuration** (`.env`):
- `DEEPSEEK_API_KEY` - Required
- `AI_BATCH_SIZE=3` - Articles per batch
- `AI_RETRY_INTERVAL_MINUTES=15` - Retry frequency

**Implementation:** See `backend/app/services/ai_labeler.py`, `frontend/src/components/AILabels.tsx`

---

### 4. AI Article Summarization

**Automatic Summary Generation**

- **Trigger**: After successful labeling (non-#可忽略 articles only)
- **Structure**: Markdown format with "主要观点和论据" + "对我的价值"
- **Smart Filtering**: Skip #可忽略 articles and content <100 chars
- **Concurrency**: Max 4 concurrent requests with semaphore control
- **Auto Retry**: Every 15 minutes for failed summaries

**Frontend Display**:
- Pending: "🏃 AI正在赶来的路上..." with spinner
- Success: Collapsible markdown viewer with copy-to-clipboard
- Error: Error message with timestamp
- Ignored: Hidden

**Configuration** (`.env`):
- `AI_SUMMARY_BATCH_SIZE=3`
- `AI_SUMMARY_TIMEOUT_SECONDS=30`
- `AI_SUMMARY_MAX_CONCURRENT=4`
- `AI_SUMMARY_INTERVAL_MINUTES=15`

**Implementation:** See `backend/app/services/ai_summarizer.py`, `frontend/src/components/ArticleDetail.tsx`

---

### 5. AI Tag Filtering

- **Smart Discovery**: Auto-extract tags from labeled articles
- **Hierarchical UI**: Special → Identity → Theme → Extra grouping
- **Real-time Search**: Fuzzy matching with visual badges
- **AND Logic**: Multiple tags combined as intersection
- **Performance**: PostgreSQL GIN index on JSONB `ai_labels` field

**Implementation:** See `frontend/src/components/TagFilter.tsx`, GIN index migration

---

### 6. Background Scheduling

**APScheduler Jobs** (every 15 minutes):

1. **RSS Fetching**: 2-minute delays between sources, triggers AI labeling after each cycle
2. **AI Label Retry**: Retries failed labels in batches of 3
3. **AI Summary Retry**: Retries failed summaries with concurrency control

**Caching**:
- Backend: 3-min TTL cache for feed validation
- Frontend: TanStack Query with 3-min staleTime

**Implementation:** See `backend/app/services/rss_scheduler.py`

---

## API Reference

**Base URL:** `http://localhost:8000`

**Documentation:**
- Interactive: http://localhost:8000/docs (Swagger)
- ReDoc: http://localhost:8000/redoc
- Full Specs: See [OPENAPI_DOCUMENTATION.md](../OPENAPI_DOCUMENTATION.md)

**Key Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rss/validate` | Validate RSS URL (cached 3 min) |
| POST | `/api/sources` | Create RSS source |
| GET | `/api/sources` | List all sources |
| PATCH | `/api/sources/{id}` | Update source (title/icon/category) |
| DELETE | `/api/sources/{id}` | Delete source + articles (CASCADE) |
| GET | `/api/articles` | List articles (supports filters: `source_id`, `category`, `tags`, `is_favorite`, `is_trashed`) |
| GET | `/api/articles/tags` | Get available AI tags (respects filters) |
| GET | `/api/articles/{id}` | Get article details |
| PATCH | `/api/articles/{id}/read` | Mark as read/unread |
| PATCH | `/api/articles/{id}/favorite` | Toggle favorite |
| POST | `/api/articles/{id}/trash` | Move to trash |
| POST | `/api/articles/{id}/restore` | Restore from trash |
| DELETE | `/api/articles/trash` | Empty trash (permanent delete) |
| GET | `/api/articles/counts` | Get counts (unread/favorite/trashed) |

---

## Key Workflows

### Adding an RSS Source
1. User enters URL → Backend validates + extracts metadata (cached)
2. User edits name/category → Source created
3. Scheduler fetches articles on next 15-minute cycle

### AI Processing Pipeline
1. RSS fetch → Insert articles with `ai_label_status='pending'`
2. AI labeler → Batch process (3 per call) → Update labels
3. If NOT #可忽略 → Trigger summarization (non-blocking)
4. Summarizer → Generate markdown → Save with status
5. Retry schedulers handle failures every 15 minutes

### Browsing & Filtering
1. User selects source/category/view → React Query fetches with filters
2. Infinite scroll loads 50 per page
3. User clicks article → Detail view renders sanitized HTML + AI tags/summary
4. Tag filter updates in real-time based on current context

---

## UI Components

**Layout:**
- `FeedSourceList` - Hierarchical tree + context menus
- `TagFilter` - AI tag browser with search/multi-select
- `ArticleList` - Virtual scroll with infinite loading
- `ArticleDetail` - Sanitized HTML + AI labels + markdown summary

**Dialogs:**
- `AddSourceDialog`, `RenameSourceDialog`, `RenameCategoryDialog`, `EditIconDialog`, `ConfirmDialog`

**AI Components:**
- `AILabels` - Color-coded tag rendering (compact/full modes)
- Markdown summary viewer with copy-to-clipboard

---

## Additional Resources

**Documentation:**
- [FEED_CACHE_IMPLEMENTATION.md](../FEED_CACHE_IMPLEMENTATION.md) - Caching strategy details
- [CONTEXT_MENU_FEATURES.md](../CONTEXT_MENU_FEATURES.md) - Context menu specs
- [OPENAPI_DOCUMENTATION.md](../OPENAPI_DOCUMENTATION.md) - Complete API reference

**Development:**
- Migrations: `backend/alembic/versions/`
- Requirements: `requirements_draft.md`
- Launch Guide: `START_SERVERS.md`
- Summary: `IMPLEMENTATION_SUMMARY.md`

---

## Recent Changes

### 2025-10-18: Article Status Filtering Fix

**Problem:** Clicking "收藏夹" (Favorites) or "回收站" (Trash) didn't update article list.

**Root Cause:**
1. `onClick` handlers in `FeedSourceList` called `setSelectedView()` → then called `setSelectedCategory(null)`
2. `setSelectedCategory()` implementation resets `selectedView` back to `null` → status filter never applied

**Solution:**
- Removed redundant `setSelectedCategory(null)` and `setSelectedSourceId(null)` calls
- `setSelectedView()` already handles these resets internally

**Files Modified:**
- `frontend/src/components/FeedSourceList.tsx` - Simplified onClick handlers
- `frontend/src/components/ArticleList.tsx` - Removed debug code

**Result:** ✅ All status views now work correctly (All/Favorites/Trash)

---

### 2025-10-18: Concurrency Fixes & Trigger Optimization

**Problem:** AsyncSession race conditions causing "session in use" errors.

**Solution:**
- **Per-task sessions**: Each concurrent task creates its own database session
- **Conditional updates**: Status changes use `WHERE` clauses to prevent race conditions
- **Non-blocking API calls**: Wrapped OpenAI SDK calls with `asyncio.to_thread()`
- **Optimized triggers**: Trigger summarization ONCE after all label batches (not per batch)

**Files Modified:**
- `backend/app/services/ai_summarizer.py` - Added `_process_article_by_id()` method
- `backend/app/services/ai_labeler.py` - Optimized trigger logic
- `backend/app/services/rss_scheduler.py` - Removed redundant scheduler

**Benefits:** ✅ No overlapping triggers, cleaner separation, less overhead

---

### 2025-10-17: AI Summarization Feature

**Delivered:**
- ✅ DeepSeek integration for structured markdown summaries
- ✅ Automatic trigger after labeling (non-#可忽略 only)
- ✅ Retry scheduler every 15 minutes
- ✅ Frontend markdown viewer with copy-to-clipboard
- ✅ Concurrency control (max 4 concurrent requests)

**New Files:**
- `backend/alembic/versions/c41751321e50_add_ai_summary_fields.py`
- `backend/app/services/ai_summarizer.py`

**Dependencies Added:**
- `react-markdown`, `remark-gfm`

**Configuration:** See section 4 for `.env` settings

---

**Last Updated:** 2025-10-18
