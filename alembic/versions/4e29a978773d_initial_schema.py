"""initial_schema

Revision ID: 4e29a978773d
Revises: 
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4e29a978773d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create PostgreSQL extensions
    # citext is needed for case-insensitive email fields
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    # pgcrypto is needed for gen_random_uuid() function used in UUID primary keys
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Create users table
    # Note: This migration only includes tables defined in current SQLAlchemy models.
    # Future migrations will add:
    # - PostgreSQL ENUM types (organization_type, vetting_status, rfq_status, etc.)
    # - organization_id and project_id foreign keys with ON DELETE CASCADE
    # - Additional tables per docs/03_database_schema.md and docs/02_architecture.md
    op.create_table(
        'users',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
        sa.Column(
            'email',
            postgresql.CITEXT(),
            nullable=False,
        ),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    # Create unique constraint on email
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    # Create index on email (for unique constraint and lookups)
    op.create_index('ix_users_email', 'users', ['email'])


def downgrade() -> None:
    # Drop table and constraints
    op.drop_index('ix_users_email', table_name='users')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_table('users')

    # Note: We do NOT drop extensions as they may be used by other databases/tables
    # If you need to drop them, do so manually:
    # op.execute("DROP EXTENSION IF EXISTS citext")
    # op.execute("DROP EXTENSION IF EXISTS pgcrypto")
