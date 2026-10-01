#!/bin/sh
# Usage: scripts/run_experiment.sh <buggy|fixed> <label> <requests> <concurrency>
# Starts downstream + API fresh, runs load, collects metrics, then cleans up.
set -eu

MODE=${1:?mode required: buggy|fixed}
LABEL=${2:?label required}
N=${3:-200}
C=${4:-20}

case "$MODE" in
  buggy|fixed) ;;
  *) echo "mode must be buggy or fixed" >&2; exit 2 ;;
esac

mkdir -p results
export DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@localhost:5432/orders}
export DOWNSTREAM_URL=http://localhost:9000
export DB_POOL_SIZE=${DB_POOL_SIZE:-5}
export DB_POOL_TIMEOUT_S=${DB_POOL_TIMEOUT_S:-0.3}
export DOWNSTREAM_BASE_LATENCY_MS=${DOWNSTREAM_BASE_LATENCY_MS:-50}
export DOWNSTREAM_JITTER_MS=${DOWNSTREAM_JITTER_MS:-350}
export TX_MODE=$MODE

echo "Waiting for local Postgres at localhost:5432..."
python - <<'PY'
import socket, sys, time
for _ in range(40):
    try:
        with socket.create_connection(("localhost", 5432), timeout=0.5):
            break
    except OSError:
        time.sleep(0.25)
else:
    print("Postgres was not reachable on localhost:5432", file=sys.stderr)
    sys.exit(1)
PY

python -m uvicorn downstream.main:app --host 127.0.0.1 --port 9000 --log-level warning & DS=$!
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning > "results/$LABEL.app.log" 2>&1 & API=$!

cleanup() {
  kill "$DS" "$API" 2>/dev/null || true
  wait "$DS" "$API" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python - <<'PY'
import sys, time, urllib.request
for _ in range(80):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=1) as r:
            if r.status == 200:
                break
    except Exception:
        time.sleep(0.25)
else:
    print("API did not become ready", file=sys.stderr)
    sys.exit(1)
PY

python scripts/load_test.py --base http://127.0.0.1:8000 --label "$LABEL" --requests "$N" --concurrency "$C" --out "results/$LABEL.load.json" > /dev/null
python scripts/collect_metrics.py http://127.0.0.1:8000 "results/$LABEL.metrics.json" > /dev/null
METRICS_OUT="results/$LABEL.prom.txt" python - <<'PY'
import os
import urllib.request
with urllib.request.urlopen("http://127.0.0.1:8000/metrics", timeout=3) as r:
    with open(os.environ["METRICS_OUT"], "wb") as f:
        f.write(r.read())
PY

echo "== $LABEL (tx_mode=$MODE) =="
cat "results/$LABEL.load.json"
cat "results/$LABEL.metrics.json"
