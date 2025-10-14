# RSS Feed Reader - Project Implementation Guide

## ✅ Implementation Status

The RSS Feed Reader has been **fully implemented** with backend and frontend working together.

---

## 🏗️ Architecture Overview

### Three-Tier Architecture
```
Frontend (React) ←→ Backend API (FastAPI) ←→ Database (PostgreSQL)
                         ↓
                   RSS Scheduler (APScheduler)
```

---

## 🎯 Core Functionality

### 1. RSS Feed Management
- **Add RSS Sources**: Users can add any RSS feed URL with validation
  - Real-time validation checks if the RSS feed is accessible and parseable
  - Extracted metadata (title, description) displayed before confirmation
  - **Custom Source Naming**: Edit RSS source name before saving (defaults to RSS feed title)
  - Custom categories for organization

- **View Sources**: Left panel displays all RSS sources
  - Grouped by categories with collapsible sections
  - Shows unread article count per source
  - Icon support for visual identification

- **Delete Sources**: Remove unwanted RSS feeds
  - Right-click context menu on any source
  - Two-step confirmation dialog with checkbox
  - Cascade deletion of all related articles
  - Toast notifications in lower right corner
  - Optimistic UI updates with error rollback

### 2. Automatic RSS Fetching
- **Scheduled Updates**: APScheduler runs every 15 minutes
- **Rate Limiting**: 2-minute gap between each RSS source fetch
- **Deduplication**: Uses GUID to prevent duplicate articles
- **Smart Parsing**: Extracts title, description, content, images, publication date
- **Error Handling**: Failed fetches don't block other sources

### 3. Article Display
- **Three-Panel Resizable Layout**:
  - **Left Panel**: RSS sources with category organization (resizable, 15-30% width)
  - **Middle Panel**: Article list with previews (resizable, 20-50% width)
  - **Right Panel**: Full article detail view (resizable, minimum 30% width)
  - **Drag-to-Resize**: Users can adjust panel boundaries by dragging resize handles
  - **Independent Scrolling**: Each panel scrolls independently when content overflows

- **Article Preview**: Shows source icon, title, description snippet, timestamp
- **Full Article View**: Complete content with cover images, AI summary placeholder, external link

### 4. Real-Time Updates
- **Auto-refresh**: Frontend queries update every 60 seconds
- **Cache Management**: TanStack Query handles caching and invalidation
- **Optimistic Updates**: UI responds immediately to user actions

---

## 🛠️ Technical Implementation

### Backend (FastAPI + Python)
**Location**: `/backend/`

**Key Components**:
- **RSS Parser Service** (`app/services/rss_parser.py`):
  - Uses `feedparser` and `httpx` for async RSS fetching
  - Extracts all RSS 2.0 fields including media content
  - Automatic favicon extraction from website domains

- **RSS Service Layer** (`app/services/rss_service.py`):
  - Centralized business logic for RSS operations
  - Delete source with user ownership validation
  - Returns deletion statistics (articles deleted count)
  - Background cleanup tasks support

- **Scheduler Service** (`app/services/rss_scheduler.py`):
  - APScheduler with interval trigger (15 minutes)
  - Sequential processing with `asyncio.sleep(120)` for 2-min gaps
  - Automatic unread count updates

- **REST API**:
  - RSS validation, source CRUD, article queries
  - Enhanced DELETE endpoint with background tasks
  - See API documentation at `http://localhost:8000/docs` for all endpoints

**Database**:
- PostgreSQL with SQLAlchemy 2.0 (async)
- Three main tables: `users`, `rss_sources`, `articles`
- Alembic for migrations

### Frontend (React + TypeScript + Vite)
**Location**: `/frontend/`

**Key Components**:
- **State Management**:
  - Zustand for UI state (selected source, selected article)
  - TanStack Query for server state and caching

- **UI Layout**:
  - `react-resizable-panels` for drag-to-resize three-panel layout
  - Radix UI ScrollArea for smooth independent scrolling per panel
  - Responsive height constraints with flexbox for proper overflow handling

- **UI Components**:
  - `FeedSourceList`: Collapsible categories, source selection, context menu
  - `ArticleList`: Scrollable article cards in resizable panel
  - `ArticleDetail`: Full article with sanitized HTML content and scroll
  - `AddSourceDialog`: RSS URL validation, custom naming, and submission
  - `SourceContextMenu`: Right-click menu for source operations
  - `ConfirmDialog`: Reusable confirmation dialog for destructive actions
  - `SourceIcon`: Smart icon component (favicon URLs or emoji fallback)
  - `Toaster`: Toast notification system (lower right corner)

- **Styling**:
  - Tailwind CSS 3.4 for utility classes
  - Radix UI components (Dialog, ContextMenu, Toast, ScrollArea, Checkbox)
  - Shadcn/ui components for consistent design
  - Custom resize handles with hover effects

---

## 🚀 How to Run

### Quick Start
Both services are currently running:
- **Frontend**: http://localhost:5174
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Manual Start Commands

