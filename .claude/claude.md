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

**Status:** Fully implemented RSS feed aggregator with backend (FastAPI + PostgreSQL) and frontend (React + TypeScript).

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

**Backend:** FastAPI (async/await), SQLAlchemy 2.0 (async), Alembic, PostgreSQL, APScheduler, feedparser, httpx, OpenAI SDK + DeepSeek API, DOMPurify, pydantic, cachetools

**Frontend:** React 18, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS 3.4, Radix UI, react-resizable-panels, DOMPurify, lucide-react

**Database Schema:**
- `users` - User accounts
- `rss_sources` - Feed subscriptions with categories and icons
- `articles` - Fetched articles with CASCADE deletion and AI labels (JSONB)

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

**Three-Tier Tag System**
- **第一层 (Identity)**: #独立开发必备, #博主素材, #双重价值, #可忽略
- **第二层 (Themes, 1-2 tags)**: #模型动态, #技术教程, #深度洞察, #经验分享, #AI应用, #趣味探索
- **第三层 (Extra, up to 2)**: Custom tags (≤6 chars)
- **Special**: #VibeCoding (gradient purple)

**Display Modes**
- **Compact (ArticleCard)**: Max 3 color-coded tags + "+N" overflow
- **Full (ArticleDetail)**: All tags with "AI分类标签" header
- **Status**: "🏃 赶来的路上" (processing), "❌寄掉了" (error)

**Configuration:** Set `DEEPSEEK_API_KEY` in `.env`, adjust `AI_BATCH_SIZE` if needed

**Implementation:** [ai_labeler.py](backend/app/services/ai_labeler.py), [AILabels.tsx](frontend/src/components/AILabels.tsx), JSONB fields (`ai_labels`, `ai_label_status`)

---

### 4. AI Tag Filtering

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

### 5. Background Processing & Scheduling

**RSS Fetching**
- APScheduler runs every 15 minutes with 2-minute delays between sources (rate limiting)
- GUID-based deduplication, automatic unread count updates
- Error tolerance: failed fetches don't block other sources

**Caching Strategy**
- Backend: TTL cache (3 min) with LRU eviction for feed validation
- Frontend: TanStack Query with 60-second auto-refresh and optimistic updates

**Implementation:** [rss_scheduler.py](backend/app/services/rss_scheduler.py), cachetools TTLCache, TanStack Query invalidation

---

### 5. Security & Data Integrity

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

- AI article summarization, user authentication (email login)
- Read/unread tracking with bold styling
- ✅ ~~Filter by AI labels~~ (Implemented - see section 4)
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

**Last Updated:** 2025-10-17
