import os
from datetime import datetime, timezone

from fastapi import FastAPI


app = FastAPI(title="cassellas-api", version="0.1.0")
API_NAME = os.getenv("API_NAME", "cassellas-api")
API_PREFIX = f"/API/{API_NAME}"


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"service": "cassellas-api", "status": "ok"}


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/now")
async def get_current_datetime() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "dataatual": now.isoformat(),
        "timezone": "UTC",
    }


@app.get(f"{API_PREFIX}/now")
async def get_current_datetime_with_prefix() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "api": API_NAME,
        "dataatual": now.isoformat(),
        "timezone": "UTC",
    }