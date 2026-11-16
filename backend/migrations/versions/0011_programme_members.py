"""Programme membership: which programmes each planner and viewer works on.

Admins see every programme and need no rows. Every existing planner and viewer is given the
default programme (the lowest-numbered active one, Computer Science), which is all they could
work on before programmes existed, so nobody loses access.

Revision ID: 0011_programme_members
Revises: 0010_document_programmes
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_programme_members"
down_revision = "0010_document_programmes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "programme_members",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("programme_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["programme_id"],
            ["programmes.id"],
            name=op.f("fk_programme_members_programme_id_programmes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_programme_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "programme_id", name=op.f("pk_programme_members")),
    )
    op.create_index(
        op.f("ix_programme_members_programme_id"), "programme_members", ["programme_id"]
    )
    op.create_index(op.f("ix_programme_members_user_id"), "programme_members", ["user_id"])
    op.execute(sa.text("""
        INSERT INTO programme_members (user_id, programme_id)
        SELECT u.id, (SELECT id FROM programmes WHERE is_active ORDER BY id LIMIT 1)
        FROM users AS u
        WHERE u.role <> 'admin'
          AND EXISTS (SELECT 1 FROM programmes WHERE is_active)
    """))


def downgrade():
    op.drop_index(op.f("ix_programme_members_user_id"), table_name="programme_members")
    op.drop_index(op.f("ix_programme_members_programme_id"), table_name="programme_members")
    op.drop_table("programme_members")
