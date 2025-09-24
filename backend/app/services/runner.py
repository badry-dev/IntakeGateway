
from app.db.session import SessionLocal
from app.db.models.task import Task

def run_import(task_id: int):
    # Placeholder that will fetch task, call API, map, and insert into Oracle.
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if not task:
            raise ValueError("Task not found")
        # TODO: implement full pipeline
        return {"task_id": task_id, "inserted": 0}
    finally:
        db.close()
