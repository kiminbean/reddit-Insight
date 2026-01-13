---
phase: 04-data-pipeline
plan: 01
status: complete
completed_at: 2025-01-13
---

# 04-01 Summary: Database Schema and ORM Models

## Objective
데이터베이스 스키마 및 ORM 모델을 정의하여 수집된 Reddit 데이터를 영구 저장하기 위한 데이터베이스 구조를 구축했다.

## Completed Tasks

### Task 1: Dependencies and Storage Module Structure
- **Files**: `pyproject.toml`, `src/reddit_insight/storage/__init__.py`
- **Changes**:
  - Added `sqlalchemy>=2.0.0` and `aiosqlite>=0.19.0` to dependencies
  - Created `src/reddit_insight/storage/` module directory
  - Defined module exports in `__init__.py`

### Task 2: SQLAlchemy ORM Models
- **Files**: `src/reddit_insight/storage/models.py`
- **Changes**:
  - Created `Base` class using `DeclarativeBase` (SQLAlchemy 2.0 style)
  - Added `TimestampMixin` for automatic `created_at`/`updated_at` management
  - Implemented `SubredditModel` with posts relationship
  - Implemented `PostModel` with subreddit/comments relationships
  - Implemented `CommentModel` with post relationship
  - Added indexes on `reddit_id`, `subreddit_id`, `fetched_at`, `reddit_created_utc`

### Task 3: Database Connection Management
- **Files**: `src/reddit_insight/storage/database.py`
- **Changes**:
  - Created `Database` class with async engine management
  - Auto-convert sync URLs to async driver URLs (sqlite -> aiosqlite, postgresql -> asyncpg)
  - Auto-create SQLite directory if not exists
  - Implemented context manager pattern (`async with Database() as db`)
  - Added `session()` context manager for transaction handling
  - Added `create_tables()` and `drop_tables()` methods

### Task 4: Pydantic to ORM Conversion
- **Files**: `src/reddit_insight/storage/models.py`, `src/reddit_insight/storage/__init__.py`
- **Changes**:
  - Added `from_pydantic()` class methods to all ORM models
  - Added `to_pydantic()` instance methods to all ORM models
  - Verified bidirectional conversion between Pydantic and ORM models

## Commits
1. `[04-01] Task 1: Add database dependencies and storage module structure`
2. `[04-01] Task 2: Define SQLAlchemy ORM models`
3. `[04-01] Task 3: Implement database connection management`

## Verification Results
```
=== Final Verification ===
1. sqlalchemy version: 2.0.39, aiosqlite available: True
2. ORM Models: subreddits, posts, comments tables
3. Database class: async connection management
4. Pydantic <-> ORM conversion: OK
5. Package exports: OK
```

## Files Modified
- `pyproject.toml` - Added database dependencies
- `src/reddit_insight/storage/__init__.py` - Module exports
- `src/reddit_insight/storage/models.py` - ORM models with relationships
- `src/reddit_insight/storage/database.py` - Async database management

## Database Schema

### subreddits
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, autoincrement |
| name | VARCHAR(64) | UNIQUE, INDEX |
| display_name | VARCHAR(64) | NOT NULL |
| title | VARCHAR(512) | nullable |
| description | TEXT | nullable |
| subscribers | INTEGER | default=0 |
| over18 | BOOLEAN | default=False |
| reddit_created_utc | DATETIME | NOT NULL |
| fetched_at | DATETIME | NOT NULL |
| created_at | DATETIME | auto |
| updated_at | DATETIME | auto |

### posts
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, autoincrement |
| reddit_id | VARCHAR(16) | UNIQUE, INDEX |
| subreddit_id | INTEGER | FK -> subreddits, INDEX |
| title | VARCHAR(512) | NOT NULL |
| selftext | TEXT | nullable |
| author | VARCHAR(64) | NOT NULL |
| score | INTEGER | default=0 |
| num_comments | INTEGER | default=0 |
| url | VARCHAR(2048) | NOT NULL |
| permalink | VARCHAR(512) | NOT NULL |
| is_self | BOOLEAN | default=True |
| reddit_created_utc | DATETIME | INDEX |
| fetched_at | DATETIME | INDEX |
| created_at | DATETIME | auto |
| updated_at | DATETIME | auto |

### comments
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, autoincrement |
| reddit_id | VARCHAR(16) | UNIQUE, INDEX |
| post_id | INTEGER | FK -> posts, INDEX |
| parent_reddit_id | VARCHAR(24) | nullable |
| body | TEXT | NOT NULL |
| author | VARCHAR(64) | NOT NULL |
| score | INTEGER | default=0 |
| reddit_created_utc | DATETIME | INDEX |
| fetched_at | DATETIME | INDEX |
| created_at | DATETIME | auto |
| updated_at | DATETIME | auto |

## Usage Example
```python
from reddit_insight.storage import Database, SubredditModel, PostModel

# Context manager usage
async with Database() as db:
    async with db.session() as session:
        # Create subreddit
        subreddit = SubredditModel.from_pydantic(subreddit_info)
        session.add(subreddit)
        await session.commit()

        # Query
        result = await session.execute(
            select(PostModel).where(PostModel.subreddit_id == subreddit.id)
        )
        posts = result.scalars().all()
```

## Next Steps
- 04-02: Implement data repository pattern for CRUD operations
- 04-03: Add data deduplication and update logic
