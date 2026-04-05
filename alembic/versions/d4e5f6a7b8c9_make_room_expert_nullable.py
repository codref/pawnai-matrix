"""Make room expert_id nullable

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-04-05 20:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE room SET expert_id = NULL WHERE expert_id = -1"))
    op.alter_column('room', 'expert_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM room WHERE expert_id IS NULL"))
    op.alter_column('room', 'expert_id', existing_type=sa.Integer(), nullable=False)
