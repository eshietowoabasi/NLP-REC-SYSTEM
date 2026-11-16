"""Give existing documents a programme.

Until programmes existed every document was a Computer Science document, and hand uploads were
still saved without a programme afterwards. Sessions now refuse documents of another programme
and treat documents without one as general (usable by every programme), so:

* NUC core documents get the programme of their benchmark version;
* every other document without a programme is assigned to the default programme (the
  lowest-numbered active one, Computer Science), which is what it was uploaded for.

Planners can later make a document general, or move it, on the document's page.

Revision ID: 0010_document_programmes
Revises: 0009_harvest_run_tracking
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_document_programmes"
down_revision = "0009_harvest_run_tracking"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        UPDATE documents AS d
        SET programme_id = v.programme_id
        FROM nuc_core_versions AS v
        WHERE v.document_id = d.id AND d.programme_id IS NULL
    """))
    op.execute(sa.text("""
        UPDATE documents
        SET programme_id = (SELECT id FROM programmes WHERE is_active ORDER BY id LIMIT 1)
        WHERE programme_id IS NULL
    """))


def downgrade():
    # Data-only migration: which documents were untagged before cannot be recovered.
    pass
