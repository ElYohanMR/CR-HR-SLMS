import time
import uuid
import subprocess
import sys
from urllib.parse import urlparse
import httpx
from sqlalchemy import URL
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication
from .config import home, save_private, read_private
from .database import engine_for, initialize
from .forms import Form


def setup_form(parent=None):
    form = Form(
        "Bienvenido a Samtec Lockers",
        [
            (
                "mode",
                "Tipo de conexión",
                [
                    ("Servidor local · PostgreSQL", "postgres"),
                    ("Conectar a servidor de TI", "remote"),
                    ("Demostración · datos ficticios", "demo"),
                ],
            ),
            ("connection_section", "CONEXIÓN A POSTGRESQL", "section"),
            ("host", "Servidor", "line"),
            ("port", "Puerto", "line"),
            ("database", "Base de datos", "line"),
            ("db_user", "Usuario de la base de datos", "line"),
            ("db_password", "Contraseña de la base de datos", "password"),
            ("url", "Dirección del servidor de TI", "line"),
            ("account_section", "CUENTA ADMINISTRADORA INICIAL", "section"),
            ("username", "Nombre de usuario", "line"),
            ("password", "Contraseña de la aplicación", "password"),
        ],
        {
            "host": "127.0.0.1",
            "port": "5432",
            "database": "samtec_lockers_dev",
            "db_user": "slms_dev",
            "url": "https://lockers.example.internal",
            "username": "admin",
        },
        parent,
        "Conecta la base de datos y crea tu cuenta para administrar los casilleros. Usa una contraseña propia para la aplicación, de al menos 10 caracteres. Las credenciales se guardan cifradas en esta computadora.",
    )
    form.setMinimumWidth(740)
    form.widgets["db_password"].setPlaceholderText("La contraseña que creaste en pgAdmin")
    form.widgets["password"].setPlaceholderText("Nueva contraseña · mínimo 10 caracteres")
    form.widgets["db_password"].setAccessibleDescription(
        "Contraseña del usuario de PostgreSQL, independiente de la cuenta de Samtec Lockers"
    )
    form.widgets["password"].setAccessibleDescription(
        "Contraseña nueva para la cuenta administradora de Samtec Lockers, mínimo 10 caracteres"
    )
    from PySide6.QtWidgets import QDialogButtonBox

    form.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).setText("Configurar y continuar")

    def mode_changed():
        mode = form.widgets["mode"].currentData()
        form.form_layout.setRowVisible(form.sections["connection_section"], mode == "postgres")
        form.form_layout.setRowVisible(form.sections["account_section"], mode != "remote")
        for name in ("host", "port", "database", "db_user", "db_password"):
            form.form_layout.setRowVisible(form.widgets[name], mode == "postgres")
        form.form_layout.setRowVisible(form.widgets["url"], mode == "remote")
        for name in ("username", "password"):
            form.form_layout.setRowVisible(form.widgets[name], mode != "remote")
        form.resize(form.sizeHint().width(), min(form.sizeHint().height(), form.maximumHeight()))

    form.widgets["mode"].currentIndexChanged.connect(mode_changed)
    mode_changed()
    return form


