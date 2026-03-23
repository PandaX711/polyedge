import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, markets, portfolio, signals, worldcup
from app.config import settings
from app.database import init_db
from app.services.scheduler import collect_prices, run_strategies, scan_markets, snapshot_volumes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")

    scheduler.add_job(scan_markets, "interval", seconds=settings.market_scan_interval_sec, id="scan_markets")
    scheduler.add_job(collect_prices, "interval", seconds=settings.price_collect_interval_sec, id="collect_prices")
    scheduler.add_job(run_strategies, "interval", seconds=settings.strategy_run_interval_sec, id="run_strategies")
    scheduler.add_job(snapshot_volumes, "cron", hour=0, minute=5, id="snapshot_volumes")  # Daily at 00:05 UTC
    scheduler.start()
    logger.info("Scheduler started")

    # Run initial scan on startup
    try:
        await scan_markets()
        await collect_prices()
        await snapshot_volumes()
    except Exception as e:
        logger.error("Initial scan failed: %s", e)

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(worldcup.router, prefix="/api/worldcup", tags=["worldcup"])


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


@app.post("/api/trigger/scan")
async def trigger_scan():
    """Manually trigger market scan."""
    await scan_markets()
    return {"ok": True}


@app.post("/api/trigger/prices")
async def trigger_prices():
    """Manually trigger price collection."""
    await collect_prices()
    return {"ok": True}


@app.post("/api/trigger/strategies")
async def trigger_strategies():
    """Manually trigger strategy run."""
    await run_strategies()
    return {"ok": True}
