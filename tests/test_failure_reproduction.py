"""Regression test for the incident: pool=2, downstream=200ms, 12 concurrent requests.

buggy: connection held across the 200ms call -> only ~2 fit per 200ms -> pool timeouts (503)
fixed: connection held ~ms -> all succeed
"""
import asyncio

from app.config import settings


async def burst(client, n=12):
    rs = await asyncio.gather(*(client.post("/orders", json={"customer_id": f"c{i}", "amount": 5}) for i in range(n)))
    return [r.status_code for r in rs], rs


async def test_buggy_mode_exhausts_pool(client, monkeypatch):
    monkeypatch.setattr(settings, "tx_mode", "buggy")
    codes, rs = await burst(client)
    assert 503 in codes and 200 in codes            # intermittent, not total outage
    bad = next(r for r in rs if r.status_code == 503)
    assert bad.json() == {"detail": "temporary service failure"}  # API hides the cause


async def test_fixed_mode_survives_same_burst(client, monkeypatch):
    monkeypatch.setattr(settings, "tx_mode", "fixed")
    codes, _ = await burst(client)
    assert set(codes) == {200}


async def test_downstream_timeout_releases_resources(client, monkeypatch):
    """Live-interview variation: downstream slower than client timeout must fail cleanly and not leak connections."""
    from app import payment_client
    from app.db import engine
    monkeypatch.setattr(settings, "tx_mode", "buggy")
    import httpx

    def slow(request):  # ASGITransport ignores timeouts, so simulate the timeout the real client raises
        raise httpx.ReadTimeout("downstream slower than client timeout")

    monkeypatch.setattr(payment_client, "_client", httpx.AsyncClient(
        transport=httpx.MockTransport(slow), base_url="http://d"))
    r = await client.post("/orders", json={"customer_id": "c", "amount": 5})
    assert r.status_code == 503
    assert engine.sync_engine.pool.checkedout() == 0   # connection returned, tx rolled back
