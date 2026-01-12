# Log Persistence Backend System - Complete Guide

## Architecture Overview

```
AppLogger (logger.py)
    ↓
persist_log() (persistence.py)
    ↓
LogPersistenceHandler (queue + background thread)
    ↓
Backend Registry (reads LOG_BACKENDS env)
    ↓
Multiple Backends (file, datadog, prometheus, etc.)
```

## Key Features

✅ **Pluggable Backends**: Add new backends without modifying core code
✅ **Non-blocking**: All writes happen in background thread
✅ **Multi-backend**: Write to file + Datadog + Prometheus simultaneously
✅ **Type-safe**: Strict typing with proper Optional handling
✅ **Env-driven**: Configure via `LOG_BACKENDS` environment variable
✅ **Uses `write_to_file`**: File backend leverages your existing function

---

## Quick Start

### 1. Basic File Logging (Default)

```python
# No env variable needed - defaults to file backend
from common.logger import get_app_logger

logger = get_app_logger(persist=True)
logger.info("This writes to weekly file")
```

### 2. Multiple Backends

```bash
# In your .env or environment
export LOG_BACKENDS=file,datadog
```

```python
from common.logger import get_app_logger

logger = get_app_logger(persist=True)
logger.info("User logged in", user_id=123)
# ✓ Written to weekly file: logs/wk02_2024-01-08--2024-01-14.json
# ✓ Sent to Datadog
```

### 3. Datadog Only

```bash
export LOG_BACKENDS=datadog
export DD_API_KEY=your_datadog_api_key
```

```python
from common.logger.backends import register_backend
from common.logger.backends.datadog_backend import DatadogBackend

# Register Datadog backend
register_backend('datadog', DatadogBackend)

logger = get_app_logger(persist=True)
logger.info("This only goes to Datadog")
```

---

## File Structure

```
common/
├── logger/
│   ├── __init__.py
│   ├── logger.py                    # AppLogger class
│   ├── persistence.py               # Queue + background thread
│   └── backends/
│       ├── __init__.py              # Exports
│       ├── base.py                  # LogBackend ABC
│       ├── file_backend.py          # Uses write_to_file()
│       ├── datadog_backend.py       # Datadog implementation
│       └── registry.py              # Backend management
├── scripts/
│   └── process_log.py               # write_to_file, get_week_date_range
└── config/
    └── structlog_config.py
```

---

## Adding a New Backend

### Example: Custom Slack Backend

```python
# common/logger/backends/slack_backend.py
from typing import Any, Dict
from .base import LogBackend

class SlackBackend(LogBackend):
    def __init__(self, **config: Any):
        super().__init__(**config)
        self.webhook_url = config.get("webhook_url", os.environ.get("SLACK_WEBHOOK_URL"))
        self._total_writes = 0

    @property
    def name(self) -> str:
        return "slack"

    def write(self, log_entry: Dict[str, Any]) -> bool:
        """Send log to Slack."""
        try:
            import requests

            # Only send errors to Slack
            if log_entry.get("level") != "ERROR":
                return True

            payload = {
                "text": f"🚨 {log_entry['message']}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Error*: {log_entry['message']}"}
                    }
                ]
            }

            response = requests.post(self.webhook_url, json=payload)
            self._total_writes += 1
            return response.ok

        except Exception as e:
            import sys
            print(f"SlackBackend error: {e}", file=sys.stderr)
            return False

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "backend": self.name,
            "total_writes": self._total_writes,
        }
```

### Register and Use

```python
# In your app startup
from common.logger.backends import register_backend
from common.logger.backends.slack_backend import SlackBackend

register_backend('slack', SlackBackend)
```

```bash
# Environment
export LOG_BACKENDS=file,slack
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

---

## Configuration Options

### Environment Variables

| Variable            | Purpose                      | Example                       |
| ------------------- | ---------------------------- | ----------------------------- |
| `LOG_BACKENDS`      | Comma-separated backend list | `file,datadog,prometheus`     |
| `DD_API_KEY`        | Datadog API key              | `abc123...`                   |
| `DD_SITE`           | Datadog region               | `datadoghq.eu`                |
| `SLACK_WEBHOOK_URL` | Slack webhook                | `https://hooks.slack.com/...` |

### Backend Selection Logic

```python
# Default (no env variable)
LOG_BACKENDS=file

# Multiple backends
LOG_BACKENDS=file,datadog
# → Writes to both file AND Datadog

# Single non-file backend
LOG_BACKENDS=datadog
# → Only Datadog (no file)

# Invalid backend
LOG_BACKENDS=file,invalid,datadog
# → Logs warning, uses file + datadog
```

---

## Performance Characteristics

### Timing Breakdown

```python
logger = get_app_logger(persist=True, track_timing=True)

# Make many log calls
for i in range(1000):
    logger.info(f"Event {i}", event_id=i)

stats = logger.get_timing_stats()
print(stats)
# {
#   'total_calls': 1000,
#   'avg_time_ms': 0.15,      # ✓ Well under 5ms target
#   'max_time_ms': 2.3,
#   'min_time_ms': 0.08
# }
```

### What's Being Measured

- **Logger timing**: Time from `logger.info()` call to return
  - Includes: structlog processing + queue enqueue
  - Excludes: Background write time (non-blocking)
