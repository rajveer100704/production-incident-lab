"""Async load test. Samples db_pool_checked_out from /metrics while running.

python scripts/load_test.py --base http://localhost:8000 --requests 200 --concurrency 20 --out results/x.json
"""
import argparse
import asyncio
import json
import re
import statistics
import time
from collections import Counter

import httpx


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))] if xs else 0.0


async def sample_pool(client, base, stop, peak):
    while not stop.is_set():
        try:
            t = (await client.get(f"{base}/metrics", timeout=1)).text
            m = re.search(r"^db_pool_checked_out ([\d.]+)", t, re.M)
            if m:
                peak.append(float(m.group(1)))
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.05)


async def main(a):
    lat, codes = [], Counter()
    sem = asyncio.Semaphore(a.concurrency)
    peak, stop = [], asyncio.Event()
    limits = httpx.Limits(max_connections=a.concurrency + 5)
    async with httpx.AsyncClient(limits=limits, timeout=10) as c:
        sampler = asyncio.create_task(sample_pool(c, a.base, stop, peak))

        async def one(i):
            async with sem:
                t0 = time.perf_counter()
                try:
                    r = await c.post(f"{a.base}/orders", json={"customer_id": f"c{i}", "amount": 1000 + i})
                    codes[r.status_code] += 1
                except httpx.HTTPError as e:
                    codes[type(e).__name__] += 1
                lat.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(a.requests)))
        wall = time.perf_counter() - t0
        stop.set()
        await sampler

    ok = codes.get(200, 0)
    res = {
        "label": a.label, "requests": a.requests, "concurrency": a.concurrency,
        "success": ok, "failed": a.requests - ok,
        "error_rate_pct": round(100 * (a.requests - ok) / a.requests, 1),
        "throughput_rps": round(a.requests / wall, 1),
        "latency_ms": {"min": round(min(lat), 1), "median": round(statistics.median(lat), 1),
                       "p95": round(pct(lat, 95), 1), "p99": round(pct(lat, 99), 1), "max": round(max(lat), 1)},
        "status_codes": dict(codes),
        "db_pool_peak_checked_out": max(peak) if peak else None,
    }
    print(json.dumps(res, indent=2))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=2)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://localhost:8000")
    p.add_argument("--requests", type=int, default=200)
    p.add_argument("--concurrency", type=int, default=20)
    p.add_argument("--label", default="run")
    p.add_argument("--out")
    asyncio.run(main(p.parse_args()))
