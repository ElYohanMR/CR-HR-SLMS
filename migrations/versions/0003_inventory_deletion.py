"""Hide removed inventory while preserving assignment history and physical identity."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("blocks", sa.Column("deleted_at", sa.String(40), nullable=True))
    op.add_column("lockers", sa.Column("deleted_at", sa.String(40), nullable=True))


def downgrade():
    op.drop_column("lockers", "deleted_at")
    op.drop_column("blocks", "deleted_at")
