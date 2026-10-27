import logging
from logging.handlers import RotatingFileHandler
import sys
from .config import home, read_private, asset


def main():
    handler = RotatingFileHandler(home() / "application.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # Do not record HTTP bodies, passwords or SQL parameter values.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if "--server" in sys.argv:
        if sys.stdout is None:
            sys.stdout = open(home() / "server-console.log", "a", encoding="utf-8")
        if sys.stderr is None:
            sys.stderr = sys.stdout
        import uvicorn
        from .database import engine_for, migrate
        from .api import create_app

        config = read_private("connection.dat")
        if not config or config["mode"] == "remote":
            raise RuntimeError("Configura primero un servidor local desde el asistente.")
        engine = engine_for(config["database_url"])
        migrate(engine)
        uvicorn.run(
            create_app(engine, config["installation"], config["mode"] == "demo"),
            host=config.get("bind", "127.0.0.1"),
            port=config.get("port", 8765),
            access_log=False,
        )
        return
    from PySide6.QtWidgets import QApplication, QMessageBox
    from .setup import setup, ensure_server, login, ServerMismatch, saved_session_valid
    from .window import Window
    from .theme import apply_theme

    from .windows_identity import configure_taskbar_identity

    configure_taskbar_identity()
    app = QApplication(sys.argv)
    app.setApplicationName("Samtec Lockers")
    app.setOrganizationName("Samtec Lockers")
    apply_theme(app)
    from PySide6.QtGui import QIcon

    app.setWindowIcon(QIcon(str(asset("lockers.svg"))))
    if "--self-test" in sys.argv:
        from .smoke import run

        run(app)
        return
    try:
        config = read_private("connection.dat")
        if config is None or "--configure" in sys.argv:
            config = setup()
        if not config:
            return
        try:
            ensure_server(config)
        except ServerMismatch as exc:
            QMessageBox.critical(None, "Conexión", str(exc))
            return
        except ValueError as exc:
            QMessageBox.warning(None, "Servidor", str(exc))
        session = read_private("session.dat")
        if not saved_session_valid(config, session):
            session = None
        if session is None:
            session = login(config)
        if not session:
            return
        window = Window(config, session)
        window.show()
        sys.exit(app.exec())
    except Exception:
        logging.getLogger("slms").exception("Error al iniciar")
        QMessageBox.critical(
            None,
            "Samtec Lockers",
            "No se pudo iniciar. Revisa application.log en la carpeta de datos local. Si cambiaste de usuario de Windows, vuelve a configurar la conexión.",
        )


if __name__ == "__main__":
    main()
