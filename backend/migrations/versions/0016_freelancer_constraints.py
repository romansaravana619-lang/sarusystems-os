"""Enforce Freelancer Management database invariants.

Revision ID: 0016_freelancer_constraints
Revises: 0015_freelancer_management
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_freelancer_constraints"
down_revision = "0015_freelancer_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_freelancer_company_email",
        "freelancers",
        ["company_id", "email"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_freelancer_company_email", "freelancers", type_="unique")