- **Persistence metrics**: Background write performance
  - Access via `get_persistence_metrics()`

### Expected Performance

| Operation                  | Typical Time   | Notes              |
| -------------------------- | -------------- | ------------------ |
| `logger.info()` call       | 0.1-0.5ms      | Enqueue only       |
| Queue enqueue              | <0.05ms        | Nearly instant     |
| Background write (file)    | 1-2ms/batch    | 100 logs per batch |
| Background write (Datadog) | 50-200ms/batch | Network latency    |

---

## Why This Architecture?

### ✅ Advantages

1. **Separation of Concerns**

   - Logger: User interface
   - Persistence: Queue management
   - Backends: Actual I/O

2. **Easy to Extend**

   ```python
   # Adding Datadog = 3 steps
   register_backend('datadog', DatadogBackend)  # 1. Register
   # 2. Set env: LOG_BACKENDS=file,datadog
   # 3. Done! No code changes
   ```

3. **Fail-Safe**

   - If Datadog fails, file logging continues
   - If queue fills, logs still go to console
   - Backend errors don't crash app

4. **Testable**

   ```python
   # Mock backends in tests
   class MockBackend(LogBackend):
       def write(self, entry):
           self.entries.append(entry)
           return True

   register_backend('mock', MockBackend)
   ```

### Vs. Alternative Approaches

| Approach                  | Issue                                          |
| ------------------------- | ---------------------------------------------- |
| SQLite + Cron             | Adds complexity, slower writes, DB maintenance |
| Direct Datadog            | Vendor lock-in, can't test locally             |
| Async/await               | Doesn't help with I/O-bound writes             |
| Multiple logger instances | Config duplication, hard to manage             |

---

## Complete FastAPI Example

```python
# main.py
import logging
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from common.config.structlog_config import configure_structlog
from common.logger import get_app_logger
from common.logger.persistence import shutdown_persistence
from common.logger.backends import register_backend

# Register custom backends
from common.logger.backends.datadog_backend import DatadogBackend
register_backend('datadog', DatadogBackend)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    # Startup
    configure_structlog(logging.INFO)
    print("Application started")

    yield

    # Shutdown
    shutdown_persistence(timeout=10.0)
    print("Application shutdown")

app = FastAPI(lifespan=lifespan)

# Create logger with persistence
logger = get_app_logger(name="api", persist=True, track_timing=True)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    import time
    start = time.perf_counter()

    response = await call_next(request)

    duration = (time.perf_counter() - start) * 1000

    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration, 2)
    )

    return response

@app.get("/metrics")
async def metrics():
    """Get logging performance metrics."""
    from common.logger.persistence import get_persistence_metrics
    from common.logger.backends.registry import get_all_metrics

    return {
        "logger": logger.get_timing_stats(),
        "persistence": get_persistence_metrics(),
        "backends": get_all_metrics()
    }
```

---

## Monitoring & Debugging

### Check Active Backends

```python
from common.logger.backends import get_active_backends

backends = get_active_backends()
print([b.name for b in backends])
# ['file', 'datadog']
```

### Get All Metrics

```python
from common.logger.backends.registry import get_all_metrics

metrics = get_all_metrics()
print(metrics)
# {
#   'file': {
#     'backend': 'file',
#     'total_writes': 1523,
#     'failed_writes': 0,
#     'log_directory': '/app/logs'
#   },
#   'datadog': {
#     'backend': 'datadog',
#     'total_writes': 1523,
#     'failed_writes': 2,
#     'service': 'myapp',
#     'site': 'datadoghq.com'
#   }
# }
```

### Debug Queue Issues

```python
from common.logger.persistence import get_persistence_metrics

metrics = get_persistence_metrics()

if metrics['queue_size'] > 5000:
    print("⚠️ Queue backing up!")

if metrics['failed_logs'] > 0:
    print(f"⚠️ {metrics['failed_logs']} logs failed to persist")
```

---

## Type Safety Fix Explanation

### The Problem

```python
# ❌ Old code
self._timing_stats = TimingStats() if track_timing else None

# Later in code:
if self._track_timing and start_time is not None:
    self._timing_stats.record(elapsed)  # ← Mypy error: could be None
```

### The Solution

```python
# ✅ Fixed
self._timing_stats: Optional[TimingStats] = (
    TimingStats() if track_timing else None
)

# Later with proper None check:
if self._track_timing and start_time is not None and self._timing_stats is not None:
    self._timing_stats.record(elapsed)  # ← Mypy happy
```

The extra `self._timing_stats is not None` check satisfies strict type checking.

---

## Summary

✨ **What You Get:**

- Non-blocking log persistence (<5ms)
- Pluggable backends via env variables
- Uses your existing `write_to_file()` function
- Easy to add Datadog/Prometheus/etc
- Type-safe with strict mypy
- Observable with built-in metrics

🎯 **To Add Datadog Tomorrow:**

1. Register backend: `register_backend('datadog', DatadogBackend)`
2. Set env: `LOG_BACKENDS=file,datadog`
3. Done! No code changes needed

📦 **To Add Slack Alerts:**

1. Create `slack_backend.py` (30 lines)
2. Register it
3. Set env: `LOG_BACKENDS=file,datadog,slack`
4. Only errors go to Slack channel
