"""Programme labour-market harvesting profiles and runs.

Revision ID: 0007_labour_market_harvester
Revises: 0006_programmes
"""

import sqlalchemy as sa
from alembic import op


revision = "0007_labour_market_harvester"
down_revision = "0006_programmes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "programmes",
        sa.Column(
            "job_search_terms",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )

    op.add_column(
        "programmes",
        sa.Column(
            "job_field_slugs",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "programme_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_documents_programme_id_programmes",
        "documents",
        "programmes",
        ["programme_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_documents_programme_id",
        "documents",
        ["programme_id"],
        unique=False,
    )

    op.create_table(
        "job_harvest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("programme_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="queued",
            nullable=False,
        ),
        sa.Column(
            "target_count",
            sa.Integer(),
            server_default="10",
            nullable=False,
        ),
        sa.Column(
            "pages_per_field",
            sa.Integer(),
            server_default="2",
            nullable=False,
        ),
        sa.Column(
            "examined_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "found_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "imported_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "skipped_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["programme_id"],
            ["programmes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_job_harvest_runs_programme_id",
        "job_harvest_runs",
        ["programme_id"],
        unique=False,
    )

    op.create_index(
        "ix_job_harvest_runs_requested_by_id",
        "job_harvest_runs",
        ["requested_by_id"],
        unique=False,
    )

    op.create_index(
        "ix_job_harvest_runs_status",
        "job_harvest_runs",
        ["status"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_job_harvest_runs_status",
        table_name="job_harvest_runs",
    )

    op.drop_index(
        "ix_job_harvest_runs_requested_by_id",
        table_name="job_harvest_runs",
    )

    op.drop_index(
        "ix_job_harvest_runs_programme_id",
        table_name="job_harvest_runs",
    )

    op.drop_table("job_harvest_runs")

    op.drop_index(
        "ix_documents_programme_id",
        table_name="documents",
    )

    op.drop_constraint(
        "fk_documents_programme_id_programmes",
        "documents",
        type_="foreignkey",
    )

    op.drop_column(
        "documents",
        "programme_id",
    )

    op.drop_column(
        "programmes",
        "job_field_slugs",
    )

    op.drop_column(
        "programmes",
        "job_search_terms",
    )
