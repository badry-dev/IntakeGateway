#!/usr/bin/env python
"""Test script to directly query task_run table and debug runs endpoint"""

import sys
from app.db.session import SessionLocal
from app.db.models.task_run import TaskRun
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_runs_query():
    """Test the runs query directly"""
    logger.info("Connecting to database...")
    logger.info(f"Using connection: {settings.sqlalchemy_url}")
    
    try:
        db = SessionLocal()
        
        # Test 1: Count total records
        logger.info("\n=== Test 1: Count Records ===")
        count = db.query(TaskRun).count()
        logger.info(f"Total TaskRun records: {count}")
        
        # Test 2: Get all records
        logger.info("\n=== Test 2: Get All Records (raw) ===")
        all_runs = db.query(TaskRun).all()
        logger.info(f"Retrieved {len(all_runs)} runs")
        
        # Test 3: Get recent records ordered by id
        logger.info("\n=== Test 3: Get Recent (ordered by id) ===")
        recent = db.query(TaskRun).order_by(TaskRun.id.desc()).limit(5).all()
        logger.info(f"Retrieved {len(recent)} recent runs")
        
        for run in recent:
            logger.info(f"  ID: {run.id}, Task: {run.task_id}, Status: {run.status}, "
                       f"Rows: {run.rows_fetched}/{run.rows_inserted}, "
                       f"Started: {run.started_at}, Ended: {run.ended_at}")
        
        # Test 4: Check for NULL values
        logger.info("\n=== Test 4: Check for NULL values ===")
        null_runs = db.query(TaskRun).filter(
            (TaskRun.started_at == None) | (TaskRun.ended_at == None)
        ).count()
        logger.info(f"Runs with NULL timestamps: {null_runs}")
        
        # Test 5: Simulate the endpoint response
        logger.info("\n=== Test 5: Simulate endpoint response ===")
        runs = db.query(TaskRun).order_by(TaskRun.id.desc()).limit(20).all()
        result = [
            {
                "id": run.id,
                "task_id": run.task_id,
                "status": run.status,
                "rows_fetched": run.rows_fetched,
                "rows_inserted": run.rows_inserted,
                "error_count": run.error_count,
                "started_at": run.started_at,
                "ended_at": run.ended_at,
                "duration_seconds": (run.ended_at - run.started_at).total_seconds() if run.ended_at else None
            }
            for run in runs
        ]
        
        logger.info(f"Response has {len(result)} items")
        for item in result[:3]:  # Show first 3
            logger.info(f"  Item: {item}")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    test_runs_query()
