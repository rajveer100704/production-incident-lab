import uuid

from sqlalchemy import text

from app import payment_client
from app.config import settings
from app.db import connection
from app.tracing import tracer


async def create_order_buggy(customer_id: str, amount: int) -> dict:
    """THE BUG: connection + transaction stay open across a network call.

    Logically correct, operationally unsafe: connection occupancy is now coupled to
    downstream latency, so pool capacity = pool_size / downstream_latency req/s.
    """
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    async with connection() as conn:
        async with conn.begin():
            with tracer.start_as_current_span("db.transaction"):
                await conn.execute(
                    text("INSERT INTO orders(id, customer_id, amount, status) VALUES (:i,:c,:a,'pending')"),
                    {"i": order_id, "c": customer_id, "a": amount})
                ref = await payment_client.charge(order_id, amount)   # <-- connection held here
                await conn.execute(
                    text("UPDATE orders SET status='confirmed', payment_ref=:r WHERE id=:i"),
                    {"r": ref, "i": order_id})
    return {"order_id": order_id, "status": "confirmed"}


async def create_order_fixed(customer_id: str, amount: int) -> dict:
    """FIX: do slow I/O with no DB resources held; then one short transaction.

    Trade-off: charge and insert are no longer atomic. Idempotency key = order_id lets a
    retry/reconciler find a charge whose row never landed (outbox/saga is the full answer).
    """
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    ref = await payment_client.charge(order_id, amount)               # no connection held
    async with connection() as conn:
        async with conn.begin():
            with tracer.start_as_current_span("db.transaction"):
                await conn.execute(
                    text("INSERT INTO orders(id, customer_id, amount, status, payment_ref) "
                         "VALUES (:i,:c,:a,'confirmed',:r)"),
                    {"i": order_id, "c": customer_id, "a": amount, "r": ref})
    return {"order_id": order_id, "status": "confirmed"}


async def create_order(customer_id: str, amount: int) -> dict:
    fn = create_order_fixed if settings.tx_mode == "fixed" else create_order_buggy
    return await fn(customer_id, amount)


async def get_order(order_id: str) -> dict | None:
    async with connection() as conn:
        row = (await conn.execute(text("SELECT id, customer_id, amount, status FROM orders WHERE id=:i"),
                                  {"i": order_id})).mappings().first()
    return dict(row) if row else None
