"""Skills lists per NUC discipline.

* ``programmes.nuc_discipline``: one of the 17 NUC CCMAS disciplines. Programmes whose name is
  a computing one (Computer Science, Software Engineering, Cybersecurity, Information
  Technology, Data Science) become ``computing``; admins set the others on the Programmes
  page.
* ``skill_patterns.discipline``: the discipline whose programmes use the pattern, or NULL for a
  general skill every programme uses. All patterns seeded so far were computing ones, except
  the general workplace skills listed below, which become general. New discipline lists are
  added by ``flask seed``.
* The unique key becomes (label, pattern, discipline), NULLs not distinct, so a phrase such as
  "AutoCAD" can belong to several disciplines.

Revision ID: 0012_discipline_skills
Revises: 0011_programme_members
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_discipline_skills"
down_revision = "0011_programme_members"
branch_labels = None
depends_on = None

DISCIPLINES = (
    "administration_and_management",
    "agriculture",
    "allied_health_sciences",
    "architecture",
    "arts",
    "basic_medical_sciences",
    "communication_and_media_studies",
    "computing",
    "education",
    "engineering_and_technology",
    "environmental_sciences",
    "law",
    "medicine_and_dentistry",
    "pharmaceutical_science",
    "sciences",
    "social_sciences",
    "veterinary_medicine",
)
GENERAL_SKILLS = (
    "Microsoft Excel",
    "Data Analysis",
    "Statistics",
    "Project Management",
    "Risk Management",
    "Data Protection Compliance",
    "PMP",
    "PRINCE2",
)


def _discipline_type(name: str) -> sa.Enum:
    return sa.Enum(*DISCIPLINES, name=name, native_enum=False, create_constraint=True, length=32)


def upgrade():
    with op.batch_alter_table("programmes") as batch_op:
        batch_op.add_column(
            sa.Column("nuc_discipline", _discipline_type("nuc_discipline"), nullable=True)
        )
    with op.batch_alter_table("skill_patterns") as batch_op:
        batch_op.add_column(sa.Column("discipline", _discipline_type("discipline"), nullable=True))
        batch_op.drop_constraint("uq_skill_patterns_label_pattern", type_="unique")
        batch_op.create_index("ix_skill_patterns_discipline", ["discipline"], unique=False)

    op.execute(sa.text("""
        UPDATE programmes SET nuc_discipline = 'computing'
        WHERE name ~* '(computer|software|cyber|information tech|data science)'
    """))
    op.execute(sa.text("UPDATE skill_patterns SET discipline = 'computing'"))
    op.execute(
        sa.text("UPDATE skill_patterns SET discipline = NULL WHERE canonical_name IN :names")
        .bindparams(sa.bindparam("names", expanding=True))
        .params(names=list(GENERAL_SKILLS))
    )

    with op.batch_alter_table("skill_patterns") as batch_op:
        batch_op.create_unique_constraint(
            "uq_skill_patterns_label_pattern_discipline",
            ["label", "pattern", "discipline"],
            postgresql_nulls_not_distinct=True,
        )


def downgrade():
    # Rows that only differ by discipline cannot survive the old unique key.
    op.execute(sa.text("""
        DELETE FROM skill_patterns AS s
        USING skill_patterns AS t
        WHERE s.label = t.label AND s.pattern = t.pattern AND s.id > t.id
    """))
    with op.batch_alter_table("skill_patterns") as batch_op:
        batch_op.drop_constraint("uq_skill_patterns_label_pattern_discipline", type_="unique")
        batch_op.drop_index("ix_skill_patterns_discipline")
        batch_op.create_unique_constraint("uq_skill_patterns_label_pattern", ["label", "pattern"])
        batch_op.drop_column("discipline")
    with op.batch_alter_table("programmes") as batch_op:
        batch_op.drop_column("nuc_discipline")
