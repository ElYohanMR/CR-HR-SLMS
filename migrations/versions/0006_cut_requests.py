"""Padlock cutting requests and original photographic evidence."""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cut_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("locker_id", sa.String(36), sa.ForeignKey("lockers.id"), nullable=False),
        sa.Column("reference", sa.JSON(), nullable=False),
        sa.Column("supervisor", sa.String(200), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("assignee", sa.String(200), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("administrators.id"), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("assigned_at", sa.String(40), nullable=True),
        sa.Column("performed_at", sa.String(40), nullable=True),
        sa.Column("completed_at", sa.String(40), nullable=True),
        sa.Column("completed_by", sa.String(36), sa.ForeignKey("administrators.id"), nullable=True),
        sa.Column("identity_verified", sa.Boolean(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
    )
    op.create_index("uq_open_cut_locker", "cut_requests", ["locker_id"], unique=True,
                    sqlite_where=sa.text("status IN ('solicitada', 'en_proceso')"),
                    postgresql_where=sa.text("status IN ('solicitada', 'en_proceso')"))
    op.create_table(
        "cut_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("cut_requests.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("filename", sa.String(240), nullable=False),
        sa.Column("media_type", sa.String(30), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("administrators.id"), nullable=False),
        sa.Column("uploaded_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_cut_evidence_request_id", "cut_evidence", ["request_id"])


def downgrade():
    op.drop_table("cut_evidence")
    op.drop_table("cut_requests")
