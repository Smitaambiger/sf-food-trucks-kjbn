import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import health, trucks
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, set_request_id

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Finds active mobile food trucks near a given location in San Francisco.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = set_request_id(request.headers.get("x-request-id") or uuid.uuid4().hex[:12])
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["x-request-id"] = request_id
    logger.info("%s %s -> %d (%.1fms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("AppError on %s: %s", request.url.path, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(health.router)
app.include_router(trucks.router)

_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(_static_dir / "index.html")
