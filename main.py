from fastapi import FastAPI


app = FastAPI(title="cassellas-api", version="0.1.0")


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"service": "cassellas-api", "status": "ok"}


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "healthy"}