"""add_citext_extension_and_update_email_column

Revision ID: 2bedffc89aee
Revises: 4e29a978773d
Create Date: 2026-02-12 20:13:25.797412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2bedffc89aee'
down_revision: Union[str, None] = '4e29a978773d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure citext extension exists (idempotent - safe to run multiple times)
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    
    # Alter email column to CITEXT if it's not already CITEXT
    # This handles the case where the database was created with String(255)
    # before this migration was applied. The initial migration already uses CITEXT,
    # so this is mainly for databases that were created before the model was updated.
    op.execute("""
        DO $$
        BEGIN
            -- Check if column exists and is not already citext
            IF EXISTS (
                SELECT 1 
                FROM information_schema.columns c
                JOIN pg_type t ON t.typname = c.udt_name
                WHERE c.table_name = 'users' 
                AND c.column_name = 'email'
                AND t.typname != 'citext'
            ) THEN
                ALTER TABLE users ALTER COLUMN email TYPE citext USING email::citext;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Convert CITEXT back to VARCHAR(255) to match String(255) type
    op.execute("ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(255) USING email::VARCHAR(255)")
    
    # Note: We do NOT drop the citext extension as it may be used by other tables
    # If you need to drop it, do so manually:
    # op.execute("DROP EXTENSION IF EXISTS citext")
