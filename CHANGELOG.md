# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-13

### Added

#### Data Collection
- Reddit API integration with PRAW
- Fallback scraping data source
- Async data collection with rate limiting
- SQLite database storage with SQLAlchemy ORM
- Batch collection from subreddit lists

#### Analysis
- Keyword extraction using TF-IDF and YAKE
- Time series trend analysis
- Rising/falling keyword detection
- Demand pattern detection with clustering
- Priority-based opportunity scoring
- Competitive analysis with entity recognition
- Sentiment analysis (positive/negative/neutral)
- Complaint and alternative pattern detection

#### Business Insights
- Rule-based insight generation engine
- Business scoring with grades (A-F)
- Feasibility assessment
- Action item recommendations

#### Dashboard
- FastAPI-based web dashboard
- HTMX for dynamic UI updates
- Jinja2 server-side rendering
- Trend visualization
- Demand analysis view
- Competition analysis view
- Insights view
- Search functionality

#### Reports
- Markdown report generation
- Template-based report system
- Individual reports (trend, demand, competitive, insight)
- Full comprehensive report
- JSON metadata export

#### CLI
- Rich-based terminal output
- Command groups: collect, analyze, report, dashboard
- Progress bars with time estimation
- User-friendly error messages with hints

#### Documentation
- Comprehensive README
- Getting started guide
- CLI reference
- API guide
- Dashboard guide

### Technical

- Python 3.11+ requirement
- Async/await throughout
- Type hints and mypy strict mode
- Ruff for linting and formatting
- Pytest for testing

[0.1.0]: https://github.com/ibkim/reddit-insight/releases/tag/v0.1.0
