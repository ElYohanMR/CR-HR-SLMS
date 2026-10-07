import json
import sqlite3
import uuid
import hashlib
from .config import home, protect
from .models import now


class LocalStore:
    def __init__(self, path=None, installation="default"):
        scope = hashlib.sha256(installation.encode()).hexdigest()[:16]
        self.path = path or home() / f"workstation-{scope}.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS queue (
                    id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, command BLOB NOT NULL,
                    status TEXT NOT NULL, message TEXT NOT NULL DEFAULT '',
                    attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
                    dependency TEXT, next_attempt REAL NOT NULL DEFAULT 0
                );
            """)
        if not self.get("device"):
            self.put("device", str(uuid.uuid4()))

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def encode(self, value):
        return protect(json.dumps(value, ensure_ascii=False).encode())

    def decode(self, value):
        return json.loads(protect(value, decrypt=True))

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return self.decode(row[0]) if row else None

    def put(self, key, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, self.encode(value)))

    def enqueue(self, actor_id, action, payload, versions, dependency=None):
        command = {
            "id": str(uuid.uuid4()),
            "device_id": self.get("device"),
            "client_at": now(),
            "action": action,
            "payload": payload,
            "versions": versions,
        }
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if action in ("block.delete", "locker.delete"):
                for existing in db.execute(
                    "SELECT id,command FROM queue WHERE actor_id=? AND status IN ('pendiente','requiere_sesion','error_temporal')",
                    (actor_id,),
                ):
                    old = self.decode(existing["command"])
                    if old["action"] == action and old["payload"].get("id") == payload.get("id"):
                        return existing["id"]
            db.execute(
                "INSERT INTO queue(id,actor_id,command,status,created_at,dependency) VALUES (?,?,?,?,?,?)",
                (command["id"], actor_id, self.encode(command), "pendiente", command["client_at"], dependency),
            )
        return command["id"]

    def require_session(self, actor_id):
        with self.connect() as db:
            db.execute(
                "UPDATE queue SET status='requiere_sesion', message=?, next_attempt=0 WHERE actor_id=? AND status IN ('pendiente','requiere_sesion')",
                ("Inicia sesión con la cuenta que creó esta solicitud para enviarla al servidor.", actor_id),
            )

    def queue(self, actor_id):
        with self.connect() as db:
            result = []
            for row in db.execute("SELECT * FROM queue WHERE actor_id=? ORDER BY created_at,id", (actor_id,)):
                item = dict(row)
                item["command"] = self.decode(item["command"])
                result.append(item)
            return result

    def result(self, id, status, message, attempt=False, next_attempt=0):
        with self.connect() as db:
            db.execute(
                "UPDATE queue SET status=?,message=?,attempts=attempts+?,next_attempt=? WHERE id=?",
                (status, message, int(attempt), next_attempt, id),
            )

    def retry(self, id, actor_id):
        with self.connect() as db:
            db.execute(
                "UPDATE queue SET status='pendiente',next_attempt=0,attempts=0 WHERE id=? AND actor_id=? AND status IN ('pendiente','error_temporal','requiere_sesion')",
                (id, actor_id),
            )
