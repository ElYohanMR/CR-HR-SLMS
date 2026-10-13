"""Record padlock presence without guessing the physical state of existing lockers."""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lockers", sa.Column("has_padlock", sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column("lockers", "has_padlock")
