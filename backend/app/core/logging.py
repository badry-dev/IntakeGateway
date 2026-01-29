
import sys
from contextvars import ContextVar
from loguru import logger

# Context variables for propagating task and run IDs through async calls
task_id_context: ContextVar[int | None] = ContextVar("task_id", default=None)
run_id_context: ContextVar[int | None] = ContextVar("run_id", default=None)


def context_filter(record):
    """Add context variables to log records"""
    record["extra"]["task_id"] = task_id_context.get()
    record["extra"]["run_id"] = run_id_context.get()
    return True


# Configure logger with context support
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    enqueue=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{extra[task_id]!s} | {extra[run_id]!s} | "
        "<level>{message}</level>"
    ),
    filter=context_filter
)


def get_logger():
    """Get the configured logger instance"""
    return logger


def set_task_context(task_id: int | None, run_id: int | None = None):
    """
    Set task and run ID context for current execution
    
    Args:
        task_id: Task identifier
        run_id: Task run identifier (optional)
    """
    task_id_context.set(task_id)
    run_id_context.set(run_id)


def clear_task_context():
    """Clear task and run ID context"""
    task_id_context.set(None)
    run_id_context.set(None)


def get_task_context() -> tuple[int | None, int | None]:
    """
    Get current task and run ID context
    
    Returns:
        Tuple of (task_id, run_id)
    """
    return task_id_context.get(), run_id_context.get()
