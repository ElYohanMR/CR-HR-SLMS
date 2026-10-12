import base64
import copy
import csv
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QStackedWidget,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QHeaderView,
    QAbstractItemView,
    QDialog,
    QGridLayout,
    QFileDialog,
    QMessageBox,
    QMenu,
    QScrollArea,
)
from .forms import Form, info, confirm
from .local import LocalStore
from .sync import SyncWorker
from .mapview import MapView
from .setup import login
from .theme import STYLE, brand_header
from .tableview import enable_sorting, fill_table
from .contextmenus import ContextMenus
from .workflows import Workflows
from .inventory_selection import InventorySelection
from .preferences import Preferences
from .cut_ui import CutWorkflows


STATES = {
    "pendiente": "Pendiente de verificar",
    "utilizable": "Disponible",
    "mantenimiento": "Mantenimiento",
    "retirado": "Retirado",
    "ocupado": "Asignado",
}
ACTIONS = {
    "cut.create": "Crear solicitud de corte",
    "cut.update": "Editar solicitud de corte",
    "cut.assign": "Asignar encargado del corte",
    "cut.evidence": "Adjuntar evidencia de corte",
    "cut.photo": "Fotografía de evidencia",
    "cut.complete": "Finalizar corte de candado",
    "cut.cancel": "Cancelar solicitud de corte",
    "inventory.restore_many": "Restaurar elementos marcados",
    "inventory.purge": "Eliminar definitivamente inventario",
    "block.purge": "Bloque eliminado definitivamente",
    "locker.purge": "Casillero eliminado definitivamente",
    "inspection.create": "Iniciar revisión física",
    "inspection.record": "Registrar revisión física",
    "inspection.complete": "Cerrar revisión física",
    "locker.inspected": "Casillero revisado",
    "employee.create": "Alta de empleado",
    "employee.update": "Actualizar empleado",
    "employee.deactivate": "Dar de baja y liberar",
    "mail_settings.update": "Configurar avisos a HR",
    "assignment.assign": "Asignar casillero",
    "assignment.transfer": "Reasignar casillero",
    "assignment.release": "Liberar casillero",
    "locker.update": "Actualizar casillero",
    "block.create": "Crear bloque",
    "block.update": "Mover / actualizar bloque",
    "block.delete": "Eliminar bloque",
    "locker.delete": "Eliminar casillero",
    "block.restore": "Restaurar bloque",
    "locker.restore": "Restaurar casillero",
    "inventory.import": "Importar inventario de bloques",
    "plan.create": "Crear plano",
    "plan.update": "Actualizar plano",
    "building.create": "Crear edificio",
    "building.update": "Actualizar edificio",
    "admin.create": "Crear cuenta",
    "admin.update": "Actualizar cuenta",
}


def local_date(value):
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).astimezone(ZoneInfo("America/Costa_Rica")).strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return value


def full_name(e):
    return " ".join(filter(None, [e.get("first_name"), e.get("surname"), e.get("second_surname")]))


def csv_safe(value):
    text = str(value if value is not None else "")
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


