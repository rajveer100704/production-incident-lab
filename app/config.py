from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/orders"
    downstream_url: str = "http://localhost:9000"
    db_pool_size: int = 5
    db_max_overflow: int = 0
    db_pool_timeout_s: float = 0.3      # how long a request waits for a pooled connection
    downstream_timeout_s: float = 0.8   # total timeout for payment call
    # buggy = downstream call inside DB transaction (the incident)
    # fixed = downstream call first, short DB transaction after
    tx_mode: str = "buggy"
    otlp_endpoint: str = ""             # e.g. http://jaeger:4318
    service_name: str = "order-api"


settings = Settings()
