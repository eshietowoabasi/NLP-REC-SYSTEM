"""Track which collection imported an advert, and the RQ job of each collection.

``documents.harvest_run_id`` lets a collection report how many of its adverts are ready to
analyse. ``job_harvest_runs.rq_job_id`` lets the API notice a collection whose background job
died, so it no longer blocks new collections for that programme.

Revision ID: 0009_harvest_run_tracking
Revises: 0008_programme_benchmarks
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_harvest_run_tracking"
down_revision = "0008_programme_benchmarks"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("job_harvest_runs", sa.Column("rq_job_id", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("harvest_run_id", sa.Integer(), nullable=True))
    op.create_index("ix_documents_harvest_run_id", "documents", ["harvest_run_id"])
    op.create_foreign_key(
        "fk_documents_harvest_run_id_job_harvest_runs",
        "documents",
        "job_harvest_runs",
        ["harvest_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "fk_documents_harvest_run_id_job_harvest_runs", "documents", type_="foreignkey"
    )
    op.drop_index("ix_documents_harvest_run_id", table_name="documents")
    op.drop_column("documents", "harvest_run_id")
    op.drop_column("job_harvest_runs", "rq_job_id")
