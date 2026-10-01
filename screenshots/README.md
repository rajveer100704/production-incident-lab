# Evidence Screenshots

These screenshots are the selected artifacts from the actual Docker validation runs.

## Buggy mode

1. `01-buggy-grafana-dashboard.png` — incident dashboard showing elevated 5xx rate, DB pool usage at capacity, increased DB acquisition/hold latency, and pool-timeout activity.
2. `02-buggy-prometheus-db-pool-checked-out.png` — direct Prometheus view of `db_pool_checked_out` reaching 5.
3. `03-buggy-prometheus-timeouts.png` — direct Prometheus view of pool-timeout activity.
4. `04-buggy-postgres-idle-in-transaction.png` — five PostgreSQL sessions observed in `idle in transaction` during the incident.
5. `05-buggy-jaeger-transaction-contains-downstream.png` — trace tree with `downstream.charge` nested under `db.transaction`.

## Fixed mode

6. `06-fixed-grafana-dashboard.png` — post-fix dashboard snapshot showing 0% rolling 5xx at capture time, lower DB acquisition/hold latency, and zero pool-timeout rate.
7. `07-fixed-prometheus-pool-timeouts-zero.png` — `increase(db_pool_timeout_total[15m])` at zero in the fixed window.
8. `08-fixed-prometheus-pool-size.png` — configured pool size of 5.
9. `09-fixed-prometheus-pool-checked-out-post-run.png` — pool returned to 0 checked-out connections after the fixed workload.
10. `10-fixed-jaeger-transaction-sibling-of-downstream.png` — fixed trace with downstream call and DB transaction as siblings under the request span.
