"""Add OAuth2, rate-limit, and cursor/replay fields

Revision ID: 003_p0_oauth_ratelimit_cursor
Revises: 002_add_auth_fields
Create Date: 2026-04-26 00:00:00.000000

Adds support for:
- OAuth2 client_credentials and refresh_token grants (encrypted token cache)
- Rate-limit / 429 retry tuning per task
- Cursor-based incremental fetch + backfill/replay tracking
"""
from alembic import op
import sqlalchemy as sa


revision = '003_p0_oauth_ratelimit_cursor'
down_revision = '002_add_auth_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add OAuth, rate-limit, and cursor columns. All additive and nullable."""

    with op.batch_alter_table('task', schema=None) as batch_op:
        # OAuth2 fields (client_secret, access_token, refresh_token are encrypted)
        batch_op.add_column(sa.Column('oauth_grant_type', sa.String(30), nullable=True))
        batch_op.add_column(sa.Column('oauth_token_url', sa.String(1000), nullable=True))
        batch_op.add_column(sa.Column('oauth_client_id', sa.String(500), nullable=True))
        # Text — Fernet ciphertext can exceed 2000 chars for large client_secrets.
        batch_op.add_column(sa.Column('oauth_client_secret', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('oauth_scope', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('oauth_audience', sa.String(500), nullable=True))
        # Text — encrypted OAuth tokens routinely exceed 2000 chars in the wild.
        batch_op.add_column(sa.Column('oauth_access_token', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('oauth_refresh_token', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('oauth_token_expires_at', sa.DateTime(timezone=True), nullable=True))

        # Rate-limit tuning (overrides for global defaults)
        batch_op.add_column(sa.Column('rate_limit_max_retries', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('rate_limit_max_wait_seconds', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('rate_limit_rps', sa.Integer(), nullable=True))

        # Cursor / incremental fetch state
        batch_op.add_column(sa.Column('cursor_field', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('cursor_param_name', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('cursor_initial_value', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('cursor_last_value', sa.String(500), nullable=True))

    with op.batch_alter_table('task_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cursor_start', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('cursor_end', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('is_backfill', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('is_replay', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('replay_of_run_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('task_run', schema=None) as batch_op:
        batch_op.drop_column('replay_of_run_id')
        batch_op.drop_column('is_replay')
        batch_op.drop_column('is_backfill')
        batch_op.drop_column('cursor_end')
        batch_op.drop_column('cursor_start')

    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('cursor_last_value')
        batch_op.drop_column('cursor_initial_value')
        batch_op.drop_column('cursor_param_name')
        batch_op.drop_column('cursor_field')
        batch_op.drop_column('rate_limit_rps')
        batch_op.drop_column('rate_limit_max_wait_seconds')
        batch_op.drop_column('rate_limit_max_retries')
        batch_op.drop_column('oauth_token_expires_at')
        batch_op.drop_column('oauth_refresh_token')
        batch_op.drop_column('oauth_access_token')
        batch_op.drop_column('oauth_audience')
        batch_op.drop_column('oauth_scope')
        batch_op.drop_column('oauth_client_secret')
        batch_op.drop_column('oauth_client_id')
        batch_op.drop_column('oauth_token_url')
        batch_op.drop_column('oauth_grant_type')
