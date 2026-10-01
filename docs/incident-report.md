# Incident Report — Intermittent `503`s on `POST /orders`

## Executive summary

A small FastAPI order service was intentionally configured with a realistic resource-lifetime failure. In the buggy implementation, a PostgreSQL transaction stays open while the handler waits for a deliberately slow downstream payment HTTP call. Because the application uses a five-connection DB pool, concurrent requests can occupy all five connections while PostgreSQL is mostly idle. New requests then wait for a connection and eventually receive a generic `503 Service Unavailable` response.

The investigation used structured JSON logs, request IDs, Prometheus metrics, Grafana, OpenTelemetry/Jaeger traces, and direct PostgreSQL session inspection. Two plausible initial hypotheses—slow SQL and a failing downstream service—were rejected with evidence before the transaction-scope issue was identified.

The fix moves the downstream HTTP call outside the DB transaction and keeps the transaction limited to the final database write. The matched Docker benchmark reduced the request error rate from 62.8% to 0.2% while keeping the pool size unchanged at five.

## 1. Environment and configuration

Canonical validation environment:

- Windows PowerShell
- Docker Desktop 4.44.3
- Docker Engine 28.3.2
- Docker Compose v2.39.1
- PostgreSQL 16.15
- API image based on Python 3.12-slim
- DB pool size: 5
- DB max overflow: 0
- DB acquisition timeout: 300 ms
- Downstream client timeout: 800 ms
- Prometheus scrape interval: 2 s

The Compose stack includes:

```text
FastAPI order-api
PostgreSQL 16
slow-but-healthy downstream payment mock
Prometheus
Grafana
Jaeger
```

## 2. User-visible symptom

The public API response intentionally does not reveal the underlying failure. A failed request returns a generic temporary-failure response rather than exposing database internals.

The first useful signal is therefore:

```text
POST /orders → intermittent 503
```

while low-concurrency traffic remains healthy.

## 3. Canonical reproduction

The same workload was used for the buggy and fixed comparison:

```text
Requests:   500
Concurrency: 20
DB pool:     5
```

### Buggy result

```text
Success:       186
Failed:        314
Error rate:    62.8%
Throughput:    42.4 req/s
Median:        404.1 ms
P95:           760.0 ms
P99:           877.6 ms
Max:          1204.5 ms
503 responses: 314
Pool peak:     5/5
```

### Fixed result

```text
Success:       499
Failed:          1
Error rate:     0.2%
Throughput:    63.9 req/s
Median:        284.4 ms
P95:           626.6 ms
P99:           796.9 ms
Max:          1025.5 ms
503 responses:   1
Pool peak:     5/5
```

The error-rate reduction is 62.6 percentage points, approximately a 99.7% relative reduction. Throughput increased by approximately 50.7%, median latency fell by approximately 29.6%, and P95 latency fell by approximately 17.6% in the matched runs.

A separate fixed-mode 200-request / 20-concurrency validation completed with 200/200 success and 0% errors. It is supplemental evidence rather than the canonical comparison.

## 4. Investigation approach

The investigation was performed from observable symptoms toward a cause rather than starting from the known injected bug.

### Hypothesis 1 — slow SQL

**Prediction:** database statement execution time should rise materially during the incident.

**Evidence:** in the recorded development investigation, `db_query_duration_seconds` stayed in the millisecond range, with p95 at or below 10 ms. `EXPLAIN ANALYZE` on the primary insert measured approximately 0.19 ms.

**Result:** rejected as the primary bottleneck.

The database was therefore not spending hundreds of milliseconds executing an expensive SQL statement.

### Hypothesis 2 — downstream service outage

**Prediction:** the payment dependency should fail, time out, or return error responses during the original incident.

**Evidence:** in the original incident run used for hypothesis validation, all 76 downstream calls returned successfully with no downstream timeouts or errors. The downstream dependency was slow, but healthy.

**Result:** rejected as the primary explanation for the large pool-starvation failure.

Later fixed-mode runs did expose an independent `downstream_timeout` edge case. That does not change the original diagnosis: the original catastrophic failure was caused by the service holding DB resources across slow downstream I/O.

## 5. Resource telemetry

### Prometheus

The following direct signals were observed:

```text
db_pool_size          = 5
db_pool_checked_out    → 5 during the incident
db_pool_timeout_total  → increased during the buggy run
```

The DB acquisition and hold histograms also moved into the hundreds-of-milliseconds range during the buggy run, while the downstream histogram showed the slow dependency latency.

See:

- `screenshots/02-buggy-prometheus-db-pool-checked-out.png`
- `screenshots/03-buggy-prometheus-timeouts.png`
- `screenshots/01-buggy-grafana-dashboard.png`

### PostgreSQL

During the buggy load, direct inspection of `pg_stat_activity` showed five sessions in:

```text
idle in transaction
```

The active query text for those sessions was the `INSERT INTO orders(...)` statement. This is consistent with a session that has already completed its immediate SQL work but remains inside an open transaction while the application is waiting on another operation.

See:

`​screenshots/04-buggy-postgres-idle-in-transaction.png`

### Trace evidence

The key Jaeger trace has the following structure:

```text
POST /orders
├── http receive
├── db.acquire_connection
├── db.transaction
│      └── downstream.charge
├── http send
└── http send
```

The downstream HTTP call is therefore inside the lifetime of the DB transaction.

See:

`screenshots/05-buggy-jaeger-transaction-contains-downstream.png`

## 6. Root cause

The buggy handler performs:

```text
BEGIN
  INSERT order
  CALL downstream payment service   ← network wait
  UPDATE order
COMMIT
```