def setup(parent=None):
    form = setup_form(parent)
    while form.exec() == QDialog.DialogCode.Accepted:
        data = form.values()
        try:
            if data["mode"] == "remote":
                url = data["url"].rstrip("/")
                parsed = urlparse(url)
                if (
                    parsed.username
                    or parsed.password
                    or parsed.query
                    or parsed.fragment
                    or (
                        parsed.scheme != "https"
                        and not (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost"))
                    )
                ):
                    raise ValueError("El servidor de TI debe usar HTTPS y no incluir credenciales en la dirección.")
                result = httpx.get(url + "/health", timeout=5, trust_env=False)
                result.raise_for_status()
                if result.json().get("app") != "samtec-lockers":
                    raise ValueError("La dirección no corresponde a Samtec Lockers.")
                config = {"mode": "remote", "url": url, "installation": result.json()["installation"]}
            else:
                if data["mode"] == "postgres":
                    url = URL.create(
                        "postgresql+psycopg",
                        username=data["db_user"],
                        password=data["db_password"],
                        host=data["host"],
                        port=int(data["port"]),
                        database=data["database"],
                    ).render_as_string(hide_password=False)
                else:
                    url = "sqlite:///" + (home() / "demo-server.sqlite3").as_posix()
                QApplication.setOverrideCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.WaitCursor)
                try:
                    engine = engine_for(url)
                    created = initialize(engine, data["username"], data["password"], data["mode"] == "demo")
                    engine.dispose()
                finally:
                    QApplication.restoreOverrideCursor()
                previous = read_private("connection.dat") or {}
                config = {
                    "mode": data["mode"],
                    "database_url": url,
                    "url": "http://127.0.0.1:8765",
                    "installation": previous["installation"]
                    if previous.get("database_url") == url
                    else str(uuid.uuid4()),
                    "bind": "127.0.0.1",
                    "port": 8765,
                }
                if not created:
                    QMessageBox.information(
                        form,
                        "Base existente",
                        "Se conserva la información existente. Inicia sesión con una cuenta ya registrada; la contraseña indicada aquí no la reemplaza.",
                    )
            save_private("connection.dat", config)
            return config
        except Exception as exc:
            message = (
                str(exc)
                if isinstance(exc, ValueError)
                else "No se pudo conectar o preparar la base. Verifica host, puerto, nombre, usuario y contraseña; revisa que el usuario sea propietario de la base."
            )
            QMessageBox.warning(form, "Configuración pendiente", message)
    return None


def ensure_server(config):
    try:
        result = httpx.get(config["url"] + "/health", timeout=2, trust_env=False)
        result.raise_for_status()
        if result.json().get("installation") != config["installation"]:
            raise ServerMismatch(
                "El puerto está ocupado por otra instalación de Samtec Lockers. Cierra el servicio anterior antes de cambiar de base."
            )
        return
    except httpx.HTTPError:
        if config["mode"] == "remote":
            return
    log = open(home() / "server.log", "a", encoding="utf-8")
    command = (
        [sys.executable, "--server"] if getattr(sys, "frozen", False) else [sys.executable, "-m", "slms", "--server"]
    )
    process = subprocess.Popen(
        command,
        stdout=log,
        stderr=log,
        cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    log.close()
    for _ in range(50):
        QApplication.processEvents()
        time.sleep(0.1)
        try:
            result = httpx.get(config["url"] + "/health", timeout=0.5, trust_env=False)
            if result.status_code == 200 and result.json().get("installation") == config["installation"]:
                return
        except httpx.HTTPError:
            pass
        if process.poll() is not None:
            break
    raise ValueError("El servicio local no inició. Revisa PostgreSQL y el archivo server.log de la carpeta de datos.")


def saved_session_valid(config, session):
    if not session or session.get("installation") != config["installation"]:
        return False
    try:
        response = httpx.get(
            config["url"] + "/me", headers={"Authorization": "Bearer " + session["token"]}, timeout=3, trust_env=False
        )
        return response.status_code not in (401, 403)
    except httpx.HTTPError:
        # Offline work may still be queued; only the server can confirm it.
        return True


def login(config, parent=None):
    form = Form(
        "Iniciar sesión",
        [("username", "Usuario", "line"), ("password", "Contraseña", "password")],
        parent=parent,
        description="Utiliza tu cuenta individual de Samtec Lockers.",
        accept_label="Entrar",
    )
    form.widgets["password"].returnPressed.connect(form.accept)
    while form.exec() == QDialog.DialogCode.Accepted:
        try:
            response = httpx.post(config["url"] + "/login", json=form.values(), timeout=8, trust_env=False)
            if response.status_code != 200:
                raise ValueError(str(response.json().get("detail", "No se pudo iniciar sesión.")))
            session = response.json()
            session["installation"] = config["installation"]
            save_private("session.dat", session)
            return session
        except (httpx.HTTPError, ValueError) as exc:
            QMessageBox.warning(
                form,
                "Inicio de sesión",
                str(exc) if isinstance(exc, ValueError) else "No se pudo conectar al servidor.",
            )
    return None


class ServerMismatch(ValueError):
    pass
