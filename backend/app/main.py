from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: init database, start scheduler
    yield
    # TODO: shutdown scheduler


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


# TODO: include routers
# from app.api import markets, signals, portfolio
# app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
# app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
# app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
