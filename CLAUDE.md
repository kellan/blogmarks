# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based linkblog system that fetches bookmarks from Pinboard and generates static HTML pages. The project creates a personal link blog inspired by Nelson's linkblog setup. The system processes bookmarks from Pinboard, stores them in a SQLite database, and generates monthly archive pages and an Atom feed.

## Environment Setup

1. Create a Python virtual environment: `python -m venv venv`
2. Activate virtual environment: `source venv/bin/activate` (Unix/Mac) or `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Set required environment variable: `PINBOARD_API_TOKEN` (get from Pinboard settings)

## Common Commands

### Fetching Links from Pinboard
```bash
python -m blogmarks.pinboard
```

### Generating Static Site
```bash
python -m blogmarks.render
```

### Testing
```bash
./venv/bin/python -m pytest tests/ -v    # Run all tests
./venv/bin/python -m pytest tests/test_via_field.py -v    # Run specific test file
```

### Direct Module Testing
```bash
python -m blogmarks.db        # Test database connection
python -m blogmarks.render    # Generate all HTML files and feed
```

## Architecture

The codebase follows a simple modular structure:

- **blogmarks/pinboard.py**: Fetches bookmarks from Pinboard API, handles date/via tag parsing, and stores to database
- **blogmarks/db.py**: SQLite database operations using PugSQL for query management
- **blogmarks/render.py**: Static site generation using Jinja2 templates
- **sql/pugsql.sql**: SQL queries for database operations
- **templates/**: Jinja2 templates for HTML generation

### Data Flow
1. `pinboard.py` fetches recent bookmarks from Pinboard API
2. Links are processed and stored in SQLite database via `db.py`
3. `render.py` queries database and generates static HTML files in `_site/`

### Key Features
- Incremental sync (only fetches new bookmarks based on timestamps)
- **Via field support**: `via:source` tags are extracted and stored in database `via` field, then removed from tags
- **Date field support**: `date:YYYY-MM-DD` tags override timestamp for backdating posts
- Monthly archives with automatic year/month organization
- Atom feed generation for syndication
- Comprehensive test suite with 37 tests covering all major functionality

## Database Schema

SQLite database (`data.db`) with single `links` table containing:
- id, ts (Unix timestamp), url, description, extended, via, tags, hash

## Output Structure

Generated files in `_site/`:
- `index.html` - Recent links
- `YYYY-MM.html` - Monthly archive pages  
- `archive.html` - Archive index with year/month links
- `index.atom` - Atom feed

## Environment Variables

- `PINBOARD_API_TOKEN` (required) - Your Pinboard API token
- `PINBOARD_API_COUNT` (optional) - Number of recent posts to fetch
- `PINBOARD_API_TAG` (optional) - Filter by specific tag

## Development Notes

### Testing
- TDD approach is followed for all new features
- Comprehensive test suite covers pinboard processing, database operations, and rendering
- Tests use temporary databases to avoid affecting production data
- Run tests before making changes to ensure no regressions

### Tag Processing
- `via:source` tags: Extracted to `via` database field, removed from tags list
- `date:YYYY-MM-DD` tags: Override timestamp for backdating, removed from tags list
- Special tags `+` and `-` are filtered out during post preparation