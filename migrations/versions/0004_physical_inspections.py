"""Resumable physical inspections, independent of assignment history."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inspection_rounds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("locker_ids", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("administrators.id"), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("completed_at", sa.String(40), nullable=True),
    )
    op.create_table(
        "inspection_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.String(36), sa.ForeignKey("inspection_rounds.id"), nullable=False),
        sa.Column("locker_id", sa.String(36), sa.ForeignKey("lockers.id"), nullable=False),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("administrators.id"), nullable=False),
        sa.Column("at", sa.String(40), nullable=False),
        sa.Column("observed_at", sa.String(40), nullable=False),
        sa.Column("assignment_id", sa.String(36), sa.ForeignKey("assignments.id"), nullable=True),
    )
    op.create_index("uq_inspection_locker", "inspection_entries", ["round_id", "locker_id"], unique=True)


def downgrade():
    op.drop_table("inspection_entries")
    op.drop_table("inspection_rounds")
