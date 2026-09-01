from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import column_mappings, connections, runs, schedules, tasks
from app.api.v1.routes.column_mappings import oracle_router
from app.core.auth import enforce_api_token_configured, require_api_token
from app.core.config import settings
from app.db.session import init_app_database

enforce_api_token_configured()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app_database()
    yield


_docs_enabled = settings.APP_ENV != "production"

app = FastAPI(
    title="IntakeGateway",
    version="0.1.0",
    lifespan=lifespan,
    # Interactive API docs are a development convenience; don't expose the
    # API surface description on production deployments.
    docs_url="/docs" if _docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local React dev server
        "http://localhost:5173",  # Local Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    if settings.APP_ENV == "development"
    else [settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Real router-level dependencies (NOT dependency_overrides, which only
# replaces existing dependencies and would leave routes unauthenticated).
app.include_router(
    tasks.router, prefix="/api/v1/tasks", tags=["tasks"], dependencies=[Depends(require_api_token)]
)
app.include_router(
    runs.router, prefix="/api/v1/runs", tags=["runs"], dependencies=[Depends(require_api_token)]
)
app.include_router(
    column_mappings.router,
    prefix="/api/v1/tasks",
    tags=["column_mappings"],
    dependencies=[Depends(require_api_token)],
)
app.include_router(schedules.router, tags=["schedules"], dependencies=[Depends(require_api_token)])
app.include_router(
    connections.router, tags=["connections"], dependencies=[Depends(require_api_token)]
)
app.include_router(
    oracle_router, prefix="/api/v1", tags=["oracle"], dependencies=[Depends(require_api_token)]
)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/")
def root():
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs" if _docs_enabled else None,
        "openapi": "/openapi.json" if _docs_enabled else None,
    }
