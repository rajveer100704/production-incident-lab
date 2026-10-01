import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as PoolTimeout

from app import orders, payment_client
from app.config import settings
from app.db import connection, engine, init_db
from app.logging_setup import request_id_var, setup_logging
from app.metrics import DB_POOL_TIMEOUT, HTTP_ERRORS, HTTP_LATENCY, HTTP_REQUESTS
from app.tracing import setup_tracing

log = setup_logging()
setup_tracing()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    log.info("started", extra={"fields": {"tx_mode": settings.tx_mode, "pool_size": settings.db_pool_size}})
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app, excluded_urls="metrics,health")
except Exception:  # tracing is best-effort
    pass


class OrderIn(BaseModel):
    customer_id: str
    amount: int = Field(gt=0)


GENERIC_503 = {"detail": "temporary service failure"}  # deliberately opaque


@app.middleware("http")
async def observe(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    request_id_var.set(rid)
    t0 = time.perf_counter()
    request.state.error_type = None
    status = 500
    try:
        resp = await call_next(request)
        status = resp.status_code
        resp.headers["x-request-id"] = rid
        return resp
    finally:
        dur = time.perf_counter() - t0
        route = getattr(request.scope.get("route"), "path", request.url.path)
        HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
        HTTP_LATENCY.labels(request.method, route).observe(dur)
        if status >= 500:
            HTTP_ERRORS.labels(route, request.state.error_type or "unknown").inc()
        if route not in ("/metrics", "/health/live"):
            fields = {"route": route, "method": request.method, "status": status,
                      "duration_ms": round(dur * 1000, 1)}
            if request.state.error_type:
                fields["error_type"] = request.state.error_type
            (log.error if status >= 500 else log.info)("request", extra={"fields": fields})


@app.post("/orders")
async def create_order(body: OrderIn, request: Request):
    try:
        return await orders.create_order(body.customer_id, body.amount)
    except PoolTimeout:
        DB_POOL_TIMEOUT.inc()
        request.state.error_type = "db_pool_timeout"
    except payment_client.DownstreamError as e:
        request.state.error_type = e.error_type
    return JSONResponse(GENERIC_503, status_code=503)


@app.get("/orders/{order_id}")
async def read_order(order_id: str, request: Request):
    try:
        o = await orders.get_order(order_id)
    except PoolTimeout:
        DB_POOL_TIMEOUT.inc()
        request.state.error_type = "db_pool_timeout"
        return JSONResponse(GENERIC_503, status_code=503)
    if not o:
        raise HTTPException(404, "not found")
    return o


@app.get("/health/live")
async def live():
    return {"status": "alive"}  # process only; never depends on dependencies


@app.get("/health/ready")
async def ready():
    deps = {"postgres": "ok", "downstream": "ok"}
    try:
        async with connection() as c:
            await c.execute(text("SELECT 1"))
    except Exception:
        deps["postgres"] = "fail"
    if not await payment_client.ping():
        deps["downstream"] = "fail"
    ok = all(v == "ok" for v in deps.values())
    return JSONResponse({"status": "ready" if ok else "not_ready", "dependencies": deps},
                        status_code=200 if ok else 503)


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