**Database** (PostgreSQL):
```bash
docker-compose up -d
```

**Backend**:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Frontend**:
```bash
cd frontend
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
npm run dev
```

---

## 📊 Data Flow

### Adding an RSS Source
1. User enters RSS URL in dialog
2. Frontend calls validation API to check URL
3. Backend fetches RSS feed with `httpx` and parses with `feedparser`
4. If valid, user can edit source name (defaults to RSS feed title) and add category
5. Frontend sends custom name, URL, and category to backend
6. Backend saves to `rss_sources` table with user's custom name
7. Scheduler will fetch articles on next cycle

### Fetching Articles
1. APScheduler triggers every 15 minutes
2. Queries all RSS sources from database
3. Fetches each feed with 2-minute delay between sources
4. Parses articles and checks for duplicates (by GUID)
5. Stores new articles in `articles` table
6. Updates unread counts per source

### Viewing Articles
1. Frontend loads sources on mount
2. User selects source → filters articles by `source_id`
3. User selects article → fetches full details
4. Frontend auto-refreshes every 60 seconds

### Deleting an RSS Source
1. User right-clicks on RSS source in left panel
2. Context menu appears with "删除源" option
3. User clicks → confirmation dialog opens
4. Dialog shows source name, warning, and required checkbox
5. User checks "我了解这将删除所有相关文章" and clicks "删除"
6. Frontend optimistically removes source from UI
7. Backend validates user ownership and deletes source
8. Database cascade deletes all related articles
9. Background task runs cleanup (logs, cache, metrics)
10. Success toast appears in lower right corner
11. If error occurs, source is restored and error toast shows

---

## 🔑 Key Features

### RSS Parsing
- **Format Support**: RSS 2.0 XML (standard format)
- **Fields Extracted**: title, description, content, link, pubDate, guid, media
- **HTML Content**: Preserved for rich article display
- **Error Tolerance**: Continues if individual entries fail to parse

### User Experience
- **Instant Feedback**: Validation happens before submission
- **Visual Hierarchy**: Three-panel resizable design separates concerns
- **Customizable Layout**: Drag panel boundaries to adjust widths to preference
- **Smooth Scrolling**: Independent scroll areas for each panel with proper overflow handling
- **Editable Source Names**: Customize RSS source display names
- **Performance**: Lazy loading and query caching

### Developer Experience
- **Type Safety**: Full TypeScript in frontend
- **API Documentation**: Auto-generated FastAPI docs
- **Database Migrations**: Alembic tracks schema changes
- **Hot Reload**: Both frontend and backend support live reloading

---

## 🎨 UI Design Reference

The frontend implementation closely follows `figma_frontendbasic/` design:
- Same color scheme and spacing
- Identical component structure
- Matching interactions and animations

**Key differences**:
- Real API integration (not mock data)
- RSS source addition dialog with custom naming
- Live data updates
- Resizable panels with drag handles
- Independent scrolling per panel

---

## 📚 API Documentation

### REST API Endpoints

**Base URL**: `http://localhost:8000`

#### RSS Source Management

**POST `/api/rss/validate`**
- Validate an RSS feed URL
- Request: `{ "url": "https://example.com/feed.xml" }`
- Response: `{ "valid": true, "title": "Feed Title", "description": "...", "icon": "https://example.com/favicon.ico", "error": null }`

**POST `/api/sources`**
- Create a new RSS source
- Request: `{ "url": "https://...", "title": "Custom Name", "category": "Tech" }`
- Response: RSS source object with ID, timestamps, unread_count

**GET `/api/sources`**
- List all RSS sources for the user
- Response: Array of RSS source objects

**DELETE `/api/sources/{source_id}`** 🆕
- Delete an RSS source and all related articles
- Path Parameter: `source_id` (UUID)
- Response: `{ "source_id": "...", "source_title": "...", "source_url": "...", "category": "...", "articles_deleted": 42, "message": "RSS source deleted successfully" }`
- Features:
  - User ownership validation (403 if not owner)
  - CASCADE deletion of articles (database level)
  - Background cleanup tasks
  - Returns deletion statistics
- Errors:
  - 404: Source not found
  - 403: Not authorized to delete
  - 500: Server error

#### Article Management

**GET `/api/articles`**
- List articles (optionally filtered by source)
- Query Parameter: `source_id` (optional UUID)
- Response: Array of article objects with source info

**GET `/api/articles/{article_id}`**
- Get full article details
- Path Parameter: `article_id` (UUID)
- Response: Complete article object with sanitized content

**PATCH `/api/articles/{article_id}/read`**
- Mark article as read
- Path Parameter: `article_id` (UUID)

### Interactive API Documentation

**Swagger UI**: http://localhost:8000/docs
- Try out all endpoints interactively
- View request/response schemas
- Test authentication and error handling

**ReDoc**: http://localhost:8000/redoc
- Alternative API documentation format
- Better for reading and printing

---

## 📚 Additional Resources

