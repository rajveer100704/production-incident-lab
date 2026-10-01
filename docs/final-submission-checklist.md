# Final Submission Checklist

## Repository evidence — complete

- [x] FastAPI service and downstream dependency are implemented.
- [x] Buggy transaction-scope failure is reproducible.
- [x] Fixed transaction-scope implementation is present.
- [x] Structured JSON logs and request IDs are present.
- [x] Prometheus metrics are present and scraped by Prometheus.
- [x] Grafana dashboard is provisioned from the repository.
- [x] OpenTelemetry traces are exported to Jaeger.
- [x] Liveness and readiness endpoints are implemented.
- [x] Regression/integration tests are included.
- [x] GitHub Actions CI is configured for PostgreSQL 16 and Python 3.12.

## Final Docker validation — complete

The final Docker validation was performed on 2026-10-01 using Windows PowerShell, Docker Desktop 4.44.3, Docker Engine 28.3.2, Docker Compose v2.39.1, and PostgreSQL 16.15.

Smoke test result:

```text
smoke test: PASS (API + Prometheus + Grafana + Jaeger)
```

Canonical buggy run:

```text
500 requests / 20 concurrency
186 success / 314 failed
62.8% error rate
42.4 req/s
median 404.1 ms
p95 760.0 ms
p99 877.6 ms
DB pool peak 5/5
```

Canonical fixed run:

```text
500 requests / 20 concurrency
499 success / 1 failed
0.2% error rate
63.9 req/s
median 284.4 ms
p95 626.6 ms
p99 796.9 ms
DB pool peak 5/5
```

The one canonical fixed-run error was classified by application logs as `downstream_timeout`. No DB pool timeout was present in the captured fixed error log lines, and the fixed Prometheus window showed zero increase in `db_pool_timeout_total`.

## Root-cause evidence — complete

- [x] Buggy Grafana dashboard shows 5xx activity and pool saturation.
- [x] Buggy Prometheus `db_pool_checked_out` reaches 5.
- [x] Buggy Prometheus records pool-timeout activity.
- [x] Buggy PostgreSQL inspection shows five `idle in transaction` sessions during load.
- [x] Buggy Jaeger trace shows `downstream.charge` nested inside `db.transaction`.
- [x] Fixed Grafana dashboard shows the post-fix state.
- [x] Fixed Prometheus shows zero DB pool timeout increase in the captured window.
- [x] Fixed PostgreSQL inspection returns zero `idle in transaction` rows after the run.
- [x] Fixed Jaeger trace shows `downstream.charge` as a sibling of `db.transaction`.

All evidence files are listed in [`evidence-index.md`](evidence-index.md).

## Documentation — complete

- [x] `README.md` describes architecture, setup, reproduction, observability, investigation, fix, benchmark, trade-offs, limitations, and AI usage.
- [x] `docs/incident-report.md` contains the full hypothesis → evidence → root-cause → fix → validation narrative.
- [x] `docs/evidence-index.md` maps screenshots to claims.
- [x] `docs/demo-script.md` contains a complete 5-minute narration using the actual benchmark numbers.
- [x] `docs/windows-terminal-runbook.md` contains the PowerShell commands used for validation.
- [x] `docs/submission-manifest.md` enumerates the final repository and evidence contents.

## Repository hygiene — complete

- [x] Python cache directories removed.
- [x] No `.env` file is included.
- [x] `.env.example` is included.
- [x] Final screenshots use descriptive names.
- [x] Canonical Docker results are stored separately from the earlier local-PostgreSQL reference experiment.
- [x] README and incident report use the canonical Docker benchmark for the main before/after comparison.

## External submission actions

The repository artifacts are complete. Submit the GitHub repository URL and the 4–6 minute screen recording using the narration in `docs/demo-script.md`.
