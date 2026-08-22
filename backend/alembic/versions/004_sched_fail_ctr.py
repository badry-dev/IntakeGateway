"""Add consecutive_failures counter to task_schedule

Revision ID: 004_sched_fail_ctr
Revises: 003_p0_oauth_ratelimit_cursor
Create Date: 2026-08-22 00:00:00.000000

Tracks consecutive scheduler dispatch failures per schedule so operators can
detect tasks whose cron jobs repeatedly fail to enqueue. Reset to 0 on each
successful dispatch.
"""
from alembic import op
import sqlalchemy as sa


# Revision id must fit alembic_version.version_num VARCHAR(32).
revision = '004_sched_fail_ctr'
down_revision = '003_p0_oauth_ratelimit_cursor'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('task_schedule', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'consecutive_failures',
                sa.Integer(),
                nullable=False,
                server_default=sa.text('0'),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('task_schedule', schema=None) as batch_op:
        batch_op.drop_column('consecutive_failures')
