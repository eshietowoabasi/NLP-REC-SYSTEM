"""Programmes and programme-aware analysis sessions

Revision ID: 0006_programmes
Revises: 0005_document_source
Create Date: 2026-10-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_programmes"
down_revision = "0005_document_source"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "programmes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("discipline_code", sa.String(length=32), nullable=True),
        sa.Column("faculty", sa.String(length=160), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("country", sa.String(length=80), server_default="Nigeria", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discipline_code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_programmes_is_active", "programmes", ["is_active"], unique=False)
    op.create_index("ix_programmes_name", "programmes", ["name"], unique=True)

    op.execute(sa.text("""
        INSERT INTO programmes
            (name, discipline_code, faculty, description, country, is_active)
        VALUES
            ('Computer Science', 'CSC', 'Faculty of Computing',
             'Default programme migrated from the original SkillBridge deployment.',
             'Nigeria', true)
    """))

    op.add_column("nuc_core_versions", sa.Column("programme_id", sa.Integer(), nullable=True))
    op.execute(sa.text("""
        UPDATE nuc_core_versions
        SET programme_id = (SELECT id FROM programmes WHERE name = 'Computer Science')
        WHERE programme_id IS NULL
    """))
    op.create_foreign_key(
        "fk_nuc_core_versions_programme_id_programmes",
        "nuc_core_versions",
        "programmes",
        ["programme_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_nuc_core_versions_programme_id",
        "nuc_core_versions",
        ["programme_id"],
        unique=False,
    )
    op.drop_index("uq_nuc_core_versions_single_active", table_name="nuc_core_versions")
    op.create_index(
        "uq_nuc_core_versions_programme_active",
        "nuc_core_versions",
        ["programme_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.add_column("analysis_sessions", sa.Column("programme_id", sa.Integer(), nullable=True))
    op.execute(sa.text("""
        UPDATE analysis_sessions
        SET programme_id = (SELECT id FROM programmes WHERE name = 'Computer Science')
        WHERE programme_id IS NULL
    """))
    op.create_foreign_key(
        "fk_analysis_sessions_programme_id_programmes",
        "analysis_sessions",
        "programmes",
        ["programme_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_analysis_sessions_programme_id", "analysis_sessions", ["programme_id"], unique=False)


def downgrade():
    op.drop_index("ix_analysis_sessions_programme_id", table_name="analysis_sessions")
    op.drop_constraint(
        "fk_analysis_sessions_programme_id_programmes",
        "analysis_sessions",
        type_="foreignkey",
    )
    op.drop_column("analysis_sessions", "programme_id")
    op.drop_index("ix_programmes_name", table_name="programmes")
    op.drop_index("ix_programmes_is_active", table_name="programmes")
    op.drop_table("programmes")

