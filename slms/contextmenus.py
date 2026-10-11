"""Context actions use the clicked record ID, including after sorting or refresh."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu, QPushButton

from .forms import info
from .tableview import checked_ids, mark_rows


class ContextMenus:
    def actions_button(self, layout, actions, label="Más acciones"):
        button = QPushButton(label)
        menu = QMenu(button)

        def populate():
            menu.clear()
            for title, callback, permission in actions:
                action = menu.addAction(title)
                action.setEnabled(self.allowed(permission))
                action.triggered.connect(lambda checked=False, fn=callback: fn())

        menu.aboutToShow.connect(populate)
        button.setMenu(menu)
        layout.addWidget(button)
        return button

    def allowed(self, permission):
        role = self.session["actor"]["role"]
        return permission is None or role == "admin" or (permission == "editor" and role == "operator")

    def on_record(self, table, key, callback):
        # The table may have refreshed while its menu was open.
        for row in range(table.rowCount()):
            if table.item(row, 0).data(Qt.ItemDataRole.UserRole) == key:
                table.setCurrentCell(row, 0)
                table.selectRow(row)
                callback()
                return
        info(self, "El registro ya no aparece en esta lista. Revisa los filtros o sincroniza.")

    def show_table_menu(self, table, point):
        index = table.indexAt(point)
        if not index.isValid():
            return
        menu = self.table_menu(table, index.row(), index.column())
        menu.exec(table.viewport().mapToGlobal(point))
        menu.deleteLater()

    def table_menu(self, table, row, column):
        table.setCurrentCell(row, column)
        table.selectRow(row)
        key = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        menu = QMenu(table)

        def add(title, fn, permission=None, enabled=True):
            action = menu.addAction(title)
            action.setEnabled(enabled and self.allowed(permission))
            action.triggered.connect(lambda checked=False: self.on_record(table, key, fn))

        if table is getattr(self, "employees", None):
            employee = self.lookup("employees", key)
            assigned = self.assignment_for(employee_id=key)
            add("Editar empleado", lambda: self.employee_form(True), "editor")
            add(
                "Asignar / reasignar casillero",
                self.employee_assignment,
                "editor",
                bool(employee and employee["active"]),
            )
            add("Liberar casillero", self.employee_release, "editor", bool(assigned))
            add("Dar de baja y liberar", self.deactivate_employee, "editor", bool(employee and employee["active"]))
        elif table is getattr(self, "inventory", None):
            locker = self.lookup("lockers", key)
            block = self.lookup("blocks", locker["block_id"])
            assigned = self.assignment_for(locker_id=key)
            add("Abrir / editar casillero", lambda: self.locker_dialog(key))
            add(
                "Asignar casillero",
                lambda: self.choose_person(locker),
                "editor",
                not assigned and locker["condition"] == "utilizable",
            )
            add("Liberar casillero", lambda: self.release(assigned), "editor", bool(assigned))
            menu.addSeparator()
            add("Ver casilleros del bloque", lambda: self.open_block(block["id"]))
            add("Ver asignaciones del bloque", lambda: self.block_assignments(block["id"]))
            add("Editar bloque", lambda: self.block_form(block), "admin")
            add("Eliminar casillero", lambda: self.delete_inventory("locker", locker), "admin")
            add("Eliminar bloque completo", lambda: self.delete_inventory("block", block), "admin")
        elif table is getattr(self, "queue_table", None):
            item = next((q for q in self.store.queue(self.session["actor"]["id"]) if q["id"] == key), {})
            add("Ver detalle de solicitud", self.queue_detail)
            add("Resolver conflicto…", self.resolve_conflict, "editor", item.get("status") in ("conflicto", "rechazada"))
            add("Reintentar solicitud", self.retry, "editor", item.get("status") == "error_temporal")
            add("Iniciar sesión para enviar", self.relogin, enabled=item.get("status") == "requiere_sesion")
        elif table is getattr(self, "admin_table", None):
            add("Editar cuenta / permisos", lambda: self.admin_form(True), "admin")
        elif table in (getattr(self, "audit_table", None), getattr(self, "recent", None)):
            add("Ver detalle del cambio", lambda: self.show_audit(key))
        for title, callback, permission in getattr(table, "context_actions", lambda key: [])(key):
            add(title, callback, permission)
        if menu.actions():
            menu.addSeparator()
        menu.addAction("Marcar todas las filas visibles").triggered.connect(lambda: mark_rows(table, True))
        menu.addAction("Desmarcar todas las filas visibles").triggered.connect(lambda: mark_rows(table, False))
        copy_marked = menu.addAction("Copiar filas marcadas")
        copy_marked.setEnabled(bool(checked_ids(table)))
        def copy_checked():
            checked = set(checked_ids(table))
            lines = ["\t".join(table.item(r, c).text() for c in range(table.columnCount()))
                     for r in range(table.rowCount()) if table.item(r, 0).data(Qt.ItemDataRole.UserRole) in checked]
            QApplication.clipboard().setText("\n".join(lines))
        copy_marked.triggered.connect(copy_checked)
        menu.addSeparator()
        values = [table.item(row, c).text() if table.item(row, c) else "" for c in range(table.columnCount())]
        detail = "\n".join(f"{table.horizontalHeaderItem(c).text()}: {value}" for c, value in enumerate(values))
        # These are a snapshot of visible text, so copying remains valid after a refresh.
        for title, fn in [
            ("Ver datos de la fila", lambda: info(self, detail)),
            ("Copiar valor", lambda: QApplication.clipboard().setText(values[column])),
            ("Copiar fila", lambda: QApplication.clipboard().setText("\t".join(values))),
        ]:
            menu.addAction(title).triggered.connect(lambda checked=False, callback=fn: callback())
        return menu

    def add_map_move_actions(self, menu):
        # Fresh menu actions avoid Qt transferring/deleting the map's shortcut
        # actions when a dynamic menu is cleared or a context menu is destroyed.
        for source in (self.map.undo_action, self.map.redo_action):
            action = menu.addAction(source.text() + "\t" + source.shortcut().toString())
            action.setEnabled(self.allowed("admin") and source.isEnabled())
            action.triggered.connect(lambda checked=False, source=source: source.trigger())

    def map_menu(self, block_id, position):
        menu = QMenu(self.map)

        def add(title, callback, permission=None):
            action = menu.addAction(title)
            action.setEnabled(self.allowed(permission))
            action.triggered.connect(lambda checked=False: callback())

        block = self.lookup("blocks", block_id) if block_id else None
        if block:
            add("Ver casilleros del bloque", lambda: self.open_block(block_id))
            add("Ver asignaciones del bloque", lambda: self.block_assignments(block_id))
            menu.addSeparator()
            add("Editar bloque", lambda: self.block_form(self.lookup("blocks", block_id)), "admin")
            add("Verificar casilleros vacíos", lambda: self.verify_block(self.lookup("blocks", block_id)), "editor")
            add("Eliminar bloque", lambda: self.delete_inventory("block", self.lookup("blocks", block_id)), "admin")
        elif self.map.plan:
            plan_id = self.map.plan["id"]
            add("Nuevo bloque aquí", lambda: self.block_form(position=position, plan_id=plan_id), "admin")
            add("Crear fila desde aquí", lambda: self.start_block_row(position), "admin")
        menu.addSeparator()
        add("Ajustar vista", self.map.fit)
        menu.addSeparator()
        self.add_map_move_actions(menu)
        return menu

    def show_map_menu(self, block_id, position, global_position):
        menu = self.map_menu(block_id, position)
        menu.exec(global_position)
        menu.deleteLater()
