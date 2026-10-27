"""Hold lockers in maintenance for both new and existing open cut requests."""
from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lockers", sa.Column("condition_after_cut", sa.String(20), nullable=True))
    connection = op.get_bind()
    metadata = sa.MetaData()
    lockers = sa.Table("lockers", metadata, autoload_with=connection)
    cuts = sa.Table("cut_requests", metadata, autoload_with=connection)
    audit = sa.Table("audit_events", metadata, autoload_with=connection)
    active = connection.execute(sa.select(cuts.c.id, cuts.c.locker_id, cuts.c.created_by)
                                .where(cuts.c.status.in_(("solicitada", "en_proceso")))).mappings().all()
    for cut in active:
        before = dict(connection.execute(sa.select(lockers).where(lockers.c.id == cut["locker_id"])).mappings().one())
        changes = {"condition_after_cut": before["condition"], "condition": "mantenimiento",
                   "version": before["version"] + 1}
        connection.execute(lockers.update().where(lockers.c.id == cut["locker_id"]).values(**changes))
        connection.execute(audit.insert().values(
            id=str(uuid.uuid4()), command_id=str(uuid.uuid4()), actor_id=cut["created_by"],
            at=datetime.now(timezone.utc).isoformat(), action="locker.cut_maintenance",
            target_id=cut["locker_id"], before=before, after=before | changes,
            reason=f"Actualización del sistema: mantenimiento por solicitud de corte abierta {cut['id']}."))


def downgrade():
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE lockers SET condition = condition_after_cut, version = version + 1 "
                               "WHERE condition_after_cut IS NOT NULL"))
    op.drop_column("lockers", "condition_after_cut")
