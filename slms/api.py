from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
import threading
import time
import uuid
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker
from .database import password_matches
from .models import (
    Admin,
    Session,
    Building,
    Plan,
    Block,
    Locker,
    Employee,
    Assignment,
    Audit,
    Notification,
    MailSettings,
    InspectionRound,
    InspectionEntry,
    now,
    record,
)
from .service import execute, RuleError
from . import __version__


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=500)


class Command(BaseModel):
    id: str
    device_id: str = Field(min_length=1, max_length=80)
    client_at: str = Field(max_length=40)
    action: str = Field(max_length=60)
    payload: dict
    versions: dict[str, int] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def valid_id(cls, value):
        return str(uuid.UUID(value))

    @field_validator("client_at")
    @classmethod
    def valid_time(cls, value):
        date = datetime.fromisoformat(value)
        if date.tzinfo is None:
            raise ValueError("Incluye la zona horaria de la solicitud.")
        return value


def create_app(engine, installation="test", demo=False):
    app = FastAPI(title="Samtec Lockers", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    sessions = sessionmaker(engine)
    attempts = defaultdict(deque)
    attempt_lock = threading.Lock()

    @app.middleware("http")
    async def limit_body(request: Request, call_next):
        from starlette.responses import JSONResponse

        try:
            if int(request.headers.get("content-length", "0")) > 9_000_000:
                return JSONResponse({"detail": "Solicitud demasiado grande."}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Longitud inválida."}, status_code=400)
        return await call_next(request)

    def actor(authorization):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Inicia sesión.")
        hashed = hashlib.sha256(authorization[7:].encode()).hexdigest()
        with sessions() as db:
            session = db.get(Session, hashed)
            if not session or session.expires_at < now():
                raise HTTPException(401, "La sesión venció. Inicia sesión para sincronizar.")
            admin = db.get(Admin, session.admin_id)
            if not admin or not admin.active:
                raise HTTPException(401, "La cuenta no está activa.")
            return record(admin)

    @app.get("/health")
    def health():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"app": "samtec-lockers", "version": __version__, "installation": installation, "demo": demo}

    @app.post("/login")
    def login(data: Login, request: Request):
        key = (request.client.host if request.client else "local", data.username.strip().lower())
        with attempt_lock:
            times = attempts[key]
            while times and times[0] < time.monotonic() - 60:
                times.popleft()
            if len(times) >= 10:
                raise HTTPException(429, "Demasiados intentos. Espera un minuto.")
            times.append(time.monotonic())
        with sessions.begin() as db:
            admin = db.scalar(select(Admin).where(Admin.username == key[1]))
            if not admin or not admin.active or not password_matches(data.password, admin.password_hash):
                raise HTTPException(401, "Usuario o contraseña incorrectos.")
            token = secrets.token_urlsafe(40)
            db.add(
                Session(
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    admin_id=admin.id,
                    expires_at=(datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
                )
            )
            return {"token": token, "actor": record(admin)}

    @app.get("/me")
    def me(authorization: str | None = Header(default=None)):
        return actor(authorization)

    @app.post("/logout")
    def logout(authorization: str | None = Header(default=None)):
        actor(authorization)
        with sessions.begin() as db:
            obj = db.get(Session, hashlib.sha256(authorization[7:].encode()).hexdigest())
            if obj:
                db.delete(obj)
        return {"ok": True}

    @app.get("/snapshot")
    def snapshot(authorization: str | None = Header(default=None)):
        actor(authorization)
        with sessions() as db:
            if engine.dialect.name == "postgresql":
                db.execute(text("SELECT pg_advisory_xact_lock(731962401)"))
            result = {"at": now(), "demo": demo, "features": {"inspections": True, "inventory_batch": True}}
            for name, model in (
                ("buildings", Building),
                ("plans", Plan),
                ("blocks", Block),
                ("lockers", Locker),
                ("employees", Employee),
                ("assignments", Assignment),
                ("admins", Admin),
                ("audit", Audit),
                ("notifications", Notification),
                ("mail_settings", MailSettings),
                ("inspection_rounds", InspectionRound),
                ("inspection_entries", InspectionEntry),
            ):
                query = select(model)
                if name in ("audit", "notifications"):
                    query = query.order_by(model.at.desc()).limit(2000)
                items = [record(item) for item in db.scalars(query)]
                if name in ("blocks", "lockers"):
                    result["archived_" + name] = [item for item in items if item.get("deleted_at")]
                    items = [item for item in items if not item.get("deleted_at")]
                result[name] = items
            return result

    @app.post("/commands")
    def commands(command: Command, authorization: str | None = Header(default=None)):
        identity = actor(authorization)
        try:
            return execute(engine, identity["id"], command.model_dump())
        except RuleError as exc:
            raise HTTPException(409, str(exc))
        except Exception:
            logging.getLogger("slms").exception("Falló una transacción, solicitud %s", command.id)
            raise HTTPException(500, "La operación no pudo completarse. Se conservará para reintentar.")

    @app.get("/audit")
    def audit(offset: int = 0, authorization: str | None = Header(default=None)):
        actor(authorization)
        with sessions() as db:
            return [
                record(x)
                for x in db.scalars(
                    select(Audit).order_by(Audit.at.desc(), Audit.id).offset(max(0, offset)).limit(1000)
                )
            ]

    @app.post("/backup")
    def backup(authorization: str | None = Header(default=None)):
        if actor(authorization)["role"] != "admin":
            raise HTTPException(403, "Se necesita una cuenta administradora.")
        from .backup import create_backup
        from fastapi.responses import FileResponse

        try:
            path = create_backup(engine)
            return FileResponse(path, filename=path.name, media_type="application/octet-stream")
        except Exception:
            raise HTTPException(
                500, "No se pudo crear la copia. Revisa la instalación de pg_dump y el espacio disponible."
            )

    return app
