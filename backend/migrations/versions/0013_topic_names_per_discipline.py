"""Course-style topic names per NUC discipline.

The ``topic_name_catalogue`` setting (one list, computing names) becomes
``topic_name_catalogues``: one list per NUC discipline. A stored list, possibly edited by an
admin, becomes the computing list; the other disciplines take their defaults (the setting keeps
a default for every discipline that is not stored). Data only, no schema change.

Revision ID: 0013_topic_names_per_discipline
Revises: 0012_discipline_skills
"""

import sqlalchemy as sa
from alembic import op

revision = "0013_topic_names_per_discipline"
down_revision = "0012_discipline_skills"
branch_labels = None
depends_on = None

settings = sa.table(
    "settings",
    sa.column("key", sa.String),
    sa.column("value", sa.JSON),
)


def _value(connection, key: str):
    return connection.execute(sa.select(settings.c.value).where(settings.c.key == key)).scalar()


def upgrade() -> None:
    connection = op.get_bind()
    old = _value(connection, "topic_name_catalogue")
    if old is not None and _value(connection, "topic_name_catalogues") is None:
        connection.execute(
            settings.insert().values(key="topic_name_catalogues", value={"computing": old})
        )
    connection.execute(settings.delete().where(settings.c.key == "topic_name_catalogue"))


def downgrade() -> None:
    connection = op.get_bind()
    new = _value(connection, "topic_name_catalogues")
    if new is not None and new.get("computing") is not None:
        connection.execute(
            settings.insert().values(key="topic_name_catalogue", value=new["computing"])
        )
    connection.execute(settings.delete().where(settings.c.key == "topic_name_catalogues"))
