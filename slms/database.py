import base64
import hashlib
import hmac
import secrets
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
                password_hash=password_hash(password),
                role="admin",
            )
        )
        a = Building(id="building-1", code="E1", name="Edificio 1 · superior (por confirmar)")
        b = Building(id="building-2", code="E2", name="Edificio 2 · inferior (por confirmar)")
        db.add_all([a, b])
        db.flush()
        shapes = [
            {"building_id": a.id, "points": [[326, 250], [652, 315], [623, 454], [297, 383]]},
            {
                "building_id": b.id,
                "points": [
                    [327, 406],
                    [637, 476],
                    [627, 528],
                    [771, 555],
                    [700, 899],
                    [494, 852],
                    [514, 766],
                    [453, 752],
                    [444, 794],
                    [318, 764],
                    [310, 791],
                    [222, 769],
                    [238, 681],
                    [274, 688],
                    [291, 595],
                    [345, 607],
                    [370, 493],
                    [312, 486],
                ],
            },
        ]
        image = asset("site.png")
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
                x=460,
                y=438,
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
