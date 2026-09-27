from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .database import init_db
from .routers import analyze, history, report, whatif


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PROSPECT API",
    description="Predictive Software Project Risk & Engineering Control System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "prospect-api"}


app.include_router(analyze.router)
app.include_router(history.router)
app.include_router(whatif.router)
app.include_router(report.router)
