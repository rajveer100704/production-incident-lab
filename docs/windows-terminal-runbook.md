# Windows Terminal Runbook

This runbook is the exact PowerShell flow used to validate the final Dockerized project.

## Buggy evidence run

```powershell
cd C:\Users\BIT\Downloads\production-incident-lab-reviewed\production-incident-lab
$env:TX_MODE="buggy"
docker compose up --build -d --wait --wait-timeout 60
python scripts/smoke_test.py
python scripts/load_test.py --base http://localhost:8000 --requests 500 --concurrency 20
```

Evidence queries:

```powershell
docker compose exec postgres psql -U postgres -d orders -c "SELECT pid, state, now()-xact_start AS xact_age, wait_event_type, wait_event, query FROM pg_stat_activity WHERE datname='orders' AND state='idle in transaction';"
```

Prometheus queries:

```text
up{job="order-api"}
db_pool_checked_out
db_pool_size
increase(db_pool_timeout_total[15m])
histogram_quantile(0.95, sum by (le) (rate(db_connection_hold_seconds_bucket[1m])))
histogram_quantile(0.95, sum by (le) (rate(db_connection_acquire_seconds_bucket[1m])))
```

## Fixed validation run

```powershell
docker compose down
$env:TX_MODE="fixed"
docker compose up -d --wait --wait-timeout 60
python scripts/smoke_test.py
python scripts/load_test.py --base http://localhost:8000 --requests 500 --concurrency 20
```

Post-run PostgreSQL verification:

```powershell
docker compose exec postgres psql -U postgres -d orders -c "SELECT pid, state, now()-xact_start AS xact_age, wait_event_type, wait_event, query FROM pg_stat_activity WHERE datname='orders' AND state='idle in transaction';"
```

Expected post-run result for the fixed evidence check:

```text
(0 rows)
```

## Final environment cleanup

When finished:

```powershell
docker compose down
```
