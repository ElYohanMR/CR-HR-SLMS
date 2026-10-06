"""HR notification routing; existing notifications retain their original recipients."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notifications", sa.Column("cc", sa.JSON(), nullable=False, server_default="[]"))
    settings = op.create_table(
        "mail_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("hr_email", sa.String(254), nullable=False),
        sa.Column("copy_hr_on_release", sa.Boolean(), nullable=False),
    )
    op.bulk_insert(settings, [{"id": "mail", "version": 1, "hr_email": "", "copy_hr_on_release": True}])


def downgrade():
    op.drop_table("mail_settings")
    op.drop_column("notifications", "cc")
