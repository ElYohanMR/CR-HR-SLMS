"""Persist the initial administrator identity, independently of name or role."""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("administrators", sa.Column("is_initial", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Normal accounts are created through audited commands; bootstrap is not.
    # Ambiguous legacy databases receive no privilege automatically.
    connection = op.get_bind()
    candidates = (
        connection.execute(
            sa.text(
                "SELECT id FROM administrators WHERE id NOT IN "
                "(SELECT target_id FROM audit_events WHERE action = 'admin.create')"
            )
        )
        .scalars()
        .all()
    )
    if len(candidates) == 1:
        connection.execute(sa.text("UPDATE administrators SET is_initial = true WHERE id = :id"), {"id": candidates[0]})
    op.create_index(
        "uq_initial_admin",
        "administrators",
        ["is_initial"],
        unique=True,
        sqlite_where=sa.text("is_initial = true"),
        postgresql_where=sa.text("is_initial = true"),
    )


def downgrade():
    op.drop_index("uq_initial_admin", table_name="administrators")
    op.drop_column("administrators", "is_initial")
