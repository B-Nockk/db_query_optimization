# 🚀 SQL Query Optimization: From 8s to 80ms

## Table of Contents

- [Overview](#overview)
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
  - [Running with docker + nginx](#running-with-docker--nginx)
  - [Run Optimizations](#run-optimizations)
- [Optimization Strategies](#optimization-strategies)
  - [B-Tree Indexing](#1-b-tree-indexing)
  - [Partial Indexing](#2-partial-indexing)
  - [Composite Indexing](#3-composite-indexing)
  - [Redis Caching (Cache-Aside Pattern)](#4-redis-caching-cache-aside-pattern)
  - [Connection Pooling](#5-connection-pooling)
  - [Query Analysis (EXPLAIN ANALYZE)](#6-query-analysis-explain-analyze)
- [Anti-Patterns Demonstrated](#anti-patterns-demonstrated)
  - [The "Terrible" Endpoint](#the-terrible-endpoint)
- [Performance Metrics](#performance-metrics)
  - [Baseline vs. Optimized](#baseline-vs-optimized)
  - [Load Test Results](#load-test-results)
- [Observability](#observability)
  - [Structured Logging](#structured-logging)
  - [Metrics Endpoint](#metrics-endpoint)
- [Testing](#testing)
  - [Unit Tests](#unit-tests)
  - [Load Tests](#load-tests)
- [Documentation](#documentation)
- [Key Learnings](#key-learnings)
- [Next Steps](#next-steps)
- [Contributing](#contributing)
- [License](#license)

## Overview

> A hands-on demonstration of backend performance optimization using PostgreSQL, Redis, and indexing strategies on 10 million records.

## The Problem

How do you query 10 million user records without bringing your database to its knees?

## The Solution

Multiple optimization strategies, measured and compared with real metrics.

| Strategy              | Latency | Speedup     | Use Case             |
| --------------------- | ------- | ----------- | -------------------- |
| Table Scan (baseline) | ~8000ms | 1x          | Never in production  |
| B-Tree Index          | ~120ms  | 66x faster  | Standard lookups     |
| Partial Index         | ~85ms   | 94x faster  | Filtered queries     |
| Composite Index       | ~95ms   | 84x faster  | Multi-column queries |
| Redis Cache           | ~12ms   | 666x faster | Hot data paths       |

## Tech Stack

- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **API**: FastAPI + SQLAlchemy
- **Infrastructure**: Docker Compose, Nginx
- **Observability**: Structured logging, metrics endpoint
- **Testing**: pytest, locust (load testing)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- 4GB RAM minimum

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd db_query_optimization

# Install dependencies
pip install -r requirements.txt

# rename .env.dev to .env
mv .env.dev .env

# Create initial migration from your models
alembic revision --autogenerate -m "initial schema"

# Review the generated migration in alembic/versions/
# Apply it
alembic upgrade head

# Start services
python main.py

# Seed database (takes ~2-3 minutes)
python scripts/seed_db.py

# Verify setup
curl http://localhost:8000/health
```

### Running with docker + nginx

```bash
# Clone the repository
git clone <repo-url>
cd db_query_optimization

# rename .env.dev to .env
mv .env.dev .env

# Build docker image
docker compose build

# start service (watch mode)
docker compose up

# start service (detach mode)
docker compose up -d

# Verify setup
# Note when using docker, all curl operations shouldn't include the port
curl http://localhost/health

```

### Run Optimizations

```bash
# Baseline: Full table scan
curl http://localhost:8000/users/scan?email=user5000000@example.com

# Optimized: B-Tree index
curl http://localhost:8000/users/indexed?email=user5000000@example.com

# Optimized: Partial index (active users only)
curl http://localhost:8000/users/partial?email=user5000000@example.com

# Optimized: Composite index (email + status)
curl http://localhost:8000/users/composite?email=user5000000@example.com&status=active

# Super fast: Redis cache
curl http://localhost:8000/users/cached?email=user5000000@example.com

# Anti-pattern: N+1 queries
curl http://localhost:8000/users/terrible?limit=10
```

## Optimization Strategies

### 1. **B-Tree Indexing**

Standard single-column index on `email` field.

```sql
CREATE INDEX idx_users_email ON users(email);
```

**When to use**: High-cardinality columns with frequent exact-match queries.

**Trade-offs**:

- ✅ 66x faster reads
- ❌ ~15% slower writes
- ❌ Additional storage overhead

---

### 2. **Partial Indexing**

Index only a subset of rows (e.g., active users).

```sql
CREATE INDEX idx_users_email_active ON users(email)
WHERE status = 'active';
```

**When to use**: Queries frequently filter on a low-cardinality column (status, region, etc.).

**Benefits**:

- Smaller index size (30% reduction in this case)
- Faster index scans
- Lower memory footprint

---

### 3. **Composite Indexing**

Multi-column index for queries filtering on multiple fields.

```sql
CREATE INDEX idx_users_email_status ON users(email, status);
```

**When to use**: Queries with multiple WHERE conditions.

**Index column order matters**:

- Put high-cardinality columns first (email)
- Low-cardinality columns second (status)

---

### 4. **Redis Caching (Cache-Aside Pattern)**

Cache frequently accessed data in Redis with TTL-based expiry.

**Strategy**:

1. Check cache first
2. If miss, query database
3. Store result in cache with 5-minute TTL

**Trade-offs**:

- ✅ Sub-20ms latency
- ❌ Stale data risk (mitigated by TTL)
- ❌ Cache invalidation complexity

---

### 5. **Connection Pooling**

Reuse database connections instead of creating new ones per request.

```python
# SQLAlchemy configuration
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
```

**Impact**:

- Reduced connection overhead by ~40%
- Handles 500+ concurrent requests
- Prevents connection exhaustion

---

### 6. **Query Analysis (EXPLAIN ANALYZE)**

Every optimization is validated with PostgreSQL query plans.

```sql
EXPLAIN ANALYZE
SELECT * FROM users WHERE email = 'user5000000@example.com';
```

**Output includes**:

- Execution time
- Rows scanned vs. returned
- Index usage confirmation

See [`docs/ExperimentLog.md`](docs/ExperimentLog.md) for full query plans.

---

## Anti-Patterns Demonstrated

### The "Terrible" Endpoint

Deliberately bad implementation showcasing common mistakes:

```python
@app.get("/users/terrible")
async def get_users_terrible(limit: int = 10):
    # ❌ SELECT * (fetches unnecessary columns)
    users = session.query(User).limit(limit).all()

    # ❌ N+1 queries (1 query for users, then N queries for posts)
    for user in users:
        user.posts = session.query(Post).filter_by(user_id=user.id).all()

    # ❌ No pagination
    # ❌ No indexing
    # ❌ Eager loading not used

    return users
```

**Performance**:

- 10 users = 11 database queries
- 100 users = 101 queries
- Latency scales linearly with result size

**Correct approach**: Use `joinedload` or `selectinload` for eager loading.

---

## Performance Metrics

### Baseline vs. Optimized

| Metric         | Baseline | Optimized | Improvement |
| -------------- | -------- | --------- | ----------- |
| P50 Latency    | 7800ms   | 12ms      | **650x**    |
| P95 Latency    | 9200ms   | 28ms      | **328x**    |
| P99 Latency    | 11000ms  | 45ms      | **244x**    |
| Throughput     | 8 req/s  | 520 req/s | **65x**     |
| DB CPU Usage   | 85%      | 12%       | **-86%**    |
| Cache Hit Rate | N/A      | 94%       | N/A         |

### Load Test Results

```bash
# Run with: wrk -t4 -c100 -d30s http://localhost:8000/users/cached

Running 30s test @ http://localhost:8000/users/cached
  4 threads and 100 connections

Requests/sec:   523.47
Transfer/sec:     1.2MB
Latency Distribution:
  50%   12ms
  75%   18ms
  90%   25ms
  99%   45ms
```

See [`docs/ExperimentLog.md`](docs/ExperimentLog.md) for detailed metrics.

---

## Observability

### Structured Logging

Every request logs:

- Request ID (for distributed tracing)
- Query type (scan/index/cache)
- Execution time
- Cache hit/miss status

```json
{
  "timestamp": "2025-01-05T10:30:45Z",
  "request_id": "req_abc123",
  "endpoint": "/users/cached",
  "query_time_ms": 12,
  "cache_status": "hit",
  "db_queries": 0
}
```

### Metrics Endpoint

Prometheus-compatible metrics at `/metrics`:

```
# HELP api_request_duration_seconds API request duration
# TYPE api_request_duration_seconds histogram
api_request_duration_seconds_bucket{endpoint="/users/cached",le="0.01"} 8500
api_request_duration_seconds_bucket{endpoint="/users/cached",le="0.05"} 9800

# HELP cache_hit_rate Cache hit rate percentage
# TYPE cache_hit_rate gauge
cache_hit_rate 94.2
```

---

## Testing

### Unit Tests

```bash
pytest tests/unit/ -v
```

Tests cover:

- Query correctness (all strategies return same data)
- Cache invalidation logic
- Connection pool behavior
- Error handling

### Load Tests

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Simulates:

- Concurrent users (10-500)
- Mixed endpoint access patterns
- Cache warming scenarios

---

## Documentation

- **[Architecture.md](docs/Architecture.md)**: System design, data flow, component interaction
- **[ExperimentLog.md](docs/ExperimentLog.md)**: Query timings, EXPLAIN ANALYZE outputs, observations
- **[ProgressTracking.md](docs/ProgressTracking.md)**: Feature roadmap, completed tasks, future work

---

## Key Learnings

1. **Indexes aren't free**: They speed up reads but slow down writes (~15% in this case)
2. **Right tool for the job**: B-Tree for exact matches, partial for filtered queries, cache for hot data
3. **EXPLAIN ANALYZE is essential**: "I think this is faster" doesn't cut it in production
4. **Cache invalidation is hard**: TTL-based expiry balances freshness vs. complexity
5. **Connection pooling matters**: Reduced overhead by 40%, prevents connection exhaustion
6. **SELECT \* is wasteful**: Fetching only needed columns reduced network transfer by 60%

---

## Next Steps

Potential enhancements:

- [ ] Add full-text search with `pg_trgm`
- [ ] Implement write-through caching
- [ ] Add database replication (read replicas)
- [ ] Benchmark against ClickHouse for analytical queries
- [ ] Add GraphQL endpoint for flexible querying

---

## Contributing

This is a learning project, but suggestions are welcome! Open an issue or PR.

---

## License

MIT License - feel free to use for learning or portfolio purposes.

---

**Built to understand backend & database performance optimization**
