from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "PolyEdge"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./polyedge.db"

    # Polymarket
    polymarket_clob_url: str = "https://clob.polymarket.com"
    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    hl_private_key: str = ""  # Polygon wallet private key

    # External APIs
    odds_api_key: str = ""  # the-odds-api.com
    football_data_api_key: str = ""  # football-data.org

    # AI
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-6-20250514"

    # Strategy
    odds_divergence_threshold: float = 0.05  # 5%
    book_ai_agreement_threshold: float = 0.08  # 8%
    max_position_per_market: float = 100.0  # USDC
    max_total_position: float = 1000.0  # USDC

    # Scheduler
    price_collect_interval_sec: int = 60
    market_scan_interval_sec: int = 300
    strategy_run_interval_sec: int = 300

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
