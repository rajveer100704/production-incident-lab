# Evidence Index

This repository contains the evidence collected during the final Docker validation and links each artifact to the claim it supports.

| ID | Artifact | What it proves |
|---|---|---|
| E1 | `screenshots/01-buggy-grafana-dashboard.png` | Buggy-mode dashboard shows elevated 5xx rate, DB pool at 5/5, increased DB acquisition/hold latency, downstream latency, and pool-timeout activity. |
| E2 | `screenshots/02-buggy-prometheus-db-pool-checked-out.png` | Prometheus directly records `db_pool_checked_out` reaching the configured pool capacity of 5. |
| E3 | `screenshots/03-buggy-prometheus-timeouts.png` | Prometheus directly records the `db_pool_timeout_total` increase during the incident. |
| E4 | `screenshots/04-buggy-postgres-idle-in-transaction.png` | PostgreSQL shows five sessions in `idle in transaction` during the buggy incident. |
| E5 | `screenshots/05-buggy-jaeger-transaction-contains-downstream.png` | Jaeger trace shows `downstream.charge` nested under `db.transaction`, proving external I/O occurs while the transaction is open. |
| E6 | `screenshots/06-fixed-grafana-dashboard.png` | Fixed-mode dashboard shows 0% rolling 5xx at the captured post-run point, lower DB acquisition/hold latency, and zero pool-timeout rate. |
| E7 | `screenshots/07-fixed-prometheus-pool-timeouts-zero.png` | Prometheus shows `increase(db_pool_timeout_total[15m])` at 0 in the fixed evidence window. |
| E8 | `screenshots/08-fixed-prometheus-pool-size.png` | Prometheus confirms configured DB pool size is 5. |
| E9 | `screenshots/09-fixed-prometheus-pool-checked-out-post-run.png` | Prometheus shows the pool returned to 0 checked-out connections after the fixed run. |
| E10 | `screenshots/10-fixed-jaeger-transaction-sibling-of-downstream.png` | Fixed trace shows `downstream.charge` as a sibling of `db.transaction` under `POST /orders`, rather than inside the transaction. |

## Canonical numbers

The matched 500-request / 20-concurrency measurements are stored as JSON under `results/canonical-docker/` and summarized in `docs/incident-report.md`.

## Interpretation rule

Run-level request counts and percentiles come from `scripts/load_test.py`. Prometheus/Grafana screenshots are time-series evidence over a rolling observation window. They are supporting telemetry, not a replacement for the run-specific load-test output.