- **Database Schema**: See `backend/alembic/versions/` for migration files
- **Requirements**: `requirements_draft.md` for full tech stack details
- **Quick Start**: `START_SERVERS.md` for launch instructions

---

## 🔄 Next Steps / Future Enhancements

Potential improvements (not yet implemented):
- **RSS support**:supporting the rss hub format. 
- **AI Summarization**: Replace placeholder with real LLM integration
- **User Authentication**: Currently uses default user
- **Read/Unread Tracking**: Mark articles as read
- **Favorites**: Save important articles
- **Search**: Full-text search across articles
- **Filters**: By date, source, category
- **Export**: Save articles to different formats
- **Mobile App**: Native iOS/Android versions

---

---

## 🆕 Recent Updates (2025-10-13)

### 1. Resizable Panel Layout
- Replaced fixed-width panels with dynamic resizable panels
- Users can drag boundaries between panels to adjust layout
- Panel constraints: Left (15-30%), Middle (20-50%), Right (min 30%)
- Visual resize handles with hover effects for better UX

### 2. Independent Panel Scrolling
- Fixed scroll behavior in all three panels
- Each panel now scrolls independently when content overflows
- Headers remain fixed while content areas scroll smoothly
- Proper height constraints using flexbox and Radix UI ScrollArea

### 3. Custom RSS Source Naming
- Users can now edit RSS source names before saving
- Source name input auto-populated with RSS feed title
- Fully editable before submission
- Backend updated to accept custom titles via API

### Technical Implementation Notes
- Added `react-resizable-panels` package for resizable layout
- Updated all panel components with proper overflow and height constraints
- Added `flex-1 h-0` pattern to ScrollArea for proper flex behavior
- Backend schema extended to accept `title` field in source creation

---

## 🆕 Recent Updates (2025-10-14)

### 1. Enhanced RSS Source Deletion
- **Right-Click Context Menu**: Right-click any RSS source to access delete option
- **Two-Step Confirmation**: Required checkbox confirmation before deletion
- **Cascade Deletion**: Automatically deletes all related articles (database CASCADE)
- **Toast Notifications**: Success/error messages in lower right corner
- **Optimistic Updates**: Instant UI feedback with error rollback
- **Background Tasks**: Async cleanup using FastAPI BackgroundTasks
- **Service Layer**: New `RSSService` class for centralized business logic
- **User Validation**: Ownership checks before deletion
- **Deletion Statistics**: Returns count of articles deleted

### 2. Website Favicon Support
- **Automatic Favicon Extraction**: Fetches website favicons when adding RSS sources
- **Multiple Strategies**: Tries HTML parsing, common paths (/favicon.ico, /apple-touch-icon.png)
- **Smart Icon Component**: Renders favicon URLs or falls back to emoji
- **Lazy Loading**: Images load lazily for better performance
- **Error Handling**: Graceful fallback to default emoji on broken images

### 3. HTML Content Sanitization
- **DOMPurify Integration**: Secure HTML sanitization to prevent XSS attacks
- **Whitelist Approach**: Only allows safe HTML tags (p, a, img, headings, lists, etc.)
- **Script Blocking**: Removes all `<script>`, `<iframe>`, event handlers
- **Link Security**: Auto-adds `target="_blank"` and `rel="noopener noreferrer"` to external links
- **Image Optimization**: Lazy loading and broken image handling
- **Custom Styles**: Prose styles for consistent article rendering

### 4. Reusable UI Components
- **ConfirmDialog**: Generic confirmation dialog for any destructive action
  - Customizable title, message, buttons
  - Optional two-step confirmation with checkbox
  - Support for danger/warning/info variants
  - Loading states and async action handling
- **Toast System**: Lower right corner notifications
  - Success, error, warning, info variants
  - Auto-dismiss with configurable duration
  - Queue management for multiple toasts
  - Slide-in animations
- **Context Menu**: Right-click menu using Radix UI
  - Keyboard navigation support
  - Accessible and mobile-friendly

### Technical Implementation Notes
- **Backend Dependencies**: FastAPI BackgroundTasks for async operations
- **Frontend Dependencies**:
  - `@radix-ui/react-context-menu@^2.2.16`
  - `@radix-ui/react-toast@^1.2.4`
  - `@radix-ui/react-checkbox@^1.3.3`
  - `dompurify@^3.2.7` for HTML sanitization
- **Database**: CASCADE delete configured in SQLAlchemy relationships
- **API Enhancement**: DELETE `/api/sources/{source_id}` returns deletion stats
- **Cache Invalidation**: TanStack Query properly invalidates after mutations
- **Error Handling**: Comprehensive error messages with rollback support

### Bug Fixes
- Fixed context menu not opening (removed blocking `e.preventDefault()`)
- Fixed event handler type in SourceContextMenu
- Removed article description from display (eliminates duplicate/malformed content)

---

**Last Updated**: 2025-10-14
**Status**: ✅ Fully Functional with Enhanced UX & Security
**Access**: http://localhost:5174
