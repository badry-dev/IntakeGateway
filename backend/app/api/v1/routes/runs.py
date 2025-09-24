
from fastapi import APIRouter
router = APIRouter()

@router.post("/{task_id}/run")
def run_task(task_id: int):
    # In MVP, just respond. Scheduler/worker will be wired to enqueue real runs.
    return {"enqueued": True, "task_id": task_id}
