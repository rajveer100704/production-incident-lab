import os

# must be set before app modules import (engine/pool built at import time)
os.environ.setdefault("DB_POOL_SIZE", "2")
os.environ.setdefault("DB_POOL_TIMEOUT_S", "0.2")
os.environ.setdefault("DOWNSTREAM_BASE_LATENCY_MS", "200")
os.environ.setdefault("DOWNSTREAM_JITTER_MS", "0")

import httpx
import pytest_asyncio

from app import payment_client
from app.db import init_db
from app.main import app
from downstream.main import app as downstream_app


@pytest_asyncio.fixture(scope="session")
async def client():
    # route the payment client to the in-process mock downstream
    payment_client._client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=downstream_app), base_url="http://downstream",
        timeout=httpx.Timeout(0.8))
    await init_db()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api") as c:
        yield c
