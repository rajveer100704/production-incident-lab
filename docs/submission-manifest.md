# Submission Manifest

## Repository contents

- FastAPI service with buggy and fixed transaction modes
- PostgreSQL 16 dependency
- Slow-but-healthy downstream payment mock
- Dockerfile and Docker Compose stack
- Prometheus configuration
- Grafana provisioned dashboard
- OpenTelemetry/Jaeger tracing
- Structured logging and request IDs
- Regression/integration tests
- GitHub Actions CI configuration
- Canonical Docker result JSON files
- Full incident report
- Evidence index
- Demo script
- Windows terminal runbook
- Final screenshots

## Canonical measurements

Buggy 500/20:

```text
186/500 success
62.8% error rate
42.4 req/s
median 404.1 ms
p95 760.0 ms
p99 877.6 ms
DB pool peak 5/5
```

Fixed 500/20:

```text
499/500 success
0.2% error rate
63.9 req/s
median 284.4 ms
p95 626.6 ms
p99 796.9 ms
DB pool peak 5/5
```

Fixed post-run PostgreSQL state:

```text
0 idle-in-transaction rows
```

## Evidence files

All selected screenshots are stored under `screenshots/` and are referenced by the incident report and evidence index.

## External submission items

The repository itself is complete. The only artifacts that must be created outside the repository are the GitHub repository URL and the final 4–6 minute screen recording; `docs/demo-script.md` contains the exact narration and sequence for that recording.
