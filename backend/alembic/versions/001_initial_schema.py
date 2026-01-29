"""Initial schema: add task schedule, column mapping, logs tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add indices to existing task table
    op.create_index(
        'ix_task_is_active_updated_at',
        'task',
        ['is_active', 'updated_at'],
        existing_ok=True
    )
    
    # Add foreign key to existing task_run table
    with op.batch_alter_table('task_run', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_task_run_task_id',
            'task',
            ['task_id'],
            ['id'],
            ondelete='CASCADE',
            existing_ok=True
        )
    
    # Update indices on task_run
    op.create_index(
        'ix_task_run_status',
        'task_run',
        ['task_id', 'status'],
        existing_ok=True
    )
    op.create_index(
        'ix_task_run_created',
        'task_run',
        [sa.desc('started_at')],
        existing_ok=True
    )
    
    # Create task_schedule table
    op.create_table(
        'task_schedule',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('task_id', sa.BigInteger(), nullable=False),
        sa.Column('cron_expression', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_run_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='CASCADE', name='fk_task_schedule_task_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', name='uk_task_schedule_task_id')
    )
    op.create_index('ix_task_schedule_is_active', 'task_schedule', ['is_active'])
    op.create_index('ix_task_schedule_next_run', 'task_schedule', ['next_run_date'])
    
    # Create column_mapping table
    op.create_table(
        'column_mapping',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('task_id', sa.BigInteger(), nullable=False),
        sa.Column('source_field', sa.String(255), nullable=False),
        sa.Column('dest_column', sa.String(255), nullable=False),
        sa.Column('transform_rules', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='CASCADE', name='fk_column_mapping_task_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'source_field', name='uk_column_mapping_task_source')
    )
    op.create_index('ix_column_mapping_task_id', 'column_mapping', ['task_id'])
    op.create_index('ix_column_mapping_is_active', 'column_mapping', ['is_active'])
    
    # Create task_log table
    op.create_table(
        'task_log',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('task_run_id', sa.BigInteger(), nullable=False),
        sa.Column('step_name', sa.String(50), nullable=True),
        sa.Column('message', sa.String(1000), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['task_run_id'], ['task_run.id'], ondelete='CASCADE', name='fk_task_log_run_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_log_run_id', 'task_log', ['task_run_id'])
    
    # Create task_run_log table
    op.create_table(
        'task_run_log',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('task_run_id', sa.BigInteger(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=True),
        sa.Column('column_name', sa.String(255), nullable=True),
        sa.Column('error_type', sa.String(50), nullable=True),
        sa.Column('error_message', sa.String(1000), nullable=True),
        sa.Column('source_value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['task_run_id'], ['task_run.id'], ondelete='CASCADE', name='fk_task_run_log_run_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_run_log_run_id', 'task_run_log', ['task_run_id'])


def downgrade() -> None:
    # Drop task_run_log table
    op.drop_index('ix_task_run_log_run_id', table_name='task_run_log')
    op.drop_table('task_run_log')
    
    # Drop task_log table
    op.drop_index('ix_task_log_run_id', table_name='task_log')
    op.drop_table('task_log')
    
    # Drop column_mapping table
    op.drop_index('ix_column_mapping_is_active', table_name='column_mapping')
    op.drop_index('ix_column_mapping_task_id', table_name='column_mapping')
    op.drop_table('column_mapping')
    
    # Drop task_schedule table
    op.drop_index('ix_task_schedule_next_run', table_name='task_schedule')
    op.drop_index('ix_task_schedule_is_active', table_name='task_schedule')
    op.drop_table('task_schedule')
    
    # Drop indices on task_run
    op.drop_index('ix_task_run_created', table_name='task_run')
    op.drop_index('ix_task_run_status', table_name='task_run')
    
    # Remove foreign key from task_run
    with op.batch_alter_table('task_run', schema=None) as batch_op:
        batch_op.drop_constraint('fk_task_run_task_id', type_='foreignkey')
    
    # Drop index on task table
    op.drop_index('ix_task_is_active_updated_at', table_name='task')
