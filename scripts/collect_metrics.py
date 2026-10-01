"""Scrape /metrics and print the incident-relevant numbers (p50/p95 from histogram buckets)."""
import json
import re
import sys

import httpx

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
out = sys.argv[2] if len(sys.argv) > 2 else None
text = httpx.get(f"{base}/metrics").text


def hist(name):
    b = [(float(m.group(1).replace("+Inf", "inf")), float(m.group(2)))
         for m in re.finditer(rf'^{name}_bucket{{le="([^"]+)"}} ([\d.e+]+)', text, re.M)]
    n = b[-1][1] if b else 0
    def q(p):
        for le, c in b:
            if n and c >= p * n:
                return le
        return None
    return {"count": int(n), "p50_le_s": q(0.5), "p95_le_s": q(0.95)}


def val(name):
    m = re.search(rf"^{name} ([\d.e+]+)", text, re.M)
    return float(m.group(1)) if m else None


res = {
    "db_connection_acquire_seconds": hist("db_connection_acquire_seconds"),
    "db_connection_hold_seconds": hist("db_connection_hold_seconds"),
    "db_query_duration_seconds": hist("db_query_duration_seconds"),
    "downstream_request_duration_seconds": hist("downstream_request_duration_seconds"),
    "db_pool_timeout_total": val("db_pool_timeout_total"),
    "downstream": {k: val(f'downstream_requests_total{{outcome="{k}"}}') for k in ("ok", "timeout", "error")},
}
print(json.dumps(res, indent=2))
if out:
    json.dump(res, open(out, "w"), indent=2)
