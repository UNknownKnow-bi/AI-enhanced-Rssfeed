# RSS Feed Reader - Project Documentation

## Table of Contents
- [Quick Start](#-quick-start)
- [System Architecture](#-system-architecture)
- [Core Features](#-core-features)
- [API Reference](#-api-reference)
- [Key Workflows](#-key-workflows)
- [UI Components](#-ui-components)
- [Future Enhancements](#-future-enhancements)
- [Additional Resources](#-additional-resources)

---

## ✅ Quick Start

**Status:** Fully implemented RSS feed aggregator with AI-powered content classification and summarization. Built with FastAPI (backend), PostgreSQL (database), and React + TypeScript (frontend).

**URLs:**
- Frontend: http://localhost:5174
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Prerequisites
- Docker (for PostgreSQL)
- Python 3.11+ with venv
- Node.js 18+ (managed via nvm)

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

## 🏗️ System Architecture

### Three-Tier Architecture
```
Frontend (React + Vite) ←→ Backend API (FastAPI) ←→ Database (PostgreSQL)
                                    ↓
                          RSS Scheduler + AI Labeler
```

### Tech Stack

**Backend:** FastAPI (async/await), SQLAlchemy 2.0 (async), Alembic, PostgreSQL, APScheduler, feedparser, httpx, OpenAI SDK + DeepSeek API, DOMPurify, pydantic, cachetools, asyncio (semaphore concurrency control)

**Frontend:** React 18, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS 3.4, Radix UI, react-resizable-panels, DOMPurify, lucide-react, react-markdown, remark-gfm

**Database Schema:**
- `users` - User accounts
- `rss_sources` - Feed subscriptions with categories and icons
- `articles` - Fetched articles with CASCADE deletion, AI labels (JSONB), and AI summaries (TEXT with markdown)

---

## 📦 Core Features

### 1. RSS Feed Management

**Adding & Validation**
- Real-time URL validation with automatic metadata extraction (title, description, favicon)
- Intelligent 3-minute TTL cache eliminates duplicate fetches (50% faster, ~95% cache hit rate)
- Automatic `limit=999` parameter added for maximum article retrieval
- Custom source naming and category organization

**Hierarchical Navigation (3 Levels)**
```
全部 ▼                      (All feeds)
  Tech ▼                    (Categories)
    ├─ Source 1             (Individual sources)
    └─ Source 2
  Sports ▼
    └─ Source 3
```

**Filtering & Context Menus**
- Click "全部"/category/source for different views with unread counts
- Mutually exclusive selection with visual highlighting
- **Sources** (right-click): Copy RSS link, rename, customize icon, delete (CASCADE)
- **Categories** (right-click): Rename (batch updates with retry logic and optimistic UI)

**Implementation:** [rss_parser.py](backend/app/services/rss_parser.py), [rss_service.py](backend/app/services/rss_service.py), [feed_cache.py](backend/app/services/feed_cache.py), AddSourceDialog, FeedSourceList components

---

### 2. Article Browsing & Reading

**Four-Panel Resizable Layout**
- Panel 1 (Left): RSS sources (15-30%)
- Panel 2: AI Tag filter (collapsible, 256px fixed width)
- Panel 3 (Middle): Article list (20-50%)
- Panel 4 (Right): Article details (min 30%)
- Drag-to-resize with independent scrolling (Radix UI ScrollArea)

**Article List (Infinite Scroll)**
- Multi-mode filtering: all/category/source with 50 articles per page
- Intersection Observer auto-loading, sorted by date (newest first)
- Shows source icon, title, timestamp, and AI tags
- Auto-refresh every 60 seconds with intelligent cache invalidation

**Article Detail View**
- Sanitized HTML rendering (XSS protection via DOMPurify)
- Cover images with lazy loading and error fallback
- External link to original article with complete AI label display

**Implementation:** [articles.py](backend/app/api/articles.py), ArticleList/ArticleDetail components, TanStack Query infinite scroll

---

### 3. AI-Powered Content Classification

**Automatic Labeling**
- DeepSeek AI integration (model: `deepseek-chat`) with OpenAI SDK
- Batch processing: 3 articles per call (~$0.015 per 30 articles, ~2-3s per batch)
- Triggered after RSS fetch cycles with exponential backoff retry (1s, 2s)
- Status tracking: pending → processing → done/error
- **Automatic Retry**: Dedicated scheduler job runs every 15 minutes to retry failed articles
  - Queries articles with `ai_label_status='error'` in batches of 3
  - 10-second delays between batches for rate limiting
  - Concurrency protection via status locking (prevents duplicate processing)
  - Per-article error handling (partial success support)
  - Continues until all error articles processed

**Three-Tier Tag System**
- **第一层 (Identity)**: #独立开发必备, #博主素材, #双重价值, #可忽略
- **第二层 (Themes, 1-2 tags)**: #模型动态, #技术教程, #深度洞察, #经验分享, #AI应用, #趣味探索
- **第三层 (Extra, up to 2)**: Custom tags (≤6 chars)
- **Special**: #VibeCoding (gradient purple)

**Display Modes**
- **Compact (ArticleCard)**: Max 3 color-coded tags + "+N" overflow
- **Full (ArticleDetail)**: All tags with "AI分类标签" header
- **Status**: "🏃 赶来的路上" (processing), "❌寄掉了" (error)

**Configuration:** Set `DEEPSEEK_API_KEY` in `.env`, configure retry settings:
- `AI_BATCH_SIZE` (default: 3) - articles per API call
- `AI_RETRY_INTERVAL_MINUTES` (default: 15) - retry scheduler frequency
- `AI_RETRY_BATCH_DELAY_SECONDS` (default: 10) - delay between retry batches

**Implementation:** [ai_labeler.py](backend/app/services/ai_labeler.py), [rss_scheduler.py](backend/app/services/rss_scheduler.py), [AILabels.tsx](frontend/src/components/AILabels.tsx), JSONB fields (`ai_labels`, `ai_label_status`, `ai_label_error`)

---

### 4. AI-Powered Article Summarization

**Automatic Summary Generation**
- DeepSeek AI integration for generating structured Markdown summaries
- Triggered after successful AI labeling (non-#可忽略 articles only)
- Dual-trigger system: post-labeling + scheduled scan every 15 minutes
- Batch processing: 3 articles per batch with concurrency control (max 4 concurrent requests)
- Status tracking: pending → success/error/ignored
- Timeout: 30 seconds per request with automatic retry (1s, 2s exponential backoff)
- **Automatic Retry**: Dedicated scheduler job runs every 15 minutes to retry failed summaries

**Summary Structure (Markdown)**
```markdown
## 主要观点和论据 (Key Arguments)
- **观点一**: [核心观点]
  - 论据: [数据/规格/方法]

## 对我的价值
### 作为独立开发者
- [技术启发/工具/架构思路]

### 作为科技博主
- [素材/案例/话题价值]
```

**Smart Content Filtering**
- Auto-skip articles marked as #可忽略 (status: ignored)
- Auto-skip articles with content <100 chars (status: ignored)
- Content length limit: 8000 chars (token optimization)

**Frontend Display**
- **Pending**: "🏃 AI正在赶来的路上..." with loading spinner
- **Success**: Collapsible markdown viewer with copy-to-clipboard button
- **Error**: Error message with retry timestamp
- **Ignored**: Section hidden entirely

**Configuration:** Add to `.env`:
- `AI_SUMMARY_BATCH_SIZE` (default: 3) - articles per batch
- `AI_SUMMARY_TIMEOUT_SECONDS` (default: 30) - API timeout
- `AI_SUMMARY_MAX_CONCURRENT` (default: 4) - max concurrent requests
- `AI_SUMMARY_INTERVAL_MINUTES` (default: 15) - processing scheduler frequency
- `AI_SUMMARY_RETRY_INTERVAL_MINUTES` (default: 15) - retry scheduler frequency

**Implementation:** [ai_summarizer.py](backend/app/services/ai_summarizer.py), [rss_scheduler.py](backend/app/services/rss_scheduler.py), [ArticleDetail.tsx](frontend/src/components/ArticleDetail.tsx), database fields (`ai_summary`, `ai_summary_status`, `ai_summary_error`, `ai_summary_generated_at`)

---

### 5. AI Tag Filtering

**Smart Tag Discovery**
- Automatic tag extraction from articles with `ai_label_status='done'`
- Respects current source/category filter context
- Real-time updates as new articles are labeled
- Returns deduplicated, sorted tag list

**Filter UI (Four-Panel Layout)**
- **Left Panel**: Tag filter with hierarchical grouping
  - Special: #VibeCoding (gradient purple highlight)
  - Identity Tags: #独立开发必备, #博主素材, #双重价值, #可忽略
  - Theme Tags: #模型动态, #技术教程, #深度洞察, #经验分享, #AI应用, #趣味探索
  - Extra Tags: Custom AI-generated tags
- **Search**: Real-time tag search with fuzzy matching
- **Selection**: Multi-select with visual badges and count display
- **Clear**: One-click clear all selected tags

**Filter Logic (AND)**
- Multiple tags combined with AND logic (intersection)
- PostgreSQL GIN index on `ai_labels` JSONB field for optimal performance
- Uses `@>` containment operator with proper JSONB type binding
- Special handling for `#VibeCoding` boolean flag

**Tag Normalization**
- All tags automatically prefixed with `#` before storage
- Normalization applied in `ai_labeler.py::normalize_tag()`
- Database migration ensures existing tags are normalized
- Consistent format across API, database, and UI

**Technical Details**
- **Backend**: JSONB containment queries via SQLAlchemy
  ```python
  Article.ai_labels.op('@>')({"identities": [tag]})
  ```
- **Frontend**: TanStack Query for tag list caching
- **Database**: GIN index (`idx_articles_ai_labels_gin`) for fast JSONB searches
- **Migration**: `c85b81cde9f1_normalize_existing_tags.py` ensures data integrity

**Implementation:** [articles.py](backend/app/api/articles.py), [TagFilter.tsx](frontend/src/components/TagFilter.tsx), [useQueries.ts](frontend/src/hooks/useQueries.ts), GIN index migration

---

### 6. Background Processing & Scheduling

**RSS Fetching**
- APScheduler runs every 15 minutes with 2-minute delays between sources (rate limiting)
- GUID-based deduplication, automatic unread count updates
- Error tolerance: failed fetches don't block other sources
- Triggers AI labeling for pending articles after each fetch cycle

**AI Labeling Retry Scheduler**
- Dedicated APScheduler job runs every 15 minutes to retry error articles
- Early exit if no error articles found (efficient)
- Processes all error articles in batches of 3 with 10-second delays
- Concurrency protection via status locking

**AI Summary Schedulers**
- **Pending Summaries**: Every 15 minutes, scans for articles with `ai_summary_status='pending'` and `ai_label_status='done'`
- **Error Retry**: Every 15 minutes, retries articles with `ai_summary_status='error'`
- Concurrent processing with semaphore control (max 4 simultaneous API calls)
- Non-blocking triggers via `asyncio.create_task()`

**Caching Strategy**
- Backend: TTL cache (3 min) with LRU eviction for feed validation
- Frontend: TanStack Query with 60-second auto-refresh and optimistic updates

**Implementation:** [rss_scheduler.py](backend/app/services/rss_scheduler.py), [ai_labeler.py](backend/app/services/ai_labeler.py), [ai_summarizer.py](backend/app/services/ai_summarizer.py), cachetools TTLCache, TanStack Query invalidation

---

### 7. Security & Data Integrity

**HTML Sanitization**
- DOMPurify (frontend + backend) with whitelist approach (safe tags only)
- Blocks `<script>`, `<iframe>`, event handlers
- Auto-adds `target="_blank"` and `rel="noopener noreferrer"` to external links

**Timezone-Aware DateTime**
- PostgreSQL: `TIMESTAMP WITH TIME ZONE`
- Python: `datetime.now(timezone.utc)` + Pydantic ISO 8601 serialization

**Data Integrity**
- User ownership validation, CASCADE deletion, transaction rollback on errors
- Original RSS URLs preserved (parameter manipulation only at fetch time)

---

## 📚 API Reference

**Base URL:** `http://localhost:8000`

### Key Endpoints

**RSS Sources**
- `POST /api/rss/validate` - Validate feed URL (cached 3 min)
- `POST /api/sources` - Create source (reuses cache)
- `GET /api/sources` - List all user sources
- `PATCH /api/sources/{id}` - Update title/icon/category
- `DELETE /api/sources/{id}` - Delete source + articles (CASCADE)

**Articles**
- `GET /api/articles?source_id={uuid}&category={string}&tags={comma_separated}` - List with filters, pagination, AI labels
  - `tags`: Comma-separated AI tags (AND logic), e.g., `tags=#独立开发必备,#技术教程`
  - Filters: source_id > category > tags (combined with AND)
  - Returns 50 articles per page with AI labels
- `GET /api/articles/tags?source_id={uuid}&category={string}` - Get available AI tags
  - Returns deduplicated tags from articles with `ai_label_status='done'`
  - Respects source/category filter context
- `GET /api/articles/{id}` - Get details with AI labels
- `PATCH /api/articles/{id}/read` - Mark as read (planned)

**Interactive Docs:** http://localhost:8000/docs (Swagger), http://localhost:8000/redoc (ReDoc)
**Full API Specs:** See [OPENAPI_DOCUMENTATION.md](../OPENAPI_DOCUMENTATION.md)

---

## 🔄 Key Workflows

### Adding an RSS Source
1. User enters URL → `POST /api/rss/validate` (backend adds `limit=999`, caches result)
2. User edits name/category → `POST /api/sources` (reuses cache)
3. Scheduler fetches articles on next 15-minute cycle

### Automatic Article Fetching & AI Labeling
1. APScheduler triggers → Query sources → Fetch RSS (2-min delays)
2. Check GUID deduplication → Insert new articles → Update unread counts
3. Trigger AI labeling → Process batches of 3 → Save labels to database

### Browsing Articles
1. User clicks "全部"/category/source → `GET /api/articles` with filters
2. Infinite scroll loads 50 per page → User selects article → `GET /api/articles/{id}`
3. Detail view displays sanitized content + full AI tags
4. Auto-refresh every 60 seconds

### Filtering Articles by AI Tags
1. User selects source/category (optional) → `GET /api/articles/tags` fetches available tags
2. TagFilter component displays tags grouped by type (Special/Identity/Theme/Extra)
3. User searches/selects tags → Multi-select with visual badges
4. `GET /api/articles?tags=#独立开发必备,#技术教程` filters with AND logic
5. PostgreSQL GIN index performs efficient JSONB containment queries
6. Article list updates with filtered results

### AI Summary Generation Workflow
1. RSS fetch completes → Articles inserted with `ai_summary_status='pending'`
2. AI labeler processes articles → Updates labels
3. If label is NOT #可忽略 → Triggers summary generation (non-blocking)
4. Summarizer checks content length (skip if <100 chars) → Updates status to 'processing'
5. Calls DeepSeek API with custom prompt → Generates structured Markdown
6. Validates response → Saves summary with status 'success'
7. User views article → Frontend renders markdown with react-markdown
8. Scheduler runs every 15 minutes → Processes any pending/error summaries

---

## 🎨 UI Components

**Layout**
- FeedSourceList - Hierarchical tree + context menus
- TagFilter - AI tag filtering with search and grouping
- ArticleList - Infinite scroll with filtering
- ArticleDetail - Sanitized HTML + AI tags
- SourceIcon - Favicon/emoji display

**Dialogs**
- AddSourceDialog, RenameSourceDialog, RenameCategoryDialog, EditIconDialog, ConfirmDialog, Toaster

**AI Components**
- AILabels - Tag rendering (compact/full modes)
- TagFilter - Hierarchical tag browser with:
  - Real-time search input
  - Grouped display (Special/Identity/Theme/Extra)
  - Multi-select with badge UI
  - Selected tags panel with clear action
  - Color-coded tags matching AILabels

**Design:** See `figma_frontendbasic/` folder

---

## 🔄 Future Enhancements

- ✅ ~~AI article summarization~~ (Implemented - see section 4)
- User authentication (email login)
- Read/unread tracking with bold styling
- ✅ ~~Filter by AI labels~~ (Implemented - see section 5)
- Favorites/bookmarks functionality
- Full-text search, advanced filters (date range, keywords)
- Export to PDF/Markdown/JSON
- Mobile apps (iOS/Android), browser extension
- RSS feed recommendations based on reading habits
- Tag-based analytics and insights dashboard

---

## 📚 Additional Resources

**Documentation**
- [FEED_CACHE_IMPLEMENTATION.md](../FEED_CACHE_IMPLEMENTATION.md) - TTL cache details
- [CONTEXT_MENU_FEATURES.md](../CONTEXT_MENU_FEATURES.md) - Context menu specs
- [OPENAPI_DOCUMENTATION.md](../OPENAPI_DOCUMENTATION.md) - API documentation

**Development**
- Migrations: [backend/alembic/versions/](backend/alembic/versions/)
- Tech Stack: `requirements_draft.md`
- Launch: `START_SERVERS.md`
- Summary: `IMPLEMENTATION_SUMMARY.md`

---

## 📝 Recent Changes

### 2025-10-17: AI-Powered Article Summarization Feature

**Summary:** Implemented comprehensive AI-powered article summarization system with DeepSeek integration, automatic scheduling, error retry mechanism, and frontend markdown rendering.

#### Backend Changes

**Database Migration:**
- 📄 **NEW**: `backend/alembic/versions/c41751321e50_add_ai_summary_fields.py`
  - Added 4 columns: `ai_summary`, `ai_summary_status`, `ai_summary_error`, `ai_summary_generated_at`
  - Created index on `ai_summary_status` for efficient querying

**Models & Schemas:**
- 📝 **UPDATED**: `backend/app/models/article.py` (lines 35-39)
  - Added AI summary fields to Article model
- 📝 **UPDATED**: `backend/app/schemas/article.py` (lines 32-35, 59-62)
  - Added summary fields to `ArticleResponse` and `ArticleListResponse`

**Service Layer:**
- 📄 **NEW**: `backend/app/services/ai_summarizer.py` (500+ lines)
  - `AISummarizer` class with DeepSeek API integration
  - Concurrency control via asyncio.Semaphore (max 4 concurrent)
  - Smart content filtering (skip #可忽略 and short articles)
  - Batch processing with error handling and retry logic
  - Custom prompt for structured markdown summaries
- 📝 **UPDATED**: `backend/app/services/ai_labeler.py` (lines 226-260, 319-342)
  - Added `_trigger_summarization()` method
  - Integrated post-labeling summary trigger
- 📝 **UPDATED**: `backend/app/services/rss_scheduler.py` (lines 12, 48-71, 236-330)
  - Added 2 new scheduler jobs (every 15 minutes)
  - `process_pending_summaries()` - Scans pending summaries
  - `retry_error_summaries()` - Retries failed summaries

**Configuration & API:**
- 📝 **UPDATED**: `backend/app/core/config.py` (lines 29-34)
  - Added 5 configuration settings for AI summary
- 📝 **UPDATED**: `backend/app/api/articles.py` (lines 82-86, 169-172)
  - Updated endpoints to include summary fields

#### Frontend Changes

**Types & Components:**
- 📝 **UPDATED**: `frontend/src/types/index.ts` (lines 38-42)
  - Added AI summary fields to Article interface
- 📝 **UPDATED**: `frontend/src/components/ArticleDetail.tsx` (lines 1-14, 59-160, 213)
  - Imported react-markdown and remark-gfm
  - Added `renderAISummary()` function with 4 states (pending/success/error/ignored)
  - Implemented collapsible markdown viewer with copy button
  - Integrated toast notifications for copy action

**Dependencies:**
- 📦 **INSTALLED**: `react-markdown` - Markdown rendering library
- 📦 **INSTALLED**: `remark-gfm` - GitHub Flavored Markdown support

#### Key Features Delivered

✅ **Automatic Trigger System:**
- Triggered after successful AI labeling (non-#可忽略 articles)
- Scheduled scan every 15 minutes for pending summaries

✅ **Robust Error Handling:**
- Exponential backoff retry (1s, 2s)
- 30-second timeout per request
- Dedicated retry scheduler every 15 minutes
- Per-article error tracking

✅ **Smart Content Management:**
- Auto-skip #可忽略 articles (status: ignored)
- Auto-skip articles with <100 chars content
- Content truncation at 8000 chars (token optimization)

✅ **Rich Frontend UX:**
- Real-time status indicators (pending/success/error)
- Collapsible markdown viewer (default: expanded)
- Copy-to-clipboard with toast feedback
- Smooth transitions and loading states

✅ **Structured Output:**
- Custom DeepSeek prompt generates consistent format:
  - **主要观点和论据** - Key arguments with evidence
  - **对我的价值** - Value for developer and blogger personas

#### Performance & Scalability

- **Concurrency Control**: Max 4 simultaneous API calls via semaphore
- **Batch Processing**: 3 articles per batch
- **Rate Limiting**: 2-second delays between batches
- **Non-blocking**: All triggers use `asyncio.create_task()`
- **Database Indexing**: `ai_summary_status` indexed for fast queries

#### Files Summary

**Created (2):**
1. `backend/alembic/versions/c41751321e50_add_ai_summary_fields.py`
2. `backend/app/services/ai_summarizer.py`

**Modified (9):**
1. `backend/app/models/article.py`
2. `backend/app/core/config.py`
3. `backend/app/services/ai_labeler.py`
4. `backend/app/services/rss_scheduler.py`
5. `backend/app/schemas/article.py`
6. `backend/app/api/articles.py`
7. `frontend/src/types/index.ts`
8. `frontend/src/components/ArticleDetail.tsx`
9. `.claude/claude.md`

**Dependencies Added (2):**
1. `react-markdown`
2. `remark-gfm`

#### Testing Guide

**1. Restart Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Expected logs:**
```
INFO: RSS Scheduler started. Fetching feeds every 15 minutes
INFO: AI Retry Scheduler started. Retrying error labels every 15 minutes
INFO: AI Summary Scheduler started. Processing summaries every 15 minutes
INFO: AI Summary Retry Scheduler started. Retrying error summaries every 15 minutes
```

**2. Verify Database Migration:**
```bash
cd backend
source venv/bin/activate
alembic current
# Should show: c41751321e50 (head)
```

**3. Test the Feature:**
- Wait for new articles to be fetched (or add a new RSS source)
- Articles will be labeled first (status: done)
- Summaries will generate automatically within 15 minutes
- Check ArticleDetail view to see summary status:
  - "🏃 AI正在赶来的路上..." = Processing
  - Markdown content with expand/collapse = Success
  - "❌ AI摘要生成失败" = Error (will retry in 15 min)

**4. Manual Trigger (Optional):**
```python
# In Python console with backend venv active
from app.services.ai_summarizer import get_ai_summarizer
from app.core.database import AsyncSessionLocal
import asyncio

async def test_summary():
    async with AsyncSessionLocal() as db:
        summarizer = get_ai_summarizer()
        count = await summarizer.process_pending_summaries(db, max_articles=1)
        print(f"Processed {count} articles")

asyncio.run(test_summary())
```

**5. Monitor Logs:**
```bash
# Watch for summary processing
tail -f backend/logs/app.log | grep -i summary

# Expected log patterns:
# "Starting AI summary generation task for pending articles"
# "Successfully generated summary for article {uuid}"
# "AI summary generation completed: N articles summarized"
```

---

**Last Updated:** 2025-10-17
