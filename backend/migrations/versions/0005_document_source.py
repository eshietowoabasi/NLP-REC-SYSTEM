"""Document source, original link and publication date

Revision ID: 0005_document_source
Revises: 0004_nuc_courses
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_document_source"
down_revision = "0004_nuc_courses"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("source", sa.String(length=128), nullable=True))
    op.add_column("documents", sa.Column("source_url", sa.String(length=1024), nullable=True))
    op.add_column("documents", sa.Column("published_on", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("documents", "published_on")
    op.drop_column("documents", "source_url")
    op.drop_column("documents", "source")
