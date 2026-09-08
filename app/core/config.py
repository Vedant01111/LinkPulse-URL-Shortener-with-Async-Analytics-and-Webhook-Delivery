from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://linkpulse:linkpulse@db:5432/linkpulse"

    # Redis (used for caching, rate limiting, and as the Celery broker)
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Short code
    short_code_length: int = 7

    # Base URL used when returning shortened links to the client
    base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
