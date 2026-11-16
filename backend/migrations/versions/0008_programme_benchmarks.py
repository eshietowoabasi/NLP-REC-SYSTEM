"""Every curriculum benchmark (NUC core version) belongs to a programme.

Versions uploaded through the original NUC core screen after migration 0006 were saved without a
programme, so sessions (which look up the active benchmark of their programme) could not find
them. This assigns those versions to the default programme, the lowest-numbered active one
(Computer Science after 0006), and makes the column required.

It also drops ``uq_programmes_name``: 0006 created both that constraint and the unique index
``ix_programmes_name`` the model declares, so programme names were checked twice.

Revision ID: 0008_programme_benchmarks
Revises: 0007_labour_market_harvester
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_programme_benchmarks"
down_revision = "0007_labour_market_harvester"
branch_labels = None
depends_on = None


def upgrade():
    # Keep at most one active version for the default programme: if an orphaned version is
    # active, it is the newer upload, so it replaces the programme's current active version.
    op.execute(sa.text("""
        WITH default_programme AS (
            SELECT id FROM programmes WHERE is_active ORDER BY id LIMIT 1
        )
        UPDATE nuc_core_versions
        SET is_active = false
        WHERE is_active
          AND programme_id = (SELECT id FROM default_programme)
          AND EXISTS (
              SELECT 1 FROM nuc_core_versions o WHERE o.programme_id IS NULL AND o.is_active
          )
    """))
    # If several orphaned versions are active, keep only the newest.
    op.execute(sa.text("""
        UPDATE nuc_core_versions
        SET is_active = false
        WHERE programme_id IS NULL AND is_active AND id <> (
            SELECT max(id) FROM nuc_core_versions WHERE programme_id IS NULL AND is_active
        )
    """))
    op.execute(sa.text("""
        UPDATE nuc_core_versions
        SET programme_id = (SELECT id FROM programmes WHERE is_active ORDER BY id LIMIT 1)
        WHERE programme_id IS NULL
    """))
    op.alter_column("nuc_core_versions", "programme_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("uq_programmes_name", "programmes", type_="unique")


def downgrade():
    op.create_unique_constraint("uq_programmes_name", "programmes", ["name"])
    op.alter_column("nuc_core_versions", "programme_id", existing_type=sa.Integer(), nullable=True)
