
from fastapi import FastAPI
from app.api.v1.routes import tasks, runs
from app.core.config import settings

app = FastAPI(title="API→DB Importer", version="0.1.0")

app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV}