The connection is acquired before `BEGIN` and is not released until the transaction completes. The slow downstream call therefore converts dependency latency directly into database connection occupancy.

With a pool of five and 20 concurrent requests, five requests can hold all available connections while they wait on the downstream service. Additional requests cannot acquire a connection within the 300 ms pool timeout and return `503`.

The failure is best described as **database connection starvation caused by an over-broad transaction scope**.

## 7. Fix

The corrected flow is:

```text
CALL downstream payment service   ← no DB connection held
      ↓
BEGIN
  INSERT confirmed order
COMMIT
      ↓
RELEASE connection
```

The DB pool size remains five. No additional database capacity is required to remove the original coupling between downstream latency and connection occupancy.

The fixed trace changes accordingly:

```text
POST /orders
├── http receive
├── downstream.charge
├── db.acquire_connection
├── db.transaction
└── http send
```

`downstream.charge` and `db.transaction` are now siblings under the request span.

See:

`screenshots/10-fixed-jaeger-transaction-sibling-of-downstream.png`

## 8. Fixed-mode validation

The canonical 500-request fixed run produced:

```text
499 successful
1 failed
0.2% error rate
```

The single 503 was classified by application logs as:

```text
error_type = downstream_timeout
```

No DB pool timeout was present in the captured 503 log output for that canonical fixed run.

Prometheus also showed:

```text
increase(db_pool_timeout_total[15m]) = 0
```

for the captured fixed window.

The post-run PostgreSQL check returned:

```text
0 rows
```

for:

```sql
state = 'idle in transaction'
```

This demonstrates that the original idle-in-transaction resource retention was removed.

See:

- `screenshots/06-fixed-grafana-dashboard.png`
- `screenshots/07-fixed-prometheus-pool-timeouts-zero.png`
- `screenshots/08-fixed-prometheus-pool-size.png`
- `screenshots/09-fixed-prometheus-pool-checked-out-post-run.png`

## 9. Before/after benchmark

| Metric | Buggy | Fixed |
|---|---:|---:|
| Requests | 500 | 500 |
| Concurrency | 20 | 20 |
| Success | 186 | 499 |
| Failed | 314 | 1 |
| Error rate | 62.8% | 0.2% |
| Throughput | 42.4 req/s | 63.9 req/s |
| Median latency | 404.1 ms | 284.4 ms |
| P95 latency | 760.0 ms | 626.6 ms |
| P99 latency | 877.6 ms | 796.9 ms |
| Max latency | 1204.5 ms | 1025.5 ms |
| DB pool peak | 5/5 | 5/5 |
| DB pool timeout in captured fixed window | incident-level | 0 |
| Idle-in-transaction sessions after run | observed during incident | 0 after run |

## 10. Why increasing the pool is not the root fix

Increasing the pool from five to 50 would not remove the architectural problem. It would simply allow more concurrent requests to occupy database connections while waiting on the downstream service.

That can postpone the visible failure while increasing database connection pressure.

The direct fix is to minimize the lifetime of scarce resources.

## 11. Residual failure and consistency trade-off

The fixed flow has an intentional consistency boundary:

```text
charge succeeds
      ↓
DB write fails
      ↓
external charge exists without a confirmed local row
```

A production payment system should address this with a stable idempotency key and a durable workflow such as a pending state plus outbox/saga/reconciliation mechanism. This exercise does not add that infrastructure because the focus is transaction scope and incident diagnosis.

The downstream client timeout is bounded, and automatic unbounded retries are deliberately avoided. Retrying a resource-constrained operation can amplify load and turn a localized dependency problem into a retry storm.

## 12. Prevention and detection

Runtime controls:

- keep external network I/O outside DB transactions;
- bound DB connection acquisition time;
- bound downstream connection/read/total timeouts;
- add backpressure when concurrency can exceed scarce resource capacity.

Observability:

- alert on sustained DB pool utilization above the operating threshold;
- alert on DB connection acquisition latency;
- alert on non-zero pool timeouts;
- alert on unusual `idle in transaction` session counts;
- keep SQL execution and DB connection hold time as separate metrics.

Database safeguards:

- monitor `pg_stat_activity` for long-lived `idle in transaction` sessions;
- consider an appropriate PostgreSQL `idle_in_transaction_session_timeout` policy.

Testing controls:

- load-test concurrency above DB pool capacity;
- retain a regression test for the original failure shape;
- validate dependency timeouts separately from pool-starvation scenarios.

## 13. Known limitations

- Measurements are single-process/single-host experiments and therefore vary with CPU scheduling and local network timing.
- Percentiles displayed in Grafana are computed from Prometheus histogram buckets and are not necessarily identical to exact request-level percentiles from the load-test script.
- The remaining single fixed-run error was an explicitly bounded downstream timeout; the goal of the exercise was to remove the original connection-starvation failure rather than to claim that every dependency failure can be eliminated.

## 14. Evidence manifest

See [`docs/evidence-index.md`](evidence-index.md) for the complete evidence map.

## 15. Final validation commands

The final Docker validation used these commands:

```powershell
$env:TX_MODE="buggy"
docker compose up -d --wait --wait-timeout 60
python scripts/smoke_test.py
python scripts/load_test.py --base http://localhost:8000 --requests 500 --concurrency 20
```

and then:

```powershell
docker compose down
$env:TX_MODE="fixed"
docker compose up -d --wait --wait-timeout 60
python scripts/smoke_test.py
python scripts/load_test.py --base http://localhost:8000 --requests 500 --concurrency 20
```

The repository also contains the exact JSON summaries under `results/canonical-docker/`.
