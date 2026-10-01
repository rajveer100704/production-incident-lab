"""Small end-to-end smoke check for a running Docker Compose stack."""
import sys
import httpx


def main() -> int:
    base = "http://localhost:8000"
    checks = {
        "live": "http://localhost:8000/health/live",
        "ready": "http://localhost:8000/health/ready",
        "metrics": "http://localhost:8000/metrics",
        "prometheus": "http://localhost:9090/-/ready",
        "grafana": "http://localhost:3000/api/health",
        "jaeger": "http://localhost:16686/",
    }
    with httpx.Client(timeout=5.0) as client:
        live = client.get(checks["live"])
        ready = client.get(checks["ready"])
        order = client.post(f"{base}/orders", json={"customer_id": "smoke", "amount": 123})
        metrics = client.get(checks["metrics"])
        prometheus = client.get(checks["prometheus"])
        grafana = client.get(checks["grafana"])
        jaeger = client.get(checks["jaeger"])

    assert live.status_code == 200, live.text
    assert ready.status_code == 200, ready.text
    assert order.status_code == 200, order.text
    assert metrics.status_code == 200 and "db_pool_checked_out" in metrics.text, metrics.text
    assert prometheus.status_code == 200, prometheus.text
    assert grafana.status_code == 200, grafana.text
    assert jaeger.status_code == 200, jaeger.text

    body = order.json()
    assert body["status"] == "confirmed"
    print("smoke test: PASS (API + Prometheus + Grafana + Jaeger)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
