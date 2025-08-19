# HDX Notification Platform

A Python-based notification system that listens for HDX (Humanitarian Data Exchange) events and sends notifications through Novu.

## Overview

This platform consists of two main components:
- **Listener**: Monitors Redis event streams for dataset/resource changes
- **Sync**: Syncs user subscriptions from CKAN to the local db


## Event Types

The platform handles the following HDX events:

**Resource Events:**
- `resource-created`
- `resource-deleted`
- `resource-data-changed`

**Spreadsheet Events:**
- `spreadsheet-sheet-created`
- `spreadsheet-sheet-deleted`
- `spreadsheet-sheet-changed`

**Collection Events:**
- `organization-dataset-added`
- `crisis-dataset-added`
- `group-dataset-added`

## Quick Start

### Prerequisites
- Python 3.10+
- Redis
- PostgreSQL
- Docker (optional)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# Database configuration
HDX_NOTIFICATIONSDB_USER=some_user
HDX_NOTIFICATIONSDB_PASS=some_pass
HDX_NOTIFICATIONSDB_ADDR=localhost
HDX_NOTIFICATIONSDB_PORT=5432
HDX_NOTIFICATIONSDB_DB=notifications

# Redis configuration
REDIS_STREAM_HOST=localhost
REDIS_STREAM_DB=0

# Novu configuration
NOVU_API_URL=https://api.novu.co/v1/events/trigger
NOVU_API_KEY=your_novu_api_key

# Worker configuration
WORKER_ENABLED=true
```

### Running

**Listener mode** (monitors events):
```bash
python run.py
```

**Sync mode** (processes subscriptions):
```bash
python sync.py
```


## Testing

Run tests with pytest:
```bash
# Install test dependencies
pip install -r dev-requirements.txt

# Run tests
pytest --cov=.
```

For local testing, you can create a `.env` file with test database configurations.

## Project Structure

```
├── common/                 # Shared utilities and database models
├── config/                 # Configuration management
├── listener_processing/    # Event listener logic
├── sync_processing/        # Subscription sync logic
├── tests/                  # Test suite
├── run.py                  # Listener entry point
├── sync.py                 # Sync entry point
```

## Configuration

The platform uses environment variables for configuration. Key settings include:
- Database connection details
- Redis connection settings
- Novu API credentials
- Worker enable/disable flag

