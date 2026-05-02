from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import column_mappings, connections, runs, schedules, tasks
from app.core.config import settings
from app.db.session import init_app_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app_database()
    yield


app = FastAPI(title="IntakeGateway", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
        if settings.APP_ENV == "development"
        else [settings.FRONTEND_URL]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
# Task-scoped mapping routes: /api/v1/tasks/{task_id}/mappings, /preview-fields, etc.
app.include_router(column_mappings.router, prefix="/api/v1/tasks", tags=["column_mappings"])
# Global oracle/utility routes: /api/v1/oracle/tables/..., /api/v1/preview-fields-standalone
app.include_router(column_mappings.router, prefix="/api/v1", tags=["oracle"])
app.include_router(schedules.router, tags=["schedules"])
app.include_router(connections.router, tags=["connections"])


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/")
def root():
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
