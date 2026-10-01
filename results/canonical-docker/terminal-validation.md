# Canonical Docker Validation Record

The following measurements were captured from the actual terminal runs used for the final Docker validation on 2026-10-01.

## Environment

- Windows PowerShell
- Docker Desktop 4.44.3
- Docker Engine 28.3.2
- Docker Compose v2.39.1
- PostgreSQL 16.15 inside the Compose stack
- API container Python 3.12 image

## Stack health

`docker compose up -d --wait --wait-timeout 60` completed with all seven Compose entries reported healthy/started in the successful final fixed startup.

`python scripts/smoke_test.py` returned:

```text
smoke test: PASS (API + Prometheus + Grafana + Jaeger)
```

## Canonical buggy run

```text
requests: 500
concurrency: 20
success: 186
failed: 314
error_rate_pct: 62.8
throughput_rps: 42.4
median: 404.1 ms
p95: 760.0 ms
p99: 877.6 ms
max: 1204.5 ms
503: 314
DB pool peak: 5/5
```

PostgreSQL inspection during the buggy load returned five sessions in `idle in transaction`. The active SQL shown for those sessions was the `INSERT INTO orders(...)` statement, confirming the database session was idle inside an open transaction rather than spending the time executing SQL.

## Canonical fixed run

```text
requests: 500
concurrency: 20
success: 499
failed: 1
error_rate_pct: 0.2
throughput_rps: 63.9
median: 284.4 ms
p95: 626.6 ms
p99: 796.9 ms
max: 1025.5 ms
503: 1
DB pool peak: 5/5
```

The captured 503 log was classified as `downstream_timeout`; no `db_pool_timeout` appeared in the captured error lines. Prometheus showed `increase(db_pool_timeout_total[15m]) = 0` for the fixed evidence window. A PostgreSQL inspection after the fixed run returned zero rows for `state = 'idle in transaction'`.

## Additional fixed validation

A separate 200-request / 20-concurrency fixed run completed with 200/200 success and 0% errors. This is supplementary validation, not the canonical before/after benchmark.
