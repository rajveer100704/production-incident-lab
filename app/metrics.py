from prometheus_client import Counter, Gauge, Histogram

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1, 2, 5)

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram("http_request_duration_seconds", "HTTP latency", ["method", "route"], buckets=BUCKETS)
HTTP_ERRORS = Counter("http_errors_total", "HTTP 5xx by error type", ["route", "error_type"])

DB_POOL_SIZE = Gauge("db_pool_size", "Configured pool size")
DB_POOL_CHECKED_OUT = Gauge("db_pool_checked_out", "Connections currently checked out")
DB_ACQUIRE = Histogram("db_connection_acquire_seconds", "Wait time to get a pooled connection", buckets=BUCKETS)
DB_HOLD = Histogram("db_connection_hold_seconds", "Time a connection stays checked out", buckets=BUCKETS)
DB_POOL_TIMEOUT = Counter("db_pool_timeout_total", "Requests that timed out waiting for a connection")
DB_QUERY = Histogram("db_query_duration_seconds", "Pure SQL execution time", buckets=BUCKETS)

DOWNSTREAM_REQUESTS = Counter("downstream_requests_total", "Downstream calls", ["outcome"])
DOWNSTREAM_LATENCY = Histogram("downstream_request_duration_seconds", "Downstream call latency", buckets=BUCKETS)
