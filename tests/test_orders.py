async def test_create_and_get_order(client):
    r = await client.post("/orders", json={"customer_id": "c1", "amount": 100})
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    assert "x-request-id" in r.headers
    g = await client.get(f"/orders/{r.json()['order_id']}")
    assert g.status_code == 200 and g.json()["amount"] == 100


async def test_validation_and_404(client):
    assert (await client.post("/orders", json={"customer_id": "c", "amount": -1})).status_code == 422
    assert (await client.get("/orders/nope")).status_code == 404


async def test_health(client):
    assert (await client.get("/health/live")).json() == {"status": "alive"}
    r = await client.get("/health/ready")
    assert r.status_code == 200 and r.json()["dependencies"]["postgres"] == "ok"


async def test_metrics_exposed(client):
    t = (await client.get("/metrics")).text
    for m in ("db_pool_checked_out", "db_connection_acquire_seconds", "db_connection_hold_seconds",
              "db_pool_timeout_total", "downstream_request_duration_seconds"):
        assert m in t