class Window(CutWorkflows, Preferences, InventorySelection, Workflows, ContextMenus, QMainWindow):
    def __init__(self, config, session, store=None):
        super().__init__()
        self.config, self.session = config, session
        self.store = store or LocalStore(installation=config.get("installation", "default"))
        self.load_preferences()
        self.data = self.store.get("snapshot") or {
            key: []
            for key in (
                "employees",
                "lockers",
                "assignments",
                "blocks",
                "plans",
                "buildings",
                "admins",
                "audit",
                "notifications",
                "mail_settings",
            )
        }
        self.worker = None
        self.connection_state = "inicial"
        self.setWindowTitle("Samtec Lockers · Gestión de casilleros")
        self.resize(1450, 900)
        self.setMinimumSize(1080, 720)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.interface_scroll = QScrollArea()
        self.interface_scroll.setWidgetResizable(True)
        self.interface_scroll.setWidget(root)
        self.setCentralWidget(self.interface_scroll)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        header, top = brand_header(root)
        self.identity = QLabel()
        top.addWidget(self.identity)
        self.button(top, "Iniciar sesión", self.relogin)
        self.button(top, "Salir de la cuenta", self.logout)
        self.options_button = QPushButton("Opciones")
        self.options_menu = QMenu(self.options_button)
        self.options_button.clicked.connect(self.settings_dialog)
        shortcuts_button = QPushButton("Acciones")
        shortcuts_button.setMenu(self.options_menu)
        self.options_menu.aboutToShow.connect(self.populate_options)
        top.addWidget(self.options_button)
        top.addWidget(shortcuts_button)
        outer.addWidget(header)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 16)
        content_layout.setSpacing(20)
        outer.addWidget(content, 1)
        self.banner = QLabel("Conectando al servidor…")
        self.banner.setWordWrap(True)
        self.banner.setObjectName("banner")
        content_layout.addWidget(self.banner)
        self.session_button = QPushButton("Iniciar sesión para enviar solicitudes pendientes")
        self.session_button.clicked.connect(self.relogin)
        self.session_button.setProperty("primary", True)
        self.session_button.hide()
        content_layout.addWidget(self.session_button)
        body = QHBoxLayout()
        content_layout.addLayout(body, 1)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(205)
        self.nav.addItems(
            ["Resumen", "Mapa de casilleros", "Empleados", "Inventario", "Solicitudes", "Historial", "Administración", "Cortes de candado"]
        )
        self.stack = QStackedWidget()
        body.addWidget(self.nav)
        body.addWidget(self.stack, 1)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.make_dashboard()
        self.make_map()
        self.make_employees()
        self.make_inventory()
        self.make_queue()
        self.make_history()
        self.make_admin()
        self.make_cuts()
        self.nav.setCurrentRow(0)
        self.refresh()
        self.apply_preferences()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync)
        self.timer.start(10000)
        QTimer.singleShot(150, self.sync)

    def page(self, title, subtitle):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(18, 0, 0, 0)
        label = QLabel(title)
        label.setObjectName("title")
        layout.addWidget(label)
        label = QLabel(subtitle)
        label.setObjectName("subtitle")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.stack.addWidget(widget)
        return layout

    def button(self, layout, label, callback):
        b = QPushButton(label)
        if label.startswith(("Guardar", "Asignar", "Nuevo", "Crear", "Ver disponibles", "Registrar")):
            b.setProperty("primary", True)
        b.clicked.connect(callback)
        layout.addWidget(b)
        return b

    def table(self, layout, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(round(30 * getattr(self, "preferences", {}).get("ui_scale", 100) / 100))
        enable_sorting(table)
        if self is not None:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(lambda point: self.show_table_menu(table, point))
            table.setToolTip("Marca las casillas para seleccionar varias filas. Clic derecho para marcar todas, copiar o ver acciones. Clic en un encabezado para ordenar.")
        layout.addWidget(table, 1)
        return table

    def fill(self, table, rows):
        fill_table(table, rows)

    def selected(self, table):
        row = table.currentRow()
        return table.item(row, 0).data(Qt.ItemDataRole.UserRole) if row >= 0 and table.item(row, 0) else None

    def lookup(self, kind, id):
        return getattr(self, "indexes", {}).get(kind, {}).get(id) or next(
            (x for x in self.data.get(kind, []) + self.data.get("archived_" + kind, []) if x["id"] == id), None
        )

    def versions(self, *items):
        return {f"{kind}:{item['id']}": item["version"] for kind, item in items if item}

    def submit(self, action, payload, versions=None):
        if self.session["actor"]["role"] == "viewer":
            info(self, "Tu cuenta tiene acceso de consulta.")
            return
        try:
            origin = getattr(self, "resolving_command", None)
            if origin:
                payload = dict(payload, resolves_command_id=origin)
            request_id = self.store.enqueue(self.session["actor"]["id"], action, payload, versions or {})
        except Exception:
            QMessageBox.critical(
                self,
                "No se guardó la solicitud",
                "No fue posible guardar la solicitud en este equipo. Revisa el espacio disponible y los permisos.",
            )
            return
        self.refresh_queue()
        self.sync()
        self.statusBar().showMessage("Solicitud guardada. Consulta su confirmación en Solicitudes.", 12000)
        return request_id

    def populate_options(self):
        self.options_menu.clear()
        role = self.session["actor"]["role"]
        admin, editor = role == "admin", role != "viewer"

        def add(menu, title, callback, enabled=True):
            action = menu.addAction(title)
            action.triggered.connect(lambda checked=False: callback())
            action.setEnabled(enabled)

        add(self.options_menu, "Opciones de la aplicación…", self.settings_dialog)
        self.options_menu.addSeparator()
        connection = self.options_menu.addMenu("Conexión y solicitudes")
        add(connection, "Iniciar sesión / cambiar cuenta", self.relogin)
        add(connection, "Sincronizar ahora", self.sync)
        add(connection, "Ver solicitudes y sus resultados", lambda: self.nav.setCurrentRow(4))
        add(connection, "Reintentar solicitudes pendientes", self.retry_pending)
        add(connection, "Estado de conexión", self.connection_info)
        maps = self.options_menu.addMenu("Mapa")
        add(maps, "Abrir mapa / buscar un bloque", lambda: (self.nav.setCurrentRow(1), self.map_search.setFocus()))
        add(maps, "Ajustar vista", self.map.fit)
        add(maps, "Consultar", self.consult_mode)
        add(
            maps,
            "Editar mapa",
            lambda: (self.nav.setCurrentRow(1), self.edit_map.setChecked(True), self.toggle_map()),
            admin,
        )
        add(maps, "Guardar posiciones", self.save_map, admin and self.map.editing)
        maps.addSeparator()
        add(maps, "Nuevo bloque", self.block_form, admin)
        add(maps, "Crear fila de bloques", self.start_block_row, admin)
        add(maps, "Nuevo plano", self.plan_form, admin)
        add(maps, "Configurar plano actual", lambda: self.plan_form(True), admin and bool(self.map.plan))
        add(maps, "Agregar contorno", self.add_polygon, admin and self.map.editing)
        add(maps, "Quitar contorno", self.remove_polygon, admin and self.map.editing)
        inventory = self.options_menu.addMenu("Inventario")
        add(inventory, "Abrir inventario", lambda: self.nav.setCurrentRow(3))
        add(inventory, "Revisiones físicas", self.inspections_dialog)
        add(inventory, "Importar bloques Excel / CSV", self.import_inventory, admin)
        add(inventory, "Exportar bloques y ubicaciones", self.export_inventory)
        add(inventory, "Plantilla de inventario", lambda: self.export_inventory(template=True))
        inventory.addSeparator()
        add(inventory, "Eliminar bloque…", self.choose_delete_block, admin)
        add(
            inventory,
            "Eliminar casillero seleccionado",
            lambda: self.delete_inventory("locker", self.lookup("lockers", self.selected(self.inventory))),
            admin and bool(self.selected(self.inventory)),
        )
        add(inventory, "Elementos eliminados / restaurar", self.archived_inventory)
        employees = self.options_menu.addMenu("Empleados")
        add(employees, "Abrir empleados", lambda: self.nav.setCurrentRow(2))
        add(employees, "Nuevo empleado", self.employee_form, editor)
        add(employees, "Importar empleados CSV", self.import_employees, editor)
        add(employees, "Exportar empleados CSV", lambda: self.export("employees"))
        add(employees, "Plantilla de empleados CSV", self.template_csv)
        cuts = self.options_menu.addMenu("Cortes de candado")
        add(cuts, "Abrir solicitudes de corte", lambda: self.nav.setCurrentRow(7))
        add(cuts, "Nueva solicitud de corte", self.new_cut,
            editor and self.data.get("features", {}).get("padlock_cuts", False))
        manage = self.options_menu.addMenu("Administración e historial")
        add(manage, "Cuentas y permisos", lambda: self.nav.setCurrentRow(6), admin)
        add(manage, "Edificios", self.buildings_dialog, admin)
        add(manage, "Avisos a Recursos Humanos", self.mail_settings_form, admin)
        add(manage, "Crear respaldo", self.backup, admin)
        add(manage, "Historial de cambios", lambda: self.nav.setCurrentRow(5))
        add(manage, "Notificaciones de correo", self.notifications)
        self.options_menu.addSeparator()
        add(self.options_menu, "Ayuda y versión", self.quick_help)
        add(self.options_menu, "Cerrar sesión", self.logout)

    def retry_pending(self):
        if self.worker and self.worker.isRunning():
            info(self, "Espera a que termine la sincronización actual.")
            return
        for item in self.store.queue(self.session["actor"]["id"]):
            self.store.retry(item["id"], self.session["actor"]["id"])
        self.refresh_queue()
        if self.connection_state == "sesion":
            self.relogin()
        else:
            self.sync()

    def connection_info(self):
        labels = {
            "online": "Conectado",
            "offline": "Sin conexión",
            "sesion": "Requiere iniciar sesión",
            "error": "Error local",
            "inicial": "Comprobando conexión",
        }
        tasks = self.store.queue(self.session["actor"]["id"])
        waiting = sum(q["status"] in ("pendiente", "requiere_sesion", "error_temporal") for q in tasks)
        info(
            self,
            f"Estado: {labels.get(self.connection_state, self.connection_state)}\nSolicitudes por enviar o confirmar: {waiting}\nÚltima actualización: {local_date(self.data.get('at'))}\n\nSi la sesión venció, inicia sesión. Las solicitudes conservan su identificador y se reenvían sin duplicar efectos.",
        )

    def quick_help(self):
        from . import __version__

        info(
            self,
            f"Samtec Lockers {__version__}\n\nMapa: escribe un bloque o casillero y presiona Enter. Un clic apaga el halo azul.\nInventario: crea, importa, elimina o restaura bloques y casilleros.\nSolicitudes: revisa el resultado confirmado de cada operación. Si aparece Requiere sesión, inicia sesión con la cuenta que creó la solicitud.\nNo necesitas repetir una eliminación pendiente.\nAdministración: gestiona cuentas, edificios, avisos a HR y respaldos.",
        )

    def sync(self):
        if self.worker and self.worker.isRunning():
            return
        self.worker = SyncWorker(self.store, self.config["url"], self.session)
        self.worker.completed.connect(self.synced)
        self.worker.start()

    def synced(self, result):
        self.connection_state = result["state"]
        self.session_button.setVisible(result["state"] == "sesion")
        if result["state"] == "online":
            self.data = result["snapshot"]
            self.session["actor"] = result["actor"]
            self.banner.setText(
                ("DEMOSTRACIÓN · datos ficticios.  " if self.data.get("demo") else "")
                + "Conectado  ·  Última actualización: "
                + local_date(self.data.get("at"))
                + "  ·  Las asignaciones pendientes aún no están confirmadas."
            )
            issues = sum(x["status"] != "confirmada" for x in result.get("changes", []))
            if issues:
                self.statusBar().showMessage(f"{issues} solicitud(es) requieren revisión. Abre Solicitudes.", 20000)
            elif result.get("changes"):
                self.statusBar().showMessage(
                    f"{len(result['changes'])} solicitud(es) confirmadas por el servidor.", 20000
                )
        else:
            self.banner.setText(result.get("message", "") + "  Últimos datos: " + local_date(self.data.get("at")))
        self.refresh()

    def relogin(self):
        if self.worker and self.worker.isRunning():
            info(self, "Espera a que termine la sincronización actual.")
            return
        session = login(self.config, self)
        if session:
            self.session = session
            self.load_preferences()
            self.apply_preferences()
            self.refresh()
            self.sync()

    def logout(self):
        if not confirm(
            self, "¿Cerrar esta cuenta? Las solicitudes pendientes permanecerán guardadas para su responsable."
        ):
            return
        if self.worker and self.worker.isRunning():
            info(self, "Espera a que termine la sincronización actual.")
            return
        try:
            httpx.post(
                self.config["url"] + "/logout",
                headers={"Authorization": "Bearer " + self.session["token"]},
                timeout=3,
                trust_env=False,
            )
        except httpx.HTTPError:
            pass
        from .config import home

        (home() / "session.dat").unlink(missing_ok=True)
        self.close()

    def make_dashboard(self):
        layout = self.page("Cada casillero, en su lugar", "Inventario, ocupación y trazabilidad en un solo lugar.")
        cards = QHBoxLayout()
        self.metrics = []
        for _ in range(4):
            label = QLabel()
            label.setObjectName("metric")
            cards.addWidget(label)
            self.metrics.append(label)
        layout.addLayout(cards)
        row = QHBoxLayout()
        self.button(
            row, "Ver disponibles", lambda: (self.nav.setCurrentRow(3), self.inventory_filter.setCurrentIndex(1))
        )
        self.button(row, "Nuevo empleado", self.employee_form)
        self.button(row, "Sincronizar ahora", self.sync)
        row.addStretch()
        layout.addLayout(row)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addWidget(QLabel("ACTIVIDAD RECIENTE"))
        self.recent = self.table(layout, ["Fecha / hora", "Operación", "Responsable"])

    def make_map(self):
        layout = self.page(
            "Mapa de casilleros",
            "Consulta un bloque con un clic. Acerca con la rueda para leer filas densas; arrastra el fondo para desplazarte.",
        )
        row = QHBoxLayout()
        self.plan_combo = QComboBox()
        row.addWidget(self.plan_combo, 1)
        self.plan_combo.currentIndexChanged.connect(self.render_map)
        self.button(row, "Ajustar vista", lambda: self.map.fit())
        self.consult_map = self.button(row, "Consultar", self.consult_mode)
        self.consult_map.setCheckable(True)
        self.consult_map.setChecked(True)
        self.edit_map = self.button(row, "Editar mapa", self.toggle_map)
        self.edit_map.setCheckable(True)
        self.save_map_button = self.button(row, "Guardar posiciones", self.save_map)
        layout.addLayout(row)
        row = QHBoxLayout()
        map_options = self.actions_button(row, [
            ("Nuevo bloque", self.block_form, "admin"),
            ("Crear fila de bloques", self.start_block_row, "admin"),
            ("Nuevo plano", self.plan_form, "admin"),
            ("Configurar plano", lambda: self.plan_form(True), "admin"),
            ("Agregar contorno", self.add_polygon, "admin"),
            ("Quitar contorno", self.remove_polygon, "admin"),
        ], "Opciones del mapa")
        row.addWidget(QLabel("Clic derecho: acciones del bloque o crear uno en ese lugar."), 1)
        layout.addLayout(row)
        self.map = MapView()

        def add_move_actions():
            menu = map_options.menu()
            menu.addSeparator()
            self.add_map_move_actions(menu)

        map_options.menu().aboutToShow.connect(add_move_actions)
        search_row = QHBoxLayout()
        self.map_search = QLineEdit()
        self.map_search.setPlaceholderText("Código del bloque o número de casillero · Enter para buscar")
        self.map_search.returnPressed.connect(self.search_map)
        search_row.addWidget(self.map_search, 1)
        self.button(search_row, "Buscar en el mapa", self.search_map)
        layout.addLayout(search_row)
        self.map.blockOpened.connect(self.open_block)
        self.map.assignmentsOpened.connect(self.block_assignments)
        self.map.contextRequested.connect(self.show_map_menu)
        self.map.rowPicked.connect(self.create_block_row)
        self.map.rowCancelled.connect(self.cancel_block_row)
        layout.addWidget(self.map, 1)
        legend = QLabel(
            "Verde: hay disponibles · Rojo: completamente asignado · Ámbar: sin disponibles, requiere revisión. Acerca para leer etiquetas pequeñas."
        )
        legend.setWordWrap(True)
        layout.addWidget(legend)

    def render_map(self):
        if not hasattr(self, "map"):
            return
        if self.map.picking_row:
            self.cancel_block_row()
        self.map.render(self.data, self.plan_combo.currentData())
        self.map.fit()

    def search_map(self):
        query = self.map_search.text().strip().casefold()
        if not query:
            return
        if self.map.editing and (self.map.dirty or (self.map.plan and self.map.shapes != self.map.plan["polygons"])):
            info(self, "Guarda las posiciones antes de buscar en otro lugar del mapa.")
            return
        matches = {}
        for block in self.data["blocks"]:
            building = self.lookup("buildings", block["building_id"]) or {}
            codes = (block["label"], f"{building.get('code', '')}-{block['location']}-{block['label']}")
            if query in [code.casefold() for code in codes]:
                matches[block["id"]] = block
        for locker in self.data["lockers"]:
            if query in (locker["number"].casefold(), self.locker_code(locker).casefold()):
                block = self.lookup("blocks", locker["block_id"])
                if block:
                    matches[block["id"]] = block
        if not matches:
            self.map.stop_highlight()
            info(self, "No se encontró ese bloque o casillero. Escribe su código o número completo.")
            return
        if len(matches) > 1:
            choices = []
            for block in matches.values():
                building = self.lookup("buildings", block["building_id"]) or {}
                plan = self.lookup("plans", block["plan_id"]) or {}
                choices.append((f"{building.get('code', '')} · {block['label']} · {plan.get('name', '')}", block["id"]))
            form = Form("Selecciona el bloque", [("id", "Coincidencias", choices)], parent=self)
            if form.exec() != QDialog.DialogCode.Accepted:
                return
            block = matches[form.values()["id"]]
        else:
            block = next(iter(matches.values()))
        self.edit_map.setChecked(False)
        self.consult_map.setChecked(True)
        self.map.set_editing(False)
        self.plan_combo.setCurrentIndex(self.plan_combo.findData(block["plan_id"]))
        self.map.start_highlight(block["id"], focus=True)
        self.statusBar().showMessage(
            f"Encontrado en {block['label']}. Selecciona el bloque para apagar la luz azul.", 12000
        )

    def toggle_map(self):
        if self.map.picking_row:
            self.cancel_block_row()
        if self.session["actor"]["role"] != "admin":
            self.edit_map.setChecked(False)
            info(self, "Solo los administradores editan el mapa.")
            return
        self.map.set_editing(self.edit_map.isChecked())
        self.consult_map.setChecked(not self.edit_map.isChecked())
        if not self.edit_map.isChecked():
            self.render_map()

    def consult_mode(self):
        self.edit_map.setChecked(False)
        self.consult_map.setChecked(True)
        self.map.set_editing(False)
        self.render_map()

    def block_assignments(self, id):
        block = self.lookup("blocks", id)
        if not block:
            return
        lockers = {item["id"]: item for item in self.data["lockers"] if item["block_id"] == id}
        dialog = QDialog(self)
        dialog.setWindowTitle("Asignaciones · " + block["label"])
        dialog.resize(760, 480)
        layout = QVBoxLayout(dialog)
        table = self.table(layout, ["Casillero", "ID empleado", "Nombre", "Primer apellido", "Segundo apellido"])
        rows = []
        for assignment in self.data["assignments"]:
            if assignment["ended_at"] is not None or assignment["locker_id"] not in lockers:
                continue
            person = self.lookup("employees", assignment["employee_id"]) or {}
            locker = lockers[assignment["locker_id"]]
            rows.append(
                (
                    locker["id"],
                    [
                        locker["number"],
                        person.get("employee_number", ""),
                        person.get("first_name", ""),
                        person.get("surname", ""),
                        person.get("second_surname", ""),
                    ],
                )
            )
        rows.sort(key=lambda entry: entry[1][0])
        self.fill(table, rows)
        table.context_actions = lambda key: [
            ("Abrir casillero", lambda: self.locker_dialog(key), None),
        ]
        layout.addWidget(
            QLabel(
                f"{len(rows)} asignaciones vigentes · Según la última sincronización."
                if rows
                else "Este bloque no tiene asignaciones vigentes."
            )
        )
        self.button(layout, "Cerrar", dialog.accept)
        dialog.exec()

    def save_map(self):
        if not self.map.editing or not self.map.plan:
            info(self, "Activa Editar mapa para mover bloques o los puntos de los contornos.")
            return
        for id, (x, y) in list(self.map.dirty.items()):
            block = self.lookup("blocks", id)
            payload = dict(block, x=x, y=y)
            self.submit("block.update", payload, self.versions(("block", block)))
        plan = self.map.plan
        if self.map.shapes != plan["polygons"]:
            payload = {k: v for k, v in plan.items() if k != "background"}
            payload["polygons"] = self.map.shapes
            self.submit("plan.update", payload, self.versions(("plan", plan)))
        self.edit_map.setChecked(False)
        self.consult_map.setChecked(True)
        self.map.set_editing(False)
        info(self, "Las modificaciones se enviaron como solicitudes. Revisa su resultado antes de volver a editar.")

    def add_polygon(self):
        if not self.map.editing or not self.map.plan:
            info(self, "Activa Editar mapa primero.")
            return
        choices = [(b["name"], b["id"]) for b in self.data["buildings"]]
        form = Form("Nuevo contorno", [("building_id", "Edificio", choices)], parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.map.shapes.append(
                {
                    "building_id": form.values()["building_id"],
                    "points": [[400, 400], [600, 400], [600, 600], [400, 600]],
                }
            )
            payload = {k: v for k, v in self.map.plan.items() if k != "background"}
            payload["polygons"] = self.map.shapes
            self.submit("plan.update", payload, self.versions(("plan", self.map.plan)))
            self.edit_map.setChecked(False)
            self.map.set_editing(False)

    def remove_polygon(self):
        if not self.map.editing or not self.map.plan:
            info(self, "Activa Editar mapa primero.")
            return
        options = [
            (str(i + 1) + " · " + (self.lookup("buildings", s["building_id"]) or {}).get("name", ""), i)
            for i, s in enumerate(self.map.shapes)
        ]
        if not options:
            return
        form = Form("Quitar contorno", [("index", "Contorno", options)], parent=self)
        if form.exec() == QDialog.DialogCode.Accepted and confirm(
            self, "¿Quitar este contorno del plano? Quedará registrado en el historial."
        ):
            payload = {k: v for k, v in self.map.plan.items() if k != "background"}
            payload["polygons"] = copy.deepcopy(self.map.shapes)
            payload["polygons"].pop(form.values()["index"])
            self.submit("plan.update", payload, self.versions(("plan", self.map.plan)))
            self.edit_map.setChecked(False)
            self.map.set_editing(False)

    def plan_form(self, edit=False):
        plan = self.lookup("plans", self.plan_combo.currentData()) if edit else None
        fields = [
            ("name", "Nombre", "line"),
            ("kind", "Tipo", [("Exterior", "exterior"), ("Interior", "interior")]),
            ("floor", "Piso / nivel", "line"),
            (
                "building_id",
                "Edificio",
                [("Campus (varios)", None)] + [(b["name"], b["id"]) for b in self.data["buildings"]],
            ),
        ]
        form = Form(
            "Configurar plano" if plan else "Nuevo plano",
            fields,
            plan,
            parent=self,
            description="Puedes crear planos interiores por edificio y nivel. La imagen se conserva si no eliges un archivo nuevo.",
        )
        if form.exec() != QDialog.DialogCode.Accepted:
            return
        payload = form.values()
        payload["polygons"] = plan["polygons"] if plan else []
        if plan:
            payload["id"] = plan["id"]
        if confirm(self, "¿Seleccionar una imagen de fondo PNG o JPEG para este plano?"):
            filename, _ = QFileDialog.getOpenFileName(self, "Imagen de fondo", "", "Imágenes (*.png *.jpg *.jpeg)")
            if filename:
                raw = Path(filename).read_bytes()
                if len(raw) > 6_000_000:
                    info(self, "La imagen debe pesar como máximo 6 MB.")
                    return
                payload["background"] = base64.b64encode(raw).decode()
        self.submit("plan.update" if plan else "plan.create", payload, self.versions(("plan", plan)))

    def block_form(self, block=None, position=None, plan_id=None):
        if isinstance(block, bool):
            block = None
        if not self.data["plans"] or not self.data["buildings"]:
            info(self, "Primero crea un edificio y un plano.")
            return
        fields = [
            ("label", "Nombre del bloque", "line"),
            ("x", "Posición X", "float"),
            ("y", "Posición Y", "float"),
            ("rotation", "Rotación", "float"),
        ]
        if not block:
            fields = [
                ("plan_id", "Plano", [(p["name"], p["id"]) for p in self.data["plans"]]),
                ("building_id", "Edificio", [(b["name"], b["id"]) for b in self.data["buildings"]]),
                ("side", "Lado", [("Norte", "N"), ("Sur", "S"), ("Este", "E"), ("Oeste", "O")]),
                ("location", "Ubicación", [("Exterior", "EXT"), ("Interior", "INT")]),
                ("rows", "Filas", "int"),
                ("columns", "Columnas", "int"),
                ("start", "Primer número (si son consecutivos)", "line"),
                ("numbers", "O números separados por comas", "text"),
            ] + fields
        form = Form(
            "Editar bloque" if block else "Nuevo bloque",
            fields,
            block
            or {**{k: v for k, v in self.new_block_defaults().items() if k not in ("prefix", "count")},
                "x": position[0] if position else 500, "y": position[1] if position else 500,
                "label": self.preferences["block"]["prefix"] + "01", "plan_id": plan_id or self.plan_combo.currentData()},
            self,
            description="Los casilleros nuevos quedan pendientes de verificación física. La numeración avanza de derecha a izquierda, fila por fila de arriba hacia abajo. La columna 1 está a la derecha.",
        )
        form.widgets["rotation"].setRange(-360, 360)
        if form.exec() != QDialog.DialogCode.Accepted:
            return
        payload = form.values()
        if block:
            payload["id"] = block["id"]
        else:
            if payload["numbers"].strip():
                payload["numbers"] = [x.strip() for x in payload["numbers"].replace("\n", ",").split(",") if x.strip()]
            else:
                try:
                    payload["numbers"] = [
                        str(int(payload["start"]) + i) for i in range(payload["rows"] * payload["columns"])
                    ]
                except ValueError:
                    info(self, "Indica el primer número o la lista de números físicos.")
                    return
            payload.pop("start", None)
        self.submit("block.update" if block else "block.create", payload, self.versions(("block", block)))

    def open_block(self, id):
        block = self.lookup("blocks", id)
        if not block:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Bloque " + block["label"])
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"{block['rows']} filas × {block['columns']} columnas"))
        layout.addWidget(QLabel("Vista de frente · Numeración de derecha a izquierda, de arriba hacia abajo."))
        grid = QGridLayout()
        layout.addLayout(grid)
        for locker in sorted(
            (x for x in self.data["lockers"] if x["block_id"] == id), key=lambda x: (x["row"], x["column"])
        ):
            state = self.locker_state(locker)
            button = QPushButton(locker["number"] + "\n" + STATES[state])
            button.setMinimumSize(145, 70)
            color = {
                "ocupado": "#444444",
                "pendiente": "#997329",
                "mantenimiento": "#a24b36",
                "retirado": "#6b7280",
                "utilizable": "#26724f",
            }[state]
            button.setStyleSheet(f"background:{color};color:white;")
            button.clicked.connect(
                lambda checked=False, locker=locker: (dialog.accept(), self.locker_dialog(locker["id"]))
            )
            # Stored column is the ordinal within the numbering sequence (0 = right).
            grid.addWidget(button, locker["row"], block["columns"] - 1 - locker["column"])
        self.button(layout, "Editar nombre / posición", lambda: (dialog.accept(), self.block_form(block)))
        self.button(layout, "Eliminar bloque", lambda: (dialog.accept(), self.delete_inventory("block", block)))
        self.button(
            layout, "Confirmar verificación física del bloque", lambda: (dialog.accept(), self.verify_block(block))
        )
        dialog.exec()

    def verify_block(self, block):
        lockers = [
            locker
            for locker in self.data["lockers"]
            if locker["block_id"] == block["id"] and locker["condition"] == "pendiente"
        ]
        if not lockers:
            info(self, "Este bloque no tiene casilleros pendientes de verificar.")
            return
        if not confirm(
            self,
            f"¿Verificaste físicamente que los {len(lockers)} casilleros pendientes de este bloque están vacíos y utilizables? No confirmes si desconoces su ocupación.",
        ):
            return
        self.submit(
            "lockers.verify",
            {"block_id": block["id"], "reason": "Verificación física de casilleros vacíos y utilizables"},
            self.versions(("block", block), *[("locker", locker) for locker in lockers]),
        )

    def make_employees(self):
        layout = self.page("Empleados", "Busca por nombre, identificación o correo. Las bajas conservan el historial.")
        row = QHBoxLayout()
        self.employee_search = QLineEdit()
        self.employee_search.setPlaceholderText("Buscar empleado…")
        row.addWidget(self.employee_search, 1)
        self.button(row, "Nuevo", self.employee_form)
        self.actions_button(row, [
            ("Importar CSV", self.import_employees, "editor"),
            ("Exportar CSV", lambda: self.export("employees"), None),
            ("Plantilla CSV", self.template_csv, None),
        ])
        layout.addLayout(row)
        row = QHBoxLayout()
        self.employee_status = QComboBox()
        self.employee_status.addItem("Empleados activos", "active")
        self.employee_status.addItem("Empleados inactivos", "inactive")
        self.employee_status.addItem("Todos los empleados", "all")
        row.addWidget(self.employee_status)
        self.employee_status.currentIndexChanged.connect(self.refresh_employees)
        row.addWidget(QLabel("Clic derecho en un empleado para editar, asignar o dar de baja."))
        row.addStretch()
        layout.addLayout(row)
        self.employees = self.table(
            layout, ["ID empleado", "Nombre", "Correo", "Departamento", "Turno", "Estado", "Casillero"]
        )
        self.employee_search.textChanged.connect(self.refresh_employees)
        self.employees.cellDoubleClicked.connect(lambda r, c: self.employee_form(True))

    def employee_form(self, edit=False, employee_id=None):
        item = self.lookup("employees", employee_id or self.selected(self.employees)) if edit else None
        if edit and not item:
            info(self, "Selecciona una persona.")
            return
        fields = [
            ("employee_number", "ID de empleado", "line"),
            ("first_name", "Nombre", "line"),
            ("surname", "Primer apellido", "line"),
            ("second_surname", "Segundo apellido (opcional)", "line"),
            ("email", "Correo (opcional)", "line"),
            ("department", "Departamento", "line"),
            ("shift", "Turno", "line"),
            ("active", "Activo", "bool"),
            ("notes", "Notas", "text"),
        ]
        form = Form("Editar empleado" if item else "Nuevo empleado", fields, item or dict(self.preferences["employee"]), self)
        if item and item["active"]:
            form.widgets["active"].setEnabled(False)
            form.widgets["active"].setToolTip("Para registrar una salida utiliza Dar de baja y liberar.")
        if form.exec() == QDialog.DialogCode.Accepted:
            payload = form.values()
            if item:
                payload["id"] = item["id"]
            self.submit("employee.update" if item else "employee.create", payload, self.versions(("employee", item)))

    def employee_release(self):
        employee = self.lookup("employees", self.selected(self.employees))
        current = self.assignment_for(employee_id=employee["id"]) if employee else None
        if not current:
            info(self, "Selecciona un empleado con un casillero asignado.")
            return
        self.release(current)

    def deactivate_employee(self):
        employee = self.lookup("employees", self.selected(self.employees))
        if not employee or not employee["active"]:
            info(self, "Selecciona un empleado activo.")
            return
        current = self.assignment_for(employee_id=employee["id"])
        locker = self.lookup("lockers", current["locker_id"]) if current else None
        form = Form(
            "Dar de baja y liberar",
            [
                (
                    "departure_type",
                    "Tipo de baja",
                    [
                        ("Selecciona el tipo de baja", None),
                        ("Despido", "despido"),
                        ("Renuncia", "renuncia"),
                        ("Fin de contrato", "fin_contrato"),
                        ("Otra baja", "otra_baja"),
                    ],
                ),
                ("reason", "Motivo interno", "text"),
                ("locker_verified", "Confirmé que está vacío y utilizable", "bool"),
            ],
            parent=self,
            description=full_name(employee)
            + " · ID "
            + employee["employee_number"]
            + ". "
            + (
                "Se cerrará la asignación del casillero " + locker["number"] + ". "
                if locker
                else "No tiene casillero asignado. "
            )
            + "La persona quedará inactiva y conservará su historial. Se preparará un aviso simulado para HR, sin incluir el motivo interno. Sin verificación física, el casillero quedará pendiente de revisión.",
            accept_label="Confirmar baja",
        )
        form.form_layout.setRowVisible(form.widgets["locker_verified"], locker is not None)
        if form.exec() != QDialog.DialogCode.Accepted:
            return
        payload = form.values()
        if not payload["departure_type"]:
            info(self, "Selecciona el tipo de baja.")
            return
        if not payload["reason"].strip():
            info(self, "Indica el motivo interno de la baja.")
            return
        payload.update(employee_id=employee["id"], assignment_id=current["id"] if current else None)
        self.submit("employee.deactivate", payload, self.versions(("employee", employee), ("locker", locker)))

    def employee_assignment(self, employee_id=None):
        employee = self.lookup("employees", employee_id or self.selected(self.employees))
        if not employee:
            info(self, "Selecciona una persona.")
            return
        available = [locker for locker in self.data["lockers"] if self.locker_state(locker) == "utilizable"]
        if not available:
            info(self, "No hay casilleros verificados y disponibles en la última información recibida.")
            return
        form = Form(
            "Asignar / reasignar",
            [
                ("locker_id", "Casillero", [(self.locker_code(locker), locker["id"]) for locker in available]),
                ("reason", "Motivo", "text"),
            ],
            parent=self,
            description=full_name(employee),
        )
        if form.exec() == QDialog.DialogCode.Accepted:
            self.assign(employee, self.lookup("lockers", form.values()["locker_id"]), form.values()["reason"])

    def assignment_for(self, **filters):
        if hasattr(self, "current_by_employee") and set(filters) == {"employee_id"}:
            return self.current_by_employee.get(filters["employee_id"])
        if hasattr(self, "current_by_locker") and set(filters) == {"locker_id"}:
            return self.current_by_locker.get(filters["locker_id"])
        return next(
            (
                a
                for a in self.data["assignments"]
                if a["ended_at"] is None and all(a[k] == v for k, v in filters.items())
            ),
            None,
        )

    def locker_state(self, locker):
        return "ocupado" if self.assignment_for(locker_id=locker["id"]) else locker["condition"]

    def locker_code(self, locker):
        b = self.lookup("blocks", locker["block_id"])
        building = self.lookup("buildings", b["building_id"]) if b else None
        return (
            f"{building['code']}-{b['location']}-{b['label']}-{locker['number']}"
            if b and building
            else locker["number"]
        )

    def make_inventory(self):
        layout = self.page(
            "Inventario", "Un casillero sin persona registrada no está disponible hasta verificarlo físicamente."
        )
        row = QHBoxLayout()
        self.locker_search = QLineEdit()
        self.locker_search.setPlaceholderText("Número, código, edificio, persona…")
        row.addWidget(self.locker_search, 1)
        self.inventory_filter = QComboBox()
        self.inventory_filter.addItem("Todos", "")
        for state in ("utilizable", "ocupado", "pendiente", "mantenimiento", "retirado"):
            self.inventory_filter.addItem(STATES[state], state)
        row.addWidget(self.inventory_filter)
        self.actions_button(row, [
            ("Importar bloques Excel / CSV", self.import_inventory, "admin"),
            ("Revisiones físicas", self.inspections_dialog, None),
            ("Exportar bloques y ubicaciones", self.export_inventory, None),
            ("Exportar casilleros CSV", lambda: self.export("lockers"), None),
            ("Plantilla de inventario", lambda: self.export_inventory(template=True), None),
            ("Elementos eliminados / restaurar", self.archived_inventory, None),
        ])
        layout.addLayout(row)
        layout.addWidget(QLabel("Clic derecho en un casillero para ver sus acciones y las de su bloque. Columna 1 = derecha."))
        self.inventory = self.table(layout, ["Número", "Ubicación", "Estado", "Empleado", "Fila / columna"])
        self.inventory.horizontalHeaderItem(4).setToolTip(
            "Fila 1 = arriba; columna 1 = derecha. Haz clic para ordenar."
        )
        self.locker_search.textChanged.connect(self.refresh_inventory)
        self.inventory_filter.currentIndexChanged.connect(self.refresh_inventory)
        self.inventory.cellDoubleClicked.connect(lambda r, c: self.locker_dialog(self.selected(self.inventory)))

    def choose_delete_block(self):
        choices = [
            (f"{(self.lookup('buildings', b['building_id']) or {}).get('code', '')} · {b['label']}", b["id"])
            for b in self.data["blocks"]
        ]
        if not choices:
            info(self, "No hay bloques en el inventario.")
            return
        form = Form("Eliminar bloque", [("id", "Bloque", choices)], parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.delete_inventory("block", self.lookup("blocks", form.values()["id"]))

    def delete_inventory(self, kind, item, restore=False):
        if self.session["actor"]["role"] != "admin":
            info(self, "Solo Administración puede eliminar o restaurar inventario.")
            return
        if not item:
            info(self, "Selecciona un elemento del inventario.")
            return
        if not restore and any(
            q["command"]["action"] == kind + ".delete"
            and q["command"]["payload"].get("id") == item["id"]
            and q["status"] in ("pendiente", "requiere_sesion", "error_temporal")
            for q in self.store.queue(self.session["actor"]["id"])
        ):
            self.nav.setCurrentRow(4)
            info(
                self,
                "Esta eliminación ya está guardada. Inicia sesión si se solicita y sincroniza; no necesitas volver a eliminarla.",
            )
            return
        children = [
            locker
            for locker in self.data.get("archived_lockers" if restore else "lockers", [])
            if kind == "block"
            and locker["block_id"] == item["id"]
            and (not restore or locker.get("deleted_at") == item.get("deleted_at"))
        ]
        if any(self.assignment_for(locker_id=locker["id"]) for locker in (children if kind == "block" else [item])):
            info(self, "Primero libera las asignaciones activas. No se eliminó ningún elemento.")
            return
        label = item["label"] if kind == "block" else item["number"]
        verb = "Restaurar" if restore else "Eliminar"
        description = (
            f"{label}: "
            + (f"incluye {len(children)} casilleros. " if kind == "block" else "")
            + (
                "Volverá al inventario; los casilleros deberán verificarse físicamente."
                if restore
                else "Se quitará del mapa y del inventario. Se conserva el historial. El código queda reservado; puedes recuperarlo en Elementos eliminados."
            )
        )
        form = Form(
            verb + (" bloque" if kind == "block" else " casillero"),
            [("reason", "Motivo", "text")],
            parent=self,
            description=description,
            accept_label=verb,
        )
        if form.exec() == QDialog.DialogCode.Accepted:
            reason = form.values()["reason"].strip()
            if not reason:
                info(self, "Escribe el motivo de la operación.")
                return
            self.submit(
                kind + (".restore" if restore else ".delete"),
                {"id": item["id"], "reason": reason},
                self.versions((kind, item), *[("locker", locker) for locker in children]),
            )

    def archived_inventory(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Elementos eliminados")
        dialog.resize(800, 480)
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            QLabel("El historial y los códigos se conservan. Restaura primero el bloque si también fue eliminado.")
        )
        layout.addWidget(QLabel("Marca las casillas para actuar sobre varios elementos. Clic derecho permite marcar todos."))
        table = self.table(layout, ["Tipo", "Código", "Eliminado el"])
        items = {
            kind + ":" + item["id"]: (kind, item)
            for kind, group in [("block", "archived_blocks"), ("locker", "archived_lockers")]
            for item in self.data.get(group, [])
        }
        self.fill(
            table,
            [
                (
                    key,
                    [
                        "Bloque" if kind == "block" else "Casillero",
                        item.get("label", item.get("number")),
                        local_date(item["deleted_at"]),
                    ],
                )
                for key, (kind, item) in items.items()
            ],
        )

        def restore_selected():
            selected = items.get(self.selected(table))
            if selected:
                dialog.accept()
                self.delete_inventory(*selected, restore=True)

        self.button(layout, "Restaurar seleccionado", restore_selected)
        self.button(layout, "Restaurar marcados", lambda: self.archived_batch(table, items, dialog))
        if self.initial_admin():
            self.button(layout, "Eliminar definitivamente marcados", lambda: self.archived_batch(table, items, dialog, purge=True))
        table.context_actions = lambda key: (
            [("Restaurar elemento", restore_selected, "admin"),
             ("Restaurar marcados", lambda: self.archived_batch(table, items, dialog), "admin")]
            + ([("Eliminar definitivamente marcados", lambda: self.archived_batch(table, items, dialog, purge=True), "admin")]
               if self.initial_admin() else [])
        )
        self.button(layout, "Cerrar", dialog.reject)
        dialog.exec()

    def export_inventory(self, checked=False, template=False):
        from .inventory_io import write_inventory, export_rows

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar inventario",
            "plantilla-inventario.xlsx" if template else "inventario-bloques.xlsx",
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return
        try:
            write_inventory(path, [] if template else export_rows(self.data))
            info(
                self,
                "Archivo guardado. Incluye ubicaciones y numeración; no incluye datos de empleados."
                + (" Consulta la hoja Instrucciones." if path.lower().endswith(".xlsx") else ""),
            )
        except Exception as exc:
            info(self, "No se pudo guardar el archivo: " + str(exc))

    def import_inventory(self):
        from .inventory_io import read_inventory, prepare_import

        if self.session["actor"]["role"] != "admin":
            info(self, "Solo los administradores importan bloques.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Importar inventario", "", "Inventario (*.xlsx *.csv)")
        if not path:
            return
        try:
            rows = read_inventory(path)
            operations, versions = prepare_import(rows, self.data)
        except Exception as exc:
            info(self, "No se importó ningún registro. " + str(exc))
            return
        if not operations:
            info(self, "El archivo coincide con el inventario actual. No hay cambios que importar.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Revisar importación de inventario")
        dialog.resize(900, 580)
        layout = QVBoxLayout(dialog)
        creates = sum(op["action"] == "block.create" for op in operations)
        description = QLabel(
            f"{creates} bloques nuevos · {len(operations) - creates} bloques a actualizar.\nLos casilleros nuevos quedan pendientes de verificación. Las asignaciones se conservan.\nSe enviará una sola solicitud: si existe un conflicto, no se aplica ningún cambio del archivo."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        table = self.table(layout, ["Operación", "Bloque", "Plano", "Edificio", "Casilleros", "X", "Y", "Rotación"])
        self.fill(
            table,
            [
                (
                    str(i),
                    [
                        "Crear" if op["action"] == "block.create" else "Actualizar",
                        p["label"],
                        (self.lookup("plans", p["plan_id"]) or {}).get("name", ""),
                        (self.lookup("buildings", p["building_id"]) or {}).get("code", ""),
                        p["rows"] * p["columns"],
                        p["x"],
                        p["y"],
                        p["rotation"],
                    ],
                )
                for i, op in enumerate(operations)
                for p in [op["payload"]]
            ],
        )
        row = QHBoxLayout()
        layout.addLayout(row)
        self.button(row, "Importar inventario", dialog.accept)
        self.button(row, "Cancelar", dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.submit("inventory.import", {"operations": operations}, versions)

    def locker_dialog(self, id):
        locker = self.lookup("lockers", id)
        if not locker:
            info(self, "Selecciona un casillero.")
            return
        assignment = self.assignment_for(locker_id=id)
        person = self.lookup("employees", assignment["employee_id"]) if assignment else None
        form = Form(
            self.locker_code(locker),
            [
                ("number", "Número físico", "line"),
                (
                    "condition",
                    "Condición",
                    [
                        ("Verificado y utilizable", "utilizable"),
                        ("Pendiente de verificar", "pendiente"),
                        ("Mantenimiento", "mantenimiento"),
                        ("Retirado", "retirado"),
                    ],
                ),
                ("notes", "Notas del casillero", "text"),
            ],
            locker,
            self,
            description=(
                "Asignado a " + full_name(person) + " · " + person["employee_number"]
                if person
                else "Sin asignación vigente. Estado: " + STATES[locker["condition"]]
            ),
        )
        if person:
            self.button(form.layout(), "Liberar casillero", lambda: (form.reject(), self.release(assignment)))
        elif locker["condition"] == "utilizable":
            self.button(form.layout(), "Asignar a una persona", lambda: (form.reject(), self.choose_person(locker)))
        self.button(
            form.layout(), "Eliminar casillero", lambda: (form.reject(), self.delete_inventory("locker", locker))
        )
        history = [a for a in self.data["assignments"] if a["locker_id"] == id]
        if history:
            text = "\n".join(
                f"{local_date(a['started_at'])} → {local_date(a['ended_at'])} · {full_name(self.lookup('employees', a['employee_id']) or {})}"
                for a in history
            )
            self.button(form.layout(), "Ver historial del casillero", lambda: info(form, text))
        if form.exec() == QDialog.DialogCode.Accepted:
            self.submit("locker.update", dict(form.values(), id=id), self.versions(("locker", locker)))

    def choose_person(self, locker):
        people = [e for e in self.data["employees"] if e["active"]]
        if not people:
            info(self, "Primero registra una persona activa.")
            return
        form = Form(
            "Asignar casillero",
            [
                ("employee_id", "Persona", [(e["employee_number"] + " · " + full_name(e), e["id"]) for e in people]),
                ("reason", "Motivo", "text"),
            ],
            parent=self,
            description="Si la persona ya tiene casillero, se propondrá una reasignación. Se confirma al recibir la respuesta del servidor.",
        )
        if form.exec() == QDialog.DialogCode.Accepted:
            self.assign(self.lookup("employees", form.values()["employee_id"]), locker, form.values()["reason"])

    def assign(self, employee, locker, reason):
        if not employee or not locker:
            info(self, "Selecciona una persona y un casillero de las sugerencias.")
            return
        if not reason.strip():
            info(self, "Indica el motivo de la asignación.")
            return
        current = self.assignment_for(employee_id=employee["id"])
        previous = self.lookup("lockers", current["locker_id"]) if current else None
        if current and not confirm(
            self, f"¿Reasignar a {full_name(employee)} del casillero {previous['number']} al {locker['number']}?"
        ):
            return
        self.submit(
            "assignment.transfer" if current else "assignment.assign",
            {
                "employee_id": employee["id"],
                "locker_id": locker["id"],
                "assignment_id": current["id"] if current else None,
                "reason": reason,
            },
            self.versions(("employee", employee), ("locker", locker), ("locker", previous)),
        )

    def release(self, assignment):
        employee = self.lookup("employees", assignment["employee_id"])
        locker = self.lookup("lockers", assignment["locker_id"])
        form = Form(
            "Liberar casillero",
            [
                (
                    "release_type",
                    "Motivo",
                    [
                        ("Solicitud del empleado", "Solicitud del empleado"),
                        ("Ya no necesita casillero", "Ya no necesita casillero"),
                        ("Otra devolución", "Otra devolución"),
                    ],
                ),
                ("notes", "Observaciones internas", "text"),
                ("locker_verified", "Confirmé que está vacío y utilizable", "bool"),
            ],
            parent=self,
            description=full_name(employee)
            + " · Casillero "
            + locker["number"]
            + ". El empleado seguirá activo. Se preparará un aviso simulado al empleado y, si está configurado, a HR. Sin verificación física, el casillero quedará pendiente de revisión.",
            accept_label="Confirmar liberación",
        )
        if form.exec() == QDialog.DialogCode.Accepted:
            values = form.values()
            reason = values["release_type"] + (": " + values["notes"].strip() if values["notes"].strip() else "")
            self.submit(
                "assignment.release",
                {
                    "employee_id": employee["id"],
                    "assignment_id": assignment["id"],
                    "reason": reason,
                    "locker_verified": values["locker_verified"],
                },
                self.versions(("employee", employee), ("locker", locker)),
            )

    def make_queue(self):
        layout = self.page(
            "Solicitudes de este equipo",
            "Pendiente no significa asignado. Las solicitudes conservan responsable e identificador al reintentarse.",
        )
        row = QHBoxLayout()
        self.button(row, "Sincronizar ahora", self.sync)
        row.addWidget(QLabel("Clic derecho en una solicitud para consultar o reintentar."))
        row.addStretch()
        layout.addLayout(row)
        self.queue_table = self.table(layout, ["Creada", "Operación", "Estado", "Intentos", "Resultado"])
        self.queue_table.cellDoubleClicked.connect(lambda r, c: self.queue_detail())
        layout.addWidget(
            QLabel(
                "Los conflictos se resuelven revisando los datos actuales y creando una nueva solicitud. Se muestra la cola de tu cuenta."
            )
        )

    def retry(self):
        id = self.selected(self.queue_table)
        if id:
            self.store.retry(id, self.session["actor"]["id"])
            self.refresh_queue()
            self.sync()

    def queue_detail(self):
        item = next(
            (q for q in self.store.queue(self.session["actor"]["id"]) if q["id"] == self.selected(self.queue_table)),
            None,
        )
        if item:
            content = copy.deepcopy(item)
            content["command"]["payload"].pop("password", None)
            content["command"]["payload"].pop("background", None)
            content["command"]["payload"].pop("photo", None)
            info(
                self,
                "Solicitud: "
                + item["id"]
                + "\n"
                + item["message"]
                + "\n\n"
                + json.dumps(content["command"]["payload"], ensure_ascii=False, indent=2),
            )

    def make_history(self):
        layout = self.page(
            "Historial y notificaciones",
            "Cada cambio confirmado conserva fecha del servidor, responsable y valores anteriores. Horas en Costa Rica.",
        )
        row = QHBoxLayout()
        self.audit_search = QLineEdit()
        self.audit_search.setPlaceholderText("Buscar operación, persona, casillero o responsable…")
        row.addWidget(self.audit_search, 1)
        self.button(row, "Cargar historial anterior", self.load_history)
        self.actions_button(row, [
            ("Exportar historial cargado", lambda: self.export("audit"), None),
            ("Ver notificaciones de correo (simuladas)", self.notifications, None),
        ])
        layout.addLayout(row)
        self.audit_table = self.table(layout, ["Fecha / hora", "Operación", "Responsable", "Registro", "Motivo"])
        self.audit_search.textChanged.connect(self.refresh_history)
        self.audit_table.cellDoubleClicked.connect(self.audit_detail)

    def audit_detail(self, row, col):
        self.show_audit(self.selected(self.audit_table))

    def show_audit(self, id):
        item = self.lookup("audit", id)
        if item:
            info(
                self,
                "Antes:\n"
                + json.dumps(item["before"], ensure_ascii=False, indent=2)
                + "\n\nDespués:\n"
                + json.dumps(item["after"], ensure_ascii=False, indent=2),
            )

    def load_history(self):
        try:
            r = httpx.get(
                self.config["url"] + "/audit",
                params={"offset": len(self.data["audit"])},
                headers={"Authorization": "Bearer " + self.session["token"]},
                timeout=8,
                trust_env=False,
            )
            r.raise_for_status()
            self.data["audit"].extend(r.json())
            self.refresh_history()
            if not r.json():
                info(self, "No hay más eventos anteriores.")
        except httpx.HTTPError:
            info(self, "No se pudo cargar el historial anterior. Verifica conexión y sesión.")

    def notifications(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Correo · modo simulado")
        dialog.resize(950, 550)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("No se envían correos reales. La integración corporativa se configura con TI."))
        table = self.table(layout, ["Fecha", "Para", "Copia a", "Asunto", "Estado"])
        self.fill(
            table,
            [
                (
                    n["id"],
                    [
                        local_date(n["at"]),
                        n["recipient"] or "Sin destinatario",
                        ", ".join(n.get("cc", [])),
                        n["subject"],
                        {
                            "simulado": "Simulado",
                            "sin_destinatario": "Falta destinatario",
                            "simulado_sin_hr": "Simulado · falta correo HR",
                        }.get(n["status"], n["status"]),
                    ],
                )
                for n in self.data["notifications"]
            ],
        )
        table.cellDoubleClicked.connect(
            lambda r, c: info(dialog, (self.lookup("notifications", self.selected(table)) or {}).get("body", ""))
        )
        table.context_actions = lambda key: [
            ("Ver mensaje", lambda: info(dialog, (self.lookup("notifications", key) or {}).get("body", "")), None),
        ]
        dialog.exec()

    def make_admin(self):
        layout = self.page("Administración", "Cuentas individuales, edificios y copias de seguridad.")
        row = QHBoxLayout()
        self.button(row, "Nueva cuenta", self.admin_form)
        self.actions_button(row, [
            ("Edificios", self.buildings_dialog, "admin"),
            ("Crear copia de seguridad", self.backup, "admin"),
            ("Configurar avisos a HR", self.mail_settings_form, "admin"),
        ])
        row.addWidget(QLabel("Clic derecho en una cuenta para editar sus datos y permisos."))
        row.addStretch()
        layout.addLayout(row)
        self.admin_table = self.table(layout, ["Usuario", "Nombre", "Permiso", "Estado"])
        label = QLabel(
            "Servidor: "
            + self.config["url"]
            + "\nLas contraseñas se guardan cifradas localmente. Las cuentas de consulta no pueden modificar información.\nLa restauración se realiza con el procedimiento documentado, con el servicio detenido."
        )
        label.setWordWrap(True)
        layout.addWidget(label)

    def mail_settings_form(self):
        if self.session["actor"]["role"] != "admin":
            info(self, "Solo una cuenta de administración puede configurar los avisos.")
            return
        settings = next(iter(self.data.get("mail_settings", [])), None)
        if not settings:
            info(self, "Sincroniza con el servidor actualizado antes de configurar los avisos.")
            return
        form = Form(
            "Avisos a Recursos Humanos",
            [("hr_email", "Correo de HR", "line"), ("copy_hr_on_release", "Copiar a HR en devoluciones", "bool")],
            settings,
            self,
            description="Las bajas se notifican únicamente a HR. Las devoluciones se notifican al empleado y, si activas la opción, a HR. Los avisos se registran en modo simulado: TI debe habilitar el envío corporativo. Cambiar esta configuración solo afecta avisos futuros.",
        )
        if form.exec() == QDialog.DialogCode.Accepted:
            self.submit("mail_settings.update", form.values(), self.versions(("mail_settings", settings)))

    def admin_form(self, edit=False):
        item = self.lookup("admins", self.selected(self.admin_table)) if edit else None
        if edit and not item:
            return
        form = Form(
            "Cuenta administradora",
            [
                ("username", "Usuario", "line"),
                ("name", "Nombre", "line"),
                ("role", "Permiso", [("Administración", "admin"), ("Operación", "operator"), ("Consulta", "viewer")]),
                ("active", "Activo", "bool"),
                ("password", "Contraseña nueva", "password"),
            ],
            item or {"active": True, "role": "operator"},
            self,
            description="Mínimo 10 caracteres. Al editar, deja la contraseña vacía para conservarla.",
        )
        if form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if item:
                p["id"] = item["id"]
            self.submit("admin.update" if item else "admin.create", p, self.versions(("admin", item)))

    def buildings_dialog(self):
        options = [("Nuevo edificio", None)] + [
            (b["code"] + " · " + b["name"], b["id"]) for b in self.data["buildings"]
        ]
        select = Form("Edificios", [("id", "Selecciona", options)], parent=self)
        if select.exec() != QDialog.DialogCode.Accepted:
            return
        building = self.lookup("buildings", select.values()["id"])
        form = Form("Edificio", [("code", "Código", "line"), ("name", "Nombre", "line")], building, parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if building:
                p["id"] = building["id"]
            self.submit("building.update" if building else "building.create", p, self.versions(("building", building)))

    def backup(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar copia de seguridad",
            "samtec-lockers.dump" if self.config["mode"] != "demo" else "samtec-lockers.sqlite3",
            "Copia de seguridad (*)",
        )
        if not filename:
            return
        try:
            self.statusBar().showMessage("Creando copia de seguridad…")
            r = httpx.post(
                self.config["url"] + "/backup",
                headers={"Authorization": "Bearer " + self.session["token"]},
                timeout=130,
                trust_env=False,
            )
            r.raise_for_status()
            Path(filename).write_bytes(r.content)
            info(
                self,
                "Copia de seguridad guardada. Consérvala en una ubicación aprobada y prueba su restauración periódicamente.",
            )
        except (httpx.HTTPError, OSError):
            info(self, "No se pudo crear o guardar la copia de seguridad.")

    def template_csv(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Plantilla de empleados", "plantilla-empleados.csv", "CSV (*.csv)"
        )
        if filename:
            with open(filename, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(
                    [
                        "employee_number",
                        "first_name",
                        "surname",
                        "second_surname",
                        "email",
                        "department",
                        "shift",
                        "notes",
                    ]
                )

    def import_employees(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Importar empleados", "", "CSV (*.csv)")
        if not filename:
            return
        try:
            with open(filename, encoding="utf-8-sig", newline="") as file:
                sample = file.read(4096)
                file.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;")
                except csv.Error:
                    dialect = csv.excel
                rows = list(csv.DictReader(file, dialect=dialect))
            if not rows or len(rows) > 1000:
                raise ValueError("Importa de 1 a 1000 empleados por archivo.")
            seen = {e["employee_number"] for e in self.data["employees"]}
            for index, row in enumerate(rows, 2):
                if any(not (row.get(key) or "").strip() for key in ("employee_number", "first_name", "surname")):
                    raise ValueError(f"Fila {index}: faltan identificación, nombre o primer apellido.")
                number = row["employee_number"].strip()
                if number in seen:
                    raise ValueError(f"Fila {index}: ID duplicado {number}. La importación agrega empleados nuevos.")
                seen.add(number)
            preview = QDialog(self)
            preview.setWindowTitle("Vista previa de importación")
            preview.resize(850, 500)
            layout = QVBoxLayout(preview)
            layout.addWidget(
                QLabel(f"{len(rows)} empleados nuevos. Cada alta se confirmará por separado en Solicitudes.")
            )
            table = self.table(layout, ["ID", "Nombre", "Apellido", "Correo"])
            self.fill(
                table,
                [
                    (str(i), [r.get(k, "") for k in ("employee_number", "first_name", "surname", "email")])
                    for i, r in enumerate(rows)
                ],
            )
            self.button(layout, "Importar estos registros", preview.accept)
            self.button(layout, "Cancelar", preview.reject)
            if preview.exec() == QDialog.DialogCode.Accepted:
                for row in rows:
                    payload = {
                        k: (row.get(k) or "").strip()
                        for k in (
                            "employee_number",
                            "first_name",
                            "surname",
                            "second_surname",
                            "email",
                            "department",
                            "shift",
                            "notes",
                        )
                    }
                    payload["active"] = True
                    self.store.enqueue(self.session["actor"]["id"], "employee.create", payload, {})
                self.refresh_queue()
                self.sync()
        except (OSError, ValueError, csv.Error) as exc:
            info(self, str(exc))

    def export(self, kind):
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar", f"samtec-{kind}.csv", "CSV (*.csv)")
        if not filename:
            return
        rows = copy.deepcopy(self.data[kind])
        if not rows:
            info(self, "No hay registros para exportar.")
            return
        if kind == "lockers":
            for row in rows:
                row["code"] = self.locker_code(row)
                row["state"] = STATES[self.locker_state(row)]
                assignment = self.assignment_for(locker_id=row["id"])
                employee = self.lookup("employees", assignment["employee_id"]) if assignment else None
                row["employee_number"] = employee["employee_number"] if employee else ""
                row["employee_name"] = full_name(employee) if employee else ""
        try:
            with open(filename, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=list(rows[0]))
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            k: csv_safe(json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                            for k, v in row.items()
                        }
                    )
            info(self, "Archivo exportado.")
        except OSError:
            info(self, "No se pudo guardar el archivo. Revisa si está abierto en otra aplicación.")

    def refresh_employees(self):
        query = self.employee_search.text().casefold()
        rows = []
        for e in self.data["employees"]:
            status = self.employee_status.currentData()
            if (status == "active" and not e["active"]) or (status == "inactive" and e["active"]):
                continue
            assignment = self.assignment_for(employee_id=e["id"])
            locker = self.lookup("lockers", assignment["locker_id"]) if assignment else None
            values = [
                e["employee_number"],
                full_name(e),
                e["email"],
                e["department"],
                e["shift"],
                "Activo" if e["active"] else "Inactivo",
                self.locker_code(locker) if locker else "—",
            ]
            if query in " ".join(values).casefold():
                rows.append((e["id"], values))
        self.fill(self.employees, rows)

    def refresh_inventory(self):
        query = self.locker_search.text().casefold()
        state = self.inventory_filter.currentData()
        rows = []
        for locker in self.data["lockers"]:
            status = self.locker_state(locker)
            if state and state != status:
                continue
            assignment = self.assignment_for(locker_id=locker["id"])
            employee = self.lookup("employees", assignment["employee_id"]) if assignment else None
            values = [
                locker["number"],
                self.locker_code(locker),
                STATES[status],
                full_name(employee) if employee else "—",
                f"{locker['row'] + 1} / {locker['column'] + 1}",
            ]
            if query in " ".join(values).casefold():
                rows.append((locker["id"], values))
        self.fill(self.inventory, rows)

    def refresh_queue(self):
        queue = self.store.queue(self.session["actor"]["id"])
        self.fill(
            self.queue_table,
            [
                (
                    q["id"],
                    [
                        local_date(q["created_at"]),
                        ACTIONS.get(q["command"]["action"], q["command"]["action"]),
                        q["status"].replace("_", " "),
                        q["attempts"],
                        q["message"],
                    ],
                )
                for q in reversed(queue)
            ],
        )

    def audit_rows(self):
        rows = []
        for a in self.data["audit"]:
            admin = self.lookup("admins", a["actor_id"])
            target = a["after"]
            label = (
                target.get("employee_number") or target.get("number") or target.get("label") or target.get("name") or ""
            )
            if target.get("employee_id"):
                person = self.lookup("employees", target["employee_id"])
                locker = self.lookup("lockers", target["locker_id"])
                label = full_name(person or {}) + " · " + (locker["number"] if locker else "")
            rows.append(
                (
                    a["id"],
                    [
                        local_date(a["at"]),
                        ACTIONS.get(a["action"], a["action"]),
                        admin["name"] if admin else "Administrador",
                        label,
                        a["reason"],
                    ],
                )
            )
        return rows

    def refresh_history(self):
        query = self.audit_search.text().casefold()
        rows = self.audit_rows()
        self.fill(self.audit_table, [(id, v) for id, v in rows if query in " ".join(v).casefold()])
        self.fill(self.recent, [(id, v[:3]) for id, v in rows[:12]])

    def refresh(self):
        self.indexes = {
            key: {item["id"]: item for item in value} for key, value in self.data.items() if isinstance(value, list)
        }
        self.current_by_employee = {a["employee_id"]: a for a in self.data["assignments"] if a["ended_at"] is None}
        self.current_by_locker = {a["locker_id"]: a for a in self.data["assignments"] if a["ended_at"] is None}
        self.identity.setText(
            self.session["actor"]["name"]
            + "  ·  "
            + {"admin": "Administración", "operator": "Operación", "viewer": "Consulta"}.get(
                self.session["actor"]["role"], ""
            )
        )
        counts = {key: 0 for key in STATES}
        for locker in self.data["lockers"]:
            counts[self.locker_state(locker)] += 1
        labels = [
            f"{len(self.data['lockers'])}\nCasilleros",
            f"{counts['utilizable']}\nDisponibles",
            f"{counts['ocupado']}\nAsignados",
            f"{counts['pendiente']}\nPor verificar",
        ]
        for widget, label in zip(self.metrics, labels):
            widget.setText(label)
        pending = sum(q["status"] != "confirmada" for q in self.store.queue(self.session["actor"]["id"]))
        self.summary.setText(
            f"{len(self.data['employees'])} empleados · {len(self.data['blocks'])} bloques · {counts['mantenimiento']} en mantenimiento · {pending} solicitudes sin confirmar en tu cuenta.\nPrimero registra el inventario físico. Los contornos iniciales y los nombres de edificios deben verificarse en sitio."
        )
        self.refresh_employees()
        self.refresh_inventory()
        self.refresh_queue()
        self.refresh_history()
        self.refresh_cuts()
        self.fill(
            self.admin_table,
            [
                (
                    a["id"],
                    [
                        a["username"],
                        a["name"],
                        {"admin": "Administración", "operator": "Operación", "viewer": "Consulta"}[a["role"]],
                        "Activo" if a["active"] else "Inactivo",
                    ],
                )
                for a in self.data["admins"]
            ],
        )
        if not self.map.editing:
            current = self.plan_combo.currentData()
            self.plan_combo.blockSignals(True)
            self.plan_combo.clear()
            for p in self.data["plans"]:
                self.plan_combo.addItem(p["name"], p["id"])
            idx = self.plan_combo.findData(current)
            if idx >= 0:
                self.plan_combo.setCurrentIndex(idx)
            self.plan_combo.blockSignals(False)
            self.map.render(self.data, self.plan_combo.currentData())
            if self.map.transform().m11() == 1:
                self.map.fit()

    def closeEvent(self, event):
        self.timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            if not self.worker.wait(10000):
                event.ignore()
                self.timer.start()
                return
        event.accept()
