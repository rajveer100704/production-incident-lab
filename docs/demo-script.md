# 5-Minute Submission Demo Script

## 0:00–0:35 — State the problem

Say:

> “I built a deliberately small FastAPI order service backed by PostgreSQL and a slow-but-healthy downstream payment mock. The failure I injected is a transaction-scope problem: the buggy handler holds a PostgreSQL connection while waiting for downstream HTTP. I instrumented the service with structured logs, request IDs, Prometheus, Grafana, and OpenTelemetry so I can diagnose the failure from evidence rather than from the API response.”

Show the README architecture diagram.

## 0:35–1:15 — Baseline and reproduction

Run:

```powershell
$env:TX_MODE="buggy"
python scripts/load_test.py --base http://localhost:8000 --requests 500 --concurrency 20
```

Show the terminal result:

```text
500 requests / 20 concurrency
186 success / 314 failed
62.8% error rate
DB pool peak 5/5
```

Say:

> “The endpoint only exposes a generic temporary failure, so the response does not tell me the root cause. The load test shows a reproducible production-style failure under concurrency.”

## 1:15–2:00 — Metrics

Open Grafana and show `01-buggy-grafana-dashboard.png` or the live dashboard.

Point to:

- 5xx error rate
- DB pool reaching 5/5
- DB acquire latency rising
- DB connection hold latency rising
- pool timeout activity

Then show Prometheus `db_pool_checked_out`.

Say:

> “The pool is saturated. That tells me I have a resource problem, but it does not yet identify what is consuming the resource.”

## 2:00–2:40 — Reject the hypotheses

Say:

> “First hypothesis: slow SQL. The recorded investigation shows query execution in the millisecond range, with p95 at or below 10 milliseconds and an `EXPLAIN ANALYZE` measurement of about 0.19 milliseconds for the main insert. So SQL execution is not the bottleneck.”

Then:

> “Second hypothesis: downstream outage. In the original incident run the downstream calls all succeeded. It is slow, but healthy. So downstream failure does not explain the catastrophic pool exhaustion.”

## 2:40–3:25 — Prove the root cause

Show the PostgreSQL `idle in transaction` evidence.

Say:

> “PostgreSQL shows five sessions sitting in `idle in transaction`. That means the database session is holding an open transaction while not actively executing SQL.”

Then open the Jaeger trace.

Point directly to:

```text
 db.transaction
     └── downstream.charge
```

Say:

> “The trace gives me the causal proof: the downstream HTTP call is nested inside the DB transaction. So network latency is extending the lifetime of a scarce database connection.”

## 3:25–4:05 — Explain the fix

Show the code or the flow diagram.

Say:

> “I did not increase the pool size. I moved the downstream call outside the transaction. The DB connection is now acquired only for the short database operation.”

Show:

```text
fixed:
downstream charge
      ↓
short DB transaction
      ↓
release connection
```

## 4:05–4:45 — Validate

Show the fixed result:

```text
500 requests / 20 concurrency
499 success / 1 failed
0.2% error rate
63.9 req/s
median 284.4 ms
P95 626.6 ms
DB pool peak 5/5
```

Then show the fixed Prometheus timeout graph and the PostgreSQL post-run check with zero `idle in transaction` rows.

Say:

> “The matched benchmark moves from 62.8% errors to 0.2%. The single remaining error is classified as a downstream timeout, not a DB pool timeout. The original resource-starvation mechanism is gone.”

## 4:45–5:00 — Trade-off

Say:

> “The fix changes the consistency boundary: payment can succeed before the local database write. A production payment workflow would solve that with idempotency and a durable reconciliation or outbox/saga mechanism. I kept that trade-off explicit because the exercise is about diagnosis and reliable resource handling.”
