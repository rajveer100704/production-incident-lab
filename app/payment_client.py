import time

import httpx

from app.config import settings
from app.logging_setup import request_id_var
from app.metrics import DOWNSTREAM_LATENCY, DOWNSTREAM_REQUESTS
from app.tracing import tracer

_client = httpx.AsyncClient(
    base_url=settings.downstream_url,
    timeout=httpx.Timeout(settings.downstream_timeout_s, connect=0.2),  # bounded, no retries
    limits=httpx.Limits(max_connections=200),
)


class DownstreamError(Exception):
    def __init__(self, error_type: str):
        self.error_type = error_type
        super().__init__(error_type)


async def charge(order_id: str, amount: int) -> str:
    t0 = time.perf_counter()
    with tracer.start_as_current_span("downstream.charge") as span:
        span.set_attribute("order.id", order_id)
        try:
            rid = request_id_var.get()
            r = await _client.post(
                "/charge",
                json={"order_id": order_id, "amount": amount},
                headers={"Idempotency-Key": order_id, "X-Request-ID": rid},
            )
            span.set_attribute("request.id", rid)
            r.raise_for_status()
            DOWNSTREAM_REQUESTS.labels("ok").inc()
            return r.json()["payment_ref"]
        except httpx.TimeoutException:
            DOWNSTREAM_REQUESTS.labels("timeout").inc()
            raise DownstreamError("downstream_timeout")
        except httpx.HTTPError:
            DOWNSTREAM_REQUESTS.labels("error").inc()
            raise DownstreamError("downstream_error")
        finally:
            DOWNSTREAM_LATENCY.observe(time.perf_counter() - t0)


async def ping() -> bool:
    try:
        return (await _client.get("/health", timeout=0.3)).status_code == 200
    except httpx.HTTPError:
        return False
