"""Mock payment service. Slow but *healthy*: always returns 200."""
import asyncio
import os
import random
import uuid

from fastapi import FastAPI

BASE = float(os.getenv("DOWNSTREAM_BASE_LATENCY_MS", "50")) / 1000
JITTER = float(os.getenv("DOWNSTREAM_JITTER_MS", "350")) / 1000
app = FastAPI()
_seen: dict[str, str] = {}


@app.post("/charge")
async def charge(body: dict):
    await asyncio.sleep(BASE + random.random() * JITTER)
    ref = _seen.setdefault(body["order_id"], f"pay_{uuid.uuid4().hex[:10]}")  # idempotent
    return {"payment_ref": ref}


@app.get("/health")
async def health():
    return {"status": "ok"}
