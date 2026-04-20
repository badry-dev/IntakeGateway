
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes import tasks, runs, column_mappings, schedules, connections
from app.core.config import settings

app = FastAPI(title="IntakeGateway", version="0.1.0")

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Local React dev server
        "http://localhost:5173",      # Local Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ] if settings.APP_ENV == "development" else [
        settings.FRONTEND_URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
app.include_router(column_mappings.router, prefix="/api/v1/tasks", tags=["column_mappings"])
app.include_router(schedules.router, tags=["schedules"])
app.include_router(connections.router, tags=["connections"])
# Also include oracle metadata routes without /tasks prefix
from app.api.v1.routes.column_mappings import router as oracle_router
app.include_router(oracle_router, prefix="/api/v1", tags=["oracle"])

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV}

@app.get("/")
def root():
    return {
        "name": "IntakeGateway",
        "version": "0.1.1",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }
