"""Add authentication fields to task table

Revision ID: 002_add_auth_fields
Revises: 001_initial_schema
Create Date: 2026-01-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import oracle

# revision identifiers, used by Alembic.
revision = '002_add_auth_fields'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Add authentication fields to task table"""
    # Add auth_type column
    op.add_column('task', sa.Column('auth_type', sa.String(20), nullable=True))
    
    # Add API key column (encrypted)
    op.add_column('task', sa.Column('api_key', sa.String(500), nullable=True))
    
    # Add username column (for Basic auth)
    op.add_column('task', sa.Column('username', sa.String(200), nullable=True))
    
    # Add password column (encrypted, for Basic auth)
    op.add_column('task', sa.Column('password', sa.String(500), nullable=True))
    
    # Add OAuth config column (JSON)
    op.add_column('task', sa.Column('oauth_config', oracle.CLOB, nullable=True))
    
    # Set default auth_type to 'none' for existing tasks
    op.execute("UPDATE task SET auth_type = 'none' WHERE auth_type IS NULL")


def downgrade():
    """Remove authentication fields from task table"""
    op.drop_column('task', 'oauth_config')
    op.drop_column('task', 'password')
    op.drop_column('task', 'username')
    op.drop_column('task', 'api_key')
    op.drop_column('task', 'auth_type')
