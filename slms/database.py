import base64
import hashlib
import hmac
import secrets
import json
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config
from .config import asset
from .models import Admin, Building, Plan, Block, Locker, Employee


def password_hash(password):
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000)
    return salt + ":" + key.hex()


def password_matches(password, stored):
    salt, expected = stored.split(":")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000)
    return hmac.compare_digest(actual.hex(), expected)


def engine_for(url):
    opts = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        opts["connect_args"] = {"check_same_thread": False, "timeout": 30}
    else:
        opts["connect_args"] = {"connect_timeout": 5}
    engine = create_engine(url, **opts)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def sqlite_options(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")

    return engine


def migrate(engine):
    cfg = Config()
    cfg.set_main_option("script_location", str(asset("../migrations").resolve()))
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(731962402)"))
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")


def initialize(engine, username, password, demo=False):
    if len(password) < 10 or not username.strip():
        raise ValueError("Escribe un usuario y una contraseña de al menos 10 caracteres.")
    migrate(engine)
    with sessionmaker(engine).begin() as db:
        if engine.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(731962402)"))
        if db.scalar(select(Admin.id).limit(1)):
            return False
        db.add(
            Admin(
                username=username.strip().lower(),
                name="Administrador inicial",
                is_initial=True,
                password_hash=password_hash(password),
                role="admin",
            )
        )
        a = Building(id="building-1", code="E2", name="Edificio 2 · superior")
        b = Building(id="building-2", code="E1", name="Edificio 1 · inferior")
        db.add_all([a, b])
        db.flush()
        map_data = json.loads(asset("site-map.json").read_text(encoding="utf-8"))
        shapes = map_data["polygons"]
        image = asset("site-hd.jpg")
        plan = Plan(
            id="campus",
            name="Campus · exteriores",
            polygons=shapes,
            background=base64.b64encode(image.read_bytes()).decode() if image.exists() else "",
        )
        db.add(plan)
        db.flush()
        if demo:
            block = Block(
                id="demo-block",
                plan_id=plan.id,
                building_id=a.id,
                label="DEMO-S01",
                side="S",
                location="EXT",
                rows=4,
                columns=4,
                x=map_data["demo_position"][0],
                y=map_data["demo_position"][1],
            )
            db.add(block)
            db.flush()
            for i in range(16):
                db.add(
                    Locker(
                        block_id=block.id, number=f"DEMO-{i + 1:03}", row=i // 4, column=i % 4, condition="utilizable"
                    )
                )
            db.add(
                Employee(
                    employee_number="DEMO-001",
                    first_name="Persona",
                    surname="Ejemplo",
                    notes="Registro ficticio para demostración.",
                )
            )
    return True
