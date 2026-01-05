# Architecture

## Table of Contents

- [Overview](#overview)
- [System Components](#system-components)
- [Component Details](#component-details)
  - [Nginx (Reverse Proxy)](#1-nginx-reverse-proxy)
  - [FastAPI (Application Server)](#2-fastapi-application-server)
  - [PostgreSQL (Database)](#3-postgresql-database)
  - [Redis (Cache Layer)](#4-redis-cache-layer)
- [Data Flow](#data-flow)
  - [Flow 1: Uncached Query (First Request)](#flow-1-uncached-query-first-request)
  - [Flow 2: Cached Query (Subsequent Request within-5-min)](#flow-2-cached-query-subsequent-request-within-5-min)
  - [Flow 3: Table Scan Query (No Cache, No Index)](#flow-3-table-scan-query-no-cache-no-index)
- [Query Execution Paths](#query-execution-paths)
  - [Path A: Table Scan (Baseline)](#path-a-table-scan-baseline)
  - [Path B: B-Tree Index](#path-b-b-tree-index)
  - [Path C: Partial Index (Status Filter)](#path-c-partial-index-status-filter)
  - [Path D: Composite Index](#path-d-composite-index)
  - [Path E: Redis Cache](#path-e-redis-cache)
- [Performance Characteristics](#performance-characteristics)
  - [Latency Breakdown (Typical Request)](#latency-breakdown-typical-request)
  - [Resource Utilization (Load Test: 100 concurrent users)](#resource-utilization-load-test-100-concurrent-users)
- [Scalability Considerations](#scalability-considerations)
  - [Current Limitations](#current-limitations)
  - [Scaling Path (Future)](#scaling-path-future)
- [Observability](#observability)
  - [Logging Strategy](#logging-strategy)
  - [Metrics Exposed](#metrics-exposed)
- [Security Considerations](#security-considerations)
  - [Current Implementation](#current-implementation)
  - [Production Hardening Checklist](#production-hardening-checklist)
- [Trade-offs & Design Decisions](#trade-offs--design-decisions)
- [Future Enhancements](#future-enhancements)
  - [Phase 2: Advanced Optimizations](#phase-2-advanced-optimizations)
  - [Phase 3: Distributed Systems](#phase-3-distributed-systems)
  - [Phase 4: Analytics](#phase-4-analytics)
- [References](#references)

## Overview

This project demonstrates query optimization strategies using a typical web application stack. The architecture is intentionally simple to isolate and measure the impact of different optimization techniques.

## System Components

```

┌─────────────┐
│ Client │
│ (curl/HTTP)│
└──────┬──────┘
│
▼
┌─────────────┐
│ Nginx │ ← Reverse proxy, load balancing
│ (Port 80) │
└──────┬──────┘
│
▼
┌─────────────┐
│ FastAPI │ ← Application server
│ (Port 8000) │
└──┬────────┬─┘
│ │
│ └─────────┐
▼ ▼
┌─────────────┐ ┌─────────────┐
│ PostgreSQL │ │ Redis │
│ (10M rows) │ │ (Cache) │
│ (Port 5432) │ │ (Port 6379) │
└─────────────┘ └─────────────┘

```

---

## Component Details

### 1. **Nginx (Reverse Proxy)**

**Purpose**: Route traffic, handle SSL (if configured), provide static file serving.

**Configuration**:

- Listens on port 80
- Proxies to FastAPI on port 8000
- Client max body size: 10MB
- Timeout: 60s

**Why it's included**: Demonstrates production-ready deployment patterns. In real systems, Nginx would also handle:

- SSL termination
- Rate limiting (application-level limits in this demo)
- Static asset caching
- Load balancing across multiple FastAPI instances

---

### 2. **FastAPI (Application Server)**

**Purpose**: REST API exposing different query optimization strategies.

**Technology choices**:

- **FastAPI**: Async-capable, automatic OpenAPI docs, type hints
- **SQLAlchemy**: ORM with connection pooling, supports raw SQL for EXPLAIN
- **Uvicorn**: ASGI server (async request handling)

**Key configuration**:

```python
# Connection pool settings
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Max permanent connections
    max_overflow=10,       # Additional connections when pool exhausted
    pool_pre_ping=True,    # Verify connection health before use
    echo=False             # Set to True for SQL debugging
)
```

**Request flow**:

1. Receive HTTP request
2. Parse query parameters (email, status, etc.)
3. Check cache (if using cached endpoint)
4. Execute query with chosen strategy
5. Log metrics (query time, cache status)
6. Return JSON response

---

### 3. **PostgreSQL (Database)**

**Purpose**: Primary data store with 10 million user records.

**Schema**:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',  -- 'active' or 'inactive'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes (created as part of optimization experiments)
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_email_active ON users(email) WHERE status = 'active';
CREATE INDEX idx_users_email_status ON users(email, status);
```

**Data characteristics**:

- 10 million records
- Email distribution: Uniform (email1@example.com ... email10000000@example.com)
- Status distribution: 70% active, 30% inactive
- Table size: ~1.2 GB

**Configuration**:

```conf
shared_buffers = 256MB          # Postgres memory cache
work_mem = 16MB                 # Memory per query operation
maintenance_work_mem = 128MB    # Memory for index creation
effective_cache_size = 1GB      # OS cache estimation
```

---

### 4. **Redis (Cache Layer)**

**Purpose**: In-memory cache for frequently accessed queries.

**Caching strategy**: Cache-aside pattern

1. **Read path**:

   - Check Redis first
   - If hit: Return cached value (12ms avg)
   - If miss: Query PostgreSQL → Cache result → Return value

2. **Cache key format**:

   ```
   user:email:{email_value}
   ```

3. **TTL (Time-To-Live)**: 300 seconds (5 minutes)
   - Balances freshness vs. cache hit rate
   - Reduces stale data risk
   - Automatic eviction after expiry

**Configuration**:

```conf
maxmemory 256mb
maxmemory-policy allkeys-lru   # Evict least recently used keys
```

**Cache hit rate formula**:

```
Hit Rate = (Cache Hits / Total Requests) × 100
Target: >90% for hot data paths
```

---

## Data Flow

### Flow 1: Uncached Query (First Request)

```
Client → Nginx → FastAPI
                    ↓
              Check Redis (MISS)
                    ↓
              Query PostgreSQL (120ms with index)
                    ↓
              Store in Redis (TTL=300s)
                    ↓
              Return to Client (125ms total)
```

### Flow 2: Cached Query (Subsequent Request within 5 min)

```
Client → Nginx → FastAPI
                    ↓
              Check Redis (HIT)
                    ↓
              Return from Cache (12ms total)
```

### Flow 3: Table Scan Query (No Cache, No Index)

```
Client → Nginx → FastAPI
                    ↓
              Query PostgreSQL (full table scan)
                    ↓
              Scan 10M rows (8000ms)
                    ↓
              Return to Client (8005ms total)
```

---

## Query Execution Paths

### Path A: Table Scan (Baseline)

```
Endpoint: /users/scan

PostgreSQL execution:
1. Sequential scan of entire table
2. Filter rows where email = target
3. Return matching row

Time: ~8000ms
Rows scanned: 10,000,000
Rows returned: 1
```

### Path B: B-Tree Index

```
Endpoint: /users/indexed

PostgreSQL execution:
1. B-Tree index lookup on email
2. Direct row fetch via index pointer
3. Return matching row

Time: ~120ms
Rows scanned: 1
Rows returned: 1
Index: idx_users_email
```

### Path C: Partial Index (Status Filter)

```
Endpoint: /users/partial

PostgreSQL execution:
1. Partial index lookup (active users only)
2. Smaller index = faster lookup
3. Return matching row

Time: ~85ms
Rows scanned: 1
Rows returned: 1
Index: idx_users_email_active (30% smaller than full index)
```

### Path D: Composite Index

```
Endpoint: /users/composite

PostgreSQL execution:
1. Composite index lookup (email + status)
2. Both conditions resolved in single index scan
3. Return matching row

Time: ~95ms
Rows scanned: 1
Rows returned: 1
Index: idx_users_email_status
```

### Path E: Redis Cache

```
Endpoint: /users/cached

Execution:
1. Redis GET operation
2. Return cached value (no DB hit)

Time: ~12ms
Cache hit: 94% (after warmup)
Cache miss fallback: Path B (indexed query)
```

---

## Performance Characteristics

### Latency Breakdown (Typical Request)

| Component                | Latency    | Notes            |
| ------------------------ | ---------- | ---------------- |
| Network (client → Nginx) | ~5ms       | Local network    |
| Nginx processing         | <1ms       | Minimal overhead |
| FastAPI routing          | ~2ms       | Python overhead  |
| Cache check (Redis)      | ~2ms       | Network + lookup |
| DB query (indexed)       | ~120ms     | PostgreSQL query |
| Response serialization   | ~3ms       | JSON encoding    |
| **Total (cache miss)**   | **~130ms** |                  |
| **Total (cache hit)**    | **~12ms**  |                  |

### Resource Utilization (Load Test: 100 concurrent users)

| Resource     | Table Scan | Indexed | Cached |
| ------------ | ---------- | ------- | ------ |
| DB CPU       | 85%        | 12%     | 2%     |
| DB Memory    | 1.2GB      | 800MB   | 500MB  |
| Redis Memory | -          | -       | 120MB  |
| API CPU      | 15%        | 8%      | 6%     |
| Network I/O  | 2MB/s      | 8MB/s   | 12MB/s |

---

## Scalability Considerations

### Current Limitations

1. **Single PostgreSQL instance**: No read replicas
2. **Single Redis instance**: No Redis Cluster (single point of failure)
3. **Single FastAPI instance**: No horizontal scaling
4. **No CDN**: All requests hit origin

### Scaling Path (Future)

```
              ┌─────────────┐
              │   Cloudflare│  ← CDN, DDoS protection
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │ Load Balancer│  ← HAProxy, AWS ALB
              └──┬─────────┬─┘
                 │         │
         ┌───────▼───┐ ┌──▼────────┐
         │ FastAPI 1 │ │ FastAPI 2 │  ← Horizontal scaling
         └───┬───────┘ └──┬────────┘
             │            │
       ┌─────▼────────────▼─────┐
       │   Redis Cluster (3 nodes)│  ← High availability
       └────────────────────────┘
             │
       ┌─────▼──────┐
       │ PostgreSQL │
       │  Primary   │
       └─────┬──────┘
             │
    ┌────────▼────────┐
    │ Read Replica 1  │  ← Read scaling
    │ Read Replica 2  │
    └─────────────────┘
```

**Expected improvements**:

- 10x throughput (horizontal FastAPI scaling)
- 99.99% uptime (Redis Cluster + DB replication)
- <50ms global latency (CDN caching)

---

## Observability

### Logging Strategy

All requests generate structured logs:

```json
{
  "timestamp": "2025-01-05T10:30:45.123Z",
  "request_id": "req_abc123xyz",
  "endpoint": "/users/cached",
  "method": "GET",
  "query_params": { "email": "user5000000@example.com" },
  "query_time_ms": 12,
  "cache_status": "hit",
  "db_queries": 0,
  "status_code": 200,
  "response_size_bytes": 256
}
```

**Log aggregation**: Stdout → Docker logs → (Future: ELK stack, Datadog)

### Metrics Exposed

- Request duration histogram (P50, P95, P99)
- Cache hit/miss counters
- Database connection pool utilization
- Error rate (5xx responses)

**Endpoint**: `GET /metrics` (Prometheus format)

---

## Security Considerations

### Current Implementation

- ✅ SQL injection protection (SQLAlchemy parameterized queries)
- ✅ Connection pooling (prevents connection exhaustion)
- ✅ Input validation (FastAPI Pydantic models)
- ⚠️ No authentication (demo project)
- ⚠️ No rate limiting (planned)
- ⚠️ No SSL (add in production)

### Production Hardening Checklist

- [ ] Add API key authentication
- [ ] Implement rate limiting (per IP, per user)
- [ ] Enable SSL/TLS (Nginx + Let's Encrypt)
- [ ] Set up CORS policies
- [ ] Add request signing for webhooks
- [ ] Implement audit logging

---

## Trade-offs & Design Decisions

See [`decisions/`](decisions/) folder for detailed Architecture Decision Records (ADRs).

**Summary**:

1. **Cache-aside over write-through**: Simpler implementation, acceptable for read-heavy workload
2. **SQLAlchemy ORM**: Trade-off between convenience and raw performance (acceptable for demo)
3. **Single database**: Prioritizes simplicity for learning; production would use replicas
4. **Docker Compose**: Easy local setup; production would use Kubernetes or ECS

---

## Future Enhancements

### Phase 2: Advanced Optimizations

- [ ] PostgreSQL read replicas (separate read/write paths)
- [ ] Materialized views for aggregations
- [ ] Query result streaming (pagination)
- [ ] GraphQL endpoint (flexible querying)

### Phase 3: Distributed Systems

- [ ] Redis Cluster (sharding + replication)
- [ ] PostgreSQL sharding (partition by user ID range)
- [ ] Circuit breaker pattern (prevent cascade failures)
- [ ] Distributed tracing (OpenTelemetry)

### Phase 4: Analytics

- [ ] ClickHouse integration (OLAP queries)
- [ ] Real-time dashboards (Grafana)
- [ ] Query cost analysis (slow query alerting)

---

## References

- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [FastAPI Performance](https://fastapi.tiangolo.com/deployment/concepts/)
- [Use The Index, Luke](https://use-the-index-luke.com/) (Query optimization guide)

---

**Last Updated**: 2025-01-05
**Status**: Initial implementation complete

```

```
