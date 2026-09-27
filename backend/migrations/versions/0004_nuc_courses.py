"""NUC core courses and course-level overlap

Adds ``nuc_courses`` (one row per course of the NUC core, with its own embedding) and
``recommendations.closest_nuc_course_id``.

Revision ID: 0004_nuc_courses
Revises: 0003_session_stage_timings
Create Date: 2026-09-27
"""

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision = "0004_nuc_courses"
down_revision = "0003_session_stage_timings"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nuc_courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("units", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_nuc_courses_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nuc_courses")),
        sa.UniqueConstraint("document_id", "code", name=op.f("uq_nuc_courses_document_id_code")),
    )
    op.create_index(op.f("ix_nuc_courses_document_id"), "nuc_courses", ["document_id"])
    op.add_column(
        "recommendations", sa.Column("closest_nuc_course_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_recommendations_closest_nuc_course_id_nuc_courses"),
        "recommendations",
        "nuc_courses",
        ["closest_nuc_course_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        op.f("fk_recommendations_closest_nuc_course_id_nuc_courses"),
        "recommendations",
        type_="foreignkey",
    )
    op.drop_column("recommendations", "closest_nuc_course_id")
    op.drop_index(op.f("ix_nuc_courses_document_id"), table_name="nuc_courses")
    op.drop_table("nuc_courses")
