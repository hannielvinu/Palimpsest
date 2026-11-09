from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import SAMPLES, router, sample_inputs
from .core.config import ROOT, STEPS
from .core.storage import init


@asynccontextmanager
async def lifespan(_):
    init()
    if (ROOT / "data" / "samples").is_dir():
        for name in SAMPLES:
            sample_inputs(name)
    yield


app = FastAPI(title="Palimpsest", version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/healthz")
def health():
    return {"status": "ok", "steps": STEPS}


static = ROOT / "frontend" / "dist"
if (static / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def index():
    path = static / "index.html"
    return FileResponse(path) if path.is_file() else HTMLResponse("<h1>Palimpsest</h1><p>Build the frontend to open the investigation desk.</p>")
