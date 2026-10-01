"""Engine + instrumented connection helper.

`connection()` is the ONLY way the app gets a DB connection, so acquire-wait and
hold-time are measured in one place.
"""
import time
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.metrics import DB_ACQUIRE, DB_HOLD, DB_POOL_CHECKED_OUT, DB_POOL_SIZE, DB_QUERY
from app.tracing import tracer

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_s,
    pool_pre_ping=False,
)

DB_POOL_SIZE.set(settings.db_pool_size)
DB_POOL_CHECKED_OUT.set_function(lambda: engine.sync_engine.pool.checkedout())


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before(conn, cursor, statement, parameters, context, executemany):
    conn.info["_q_start"] = time.perf_counter()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after(conn, cursor, statement, parameters, context, executemany):
    DB_QUERY.observe(time.perf_counter() - conn.info.pop("_q_start"))


@asynccontextmanager
async def connection():
    """Acquire a pooled connection; records wait time, hold time and spans."""
    t0 = time.perf_counter()
    with tracer.start_as_current_span("db.acquire_connection") as span:
        try:
            conn = await engine.connect()  # raises sqlalchemy.exc.TimeoutError if pool exhausted
        except Exception as exc:
            waited = time.perf_counter() - t0
            DB_ACQUIRE.observe(waited)
            span.record_exception(exc)
            raise
        DB_ACQUIRE.observe(time.perf_counter() - t0)
    held_from = time.perf_counter()
    try:
        yield conn
    finally:
        await conn.close()  # returns to pool
        DB_HOLD.observe(time.perf_counter() - held_from)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(
            """CREATE TABLE IF NOT EXISTS orders (
                 id TEXT PRIMARY KEY,
                 customer_id TEXT NOT NULL,
                 amount INTEGER NOT NULL,
                 status TEXT NOT NULL,
                 payment_ref TEXT,
                 created_at TIMESTAMPTZ NOT NULL DEFAULT now())"""))
