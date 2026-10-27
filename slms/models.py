import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, JSON, LargeBinary, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Entity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Admin(Entity, Base):
    __tablename__ = "administrators"
    username: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="admin")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    __table_args__ = (Index("uq_initial_admin", "is_initial", unique=True,
                           sqlite_where=text("is_initial = true"), postgresql_where=text("is_initial = true")),)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_id: Mapped[str] = mapped_column(ForeignKey("administrators.id"))
    expires_at: Mapped[str] = mapped_column(String(40))


class Building(Entity, Base):
    __tablename__ = "buildings"
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(150))


class Plan(Entity, Base):
    __tablename__ = "plans"
    name: Mapped[str] = mapped_column(String(150))
    kind: Mapped[str] = mapped_column(String(20), default="exterior")
    floor: Mapped[str] = mapped_column(String(50), default="")
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    polygons: Mapped[list] = mapped_column(JSON, default=list)
    background: Mapped[str] = mapped_column(Text, default="")


class Block(Entity, Base):
    __tablename__ = "blocks"
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"))
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"))
    label: Mapped[str] = mapped_column(String(60))
    side: Mapped[str] = mapped_column(String(10), default="N")
    location: Mapped[str] = mapped_column(String(10), default="EXT")
    rows: Mapped[int] = mapped_column(Integer)
    columns: Mapped[int] = mapped_column(Integer)
    x: Mapped[float] = mapped_column(Float, default=500)
    y: Mapped[float] = mapped_column(Float, default=500)
    rotation: Mapped[float] = mapped_column(Float, default=0)
    deleted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    __table_args__ = (Index("uq_block_label", "building_id", "location", "label", unique=True),)


class Locker(Entity, Base):
    __tablename__ = "lockers"
    block_id: Mapped[str] = mapped_column(ForeignKey("blocks.id"))
    number: Mapped[str] = mapped_column(String(40), unique=True)
    row: Mapped[int] = mapped_column(Integer)
    # Zero-based physical position; row 0 is the top and column 0 is the right edge.
    column: Mapped[int] = mapped_column(Integer)
    condition: Mapped[str] = mapped_column(String(20), default="pendiente")
    # Physical condition to restore when the active padlock-cut request closes.
    condition_after_cut: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    has_padlock: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    deleted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    __table_args__ = (Index("uq_locker_cell", "block_id", "row", "column", unique=True),)


class Employee(Entity, Base):
    __tablename__ = "employees"
    employee_number: Mapped[str] = mapped_column(String(80), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    surname: Mapped[str] = mapped_column(String(100))
    second_surname: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(254), default="")
    department: Mapped[str] = mapped_column(String(120), default="")
    shift: Mapped[str] = mapped_column(String(80), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    extra: Mapped[dict] = mapped_column(JSON, default=dict)


class Assignment(Entity, Base):
    __tablename__ = "assignments"
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"))
    locker_id: Mapped[str] = mapped_column(ForeignKey("lockers.id"))
    started_at: Mapped[str] = mapped_column(String(40), default=now)
    ended_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    started_by: Mapped[str] = mapped_column(ForeignKey("administrators.id"))
    ended_by: Mapped[str | None] = mapped_column(ForeignKey("administrators.id"), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    end_reason: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (
        Index(
            "uq_current_employee",
            "employee_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index(
            "uq_current_locker",
            "locker_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
    )


class Receipt(Base):
    __tablename__ = "command_receipts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("administrators.id"))
    payload_hash: Mapped[str] = mapped_column(String(64))
    device_id: Mapped[str] = mapped_column(String(80))
    client_at: Mapped[str] = mapped_column(String(40))
    received_at: Mapped[str] = mapped_column(String(40), default=now)
    result: Mapped[dict] = mapped_column(JSON)


class InspectionRound(Entity, Base):
    __tablename__ = "inspection_rounds"
    title: Mapped[str] = mapped_column(String(150))
    locker_ids: Mapped[list] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(ForeignKey("administrators.id"))
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class InspectionEntry(Entity, Base):
    __tablename__ = "inspection_entries"
    round_id: Mapped[str] = mapped_column(ForeignKey("inspection_rounds.id"))
    locker_id: Mapped[str] = mapped_column(ForeignKey("lockers.id"))
    outcome: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(Text, default="")
    actor_id: Mapped[str] = mapped_column(ForeignKey("administrators.id"))
    at: Mapped[str] = mapped_column(String(40), default=now)
    observed_at: Mapped[str] = mapped_column(String(40))
    assignment_id: Mapped[str | None] = mapped_column(ForeignKey("assignments.id"), nullable=True)
    __table_args__ = (Index("uq_inspection_locker", "round_id", "locker_id", unique=True),)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    command_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("administrators.id"))
    at: Mapped[str] = mapped_column(String(40), default=now)
    action: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(36))
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")


class CutRequest(Entity, Base):
    __tablename__ = "cut_requests"
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"))
    locker_id: Mapped[str] = mapped_column(ForeignKey("lockers.id"))
    reference: Mapped[dict] = mapped_column(JSON)
    supervisor: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(30), default="otro")
    status: Mapped[str] = mapped_column(String(20), default="solicitada")
    assignee: Mapped[str] = mapped_column(String(200), default="")
    created_by: Mapped[str] = mapped_column(ForeignKey("administrators.id"))
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    assigned_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    performed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    completed_by: Mapped[str | None] = mapped_column(ForeignKey("administrators.id"), nullable=True)
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (Index("uq_open_cut_locker", "locker_id", unique=True,
                           sqlite_where=text("status IN ('solicitada', 'en_proceso')"),
                           postgresql_where=text("status IN ('solicitada', 'en_proceso')")),)


class CutEvidence(Entity, Base):
    __tablename__ = "cut_evidence"
    request_id: Mapped[str] = mapped_column(ForeignKey("cut_requests.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(240))
    media_type: Mapped[str] = mapped_column(String(30))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    current: Mapped[bool] = mapped_column(Boolean, default=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("administrators.id"))
    uploaded_at: Mapped[str] = mapped_column(String(40), default=now)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    command_id: Mapped[str] = mapped_column(String(36), unique=True)
    at: Mapped[str] = mapped_column(String(40), default=now)
    recipient: Mapped[str] = mapped_column(String(254))
    cc: Mapped[list] = mapped_column(JSON, default=list)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="simulado")


class MailSettings(Entity, Base):
    __tablename__ = "mail_settings"
    hr_email: Mapped[str] = mapped_column(String(254), default="")
    copy_hr_on_release: Mapped[bool] = mapped_column(Boolean, default=True)


def record(obj):
    return {col.name: getattr(obj, col.name) for col in obj.__table__.columns
            if col.name not in ("password_hash", "content")}
