"""Preferences window with categories and explicit apply/cancel semantics."""

import copy

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QStackedWidget,
    QWidget,
    QFormLayout,
    QScrollArea,
    QLabel,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QCheckBox,
    QTextEdit,
    QPushButton,
    QDialogButtonBox,
    QMessageBox,
)

from .preferences import DEFAULTS, SCALES, normalize_preferences


class SettingsDialog(QDialog):
    def __init__(self, values, buildings, save, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opciones de Samtec Lockers")
        self.resize(820, 610)
        self.setMinimumSize(650, 430)
        self.save = save
        self.committed = normalize_preferences(values)
        self.widgets = {}
        layout = QVBoxLayout(self)
        note = QLabel("Preferencias para tu cuenta en este equipo. Los registros existentes no cambian.")
        note.setWordWrap(True)
        layout.addWidget(note)
        body = QHBoxLayout()
        layout.addLayout(body, 1)
        self.categories = QListWidget()
        self.categories.setObjectName("nav")
        self.categories.setFixedWidth(205)
        self.pages = QStackedWidget()
        body.addWidget(self.categories)
        body.addWidget(self.pages, 1)
        self.categories.currentRowChanged.connect(self.pages.setCurrentIndex)

        form = self.page(
            "Apariencia",
            "Tamaño de la interfaz",
            "Ajusta el texto y los controles. El tamaño de los bloques respecto al mapa se conserva.",
        )
        self.combo(form, "ui_scale", "Tamaño", [(f"{s}%" + (" · normal" if s == 100 else ""), s) for s in SCALES])

        form = self.page(
            "Mapa",
            "Vista del mapa",
            "Puedes mostrar la imagen satelital o trabajar solo con contornos y bloques. "
            "Cambiar esta vista conserva el zoom, las posiciones y los movimientos sin guardar.",
        )
        self.combo(form, "satellite", "Fondo", [("Imagen satelital", True), ("Solo contornos y bloques", False)])

        form = self.page(
            "Bloques y filas",
            "Predeterminados para nuevos bloques",
            "Se rellenan al crear un bloque o una fila. Puedes cambiar cada valor en el formulario. "
            "El plano y la posición se toman del lugar donde estés trabajando.",
        )
        self.combo(
            form,
            "block.building_id",
            "Edificio",
            [("Primero disponible", "")] + [(b["name"], b["id"]) for b in buildings],
        )
        self.combo(form, "block.side", "Lado", [("Norte", "N"), ("Sur", "S"), ("Este", "E"), ("Oeste", "O")])
        self.combo(form, "block.location", "Ubicación", [("Exterior", "EXT"), ("Interior", "INT")])
        self.number(form, "block.rows", "Filas", 1, 12)
        self.number(form, "block.columns", "Columnas", 1, 12)
        self.number(form, "block.rotation", "Rotación de etiqueta", -360, 360, decimal=True)
        self.line(form, "block.prefix", "Prefijo del bloque", 40)
        self.number(form, "block.count", "Bloques por fila", 1, 200)

        form = self.page(
            "Empleados",
            "Predeterminados para nuevos empleados",
            "Se usan únicamente al crear una persona. El ID, nombre y correo se introducen "
            "individualmente; las fichas existentes conservan sus datos.",
        )
        self.line(form, "employee.department", "Departamento", 120)
        self.line(form, "employee.shift", "Turno", 80)
        active = QCheckBox("Activo al crear")
        self.add(form, "employee.active", "Estado", active)
        notes = QTextEdit()
        notes.setMaximumHeight(110)
        self.add(form, "employee.notes", "Notas iniciales", notes)

        form = self.page(
            "Microsoft y correo", "Microsoft y correo",
            "Abre los borradores en tu aplicación de correo. El acceso con Microsoft y el envío automático requieren habilitación por TI.",
        )
        method = QComboBox()
        method.addItem("Manual · abrir borrador en correo")
        method.addItem("Microsoft · pendiente de habilitación")
        method.setEnabled(False)
        form.addRow("Entrega de correo", method)
        automatic = QCheckBox("Enviar automáticamente al confirmar una asignación")
        automatic.setEnabled(False)
        automatic.setToolTip("Disponible cuando TI integre y autorice el envío con Microsoft.")
        form.addRow("Envío automático", automatic)
        form.addRow("Inicio con Microsoft", QLabel("Pendiente de habilitación por TI"))
        form.addRow("Estado actual", QLabel("La aplicación no envía correos automáticamente."))

        footer = QHBoxLayout()
        layout.addLayout(footer)
        restore = QPushButton("Restaurar valores iniciales")
        restore.clicked.connect(lambda: self.fill(copy.deepcopy(DEFAULTS)))
        footer.addWidget(restore)
        footer.addStretch()
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("primary", True)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.apply_button = self.buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.apply_button.setText("Aplicar")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.apply_button.clicked.connect(self.apply)
        footer.addWidget(self.buttons)
        for w in self.widgets.values():
            signal = (
                w.currentIndexChanged
                if isinstance(w, QComboBox)
                else w.valueChanged
                if isinstance(w, (QSpinBox, QDoubleSpinBox))
                else w.toggled
                if isinstance(w, QCheckBox)
                else w.textChanged
            )
            signal.connect(self.changed)
        self.fill(self.committed)
        self.categories.setCurrentRow(0)

    def page(self, name, title, description):
        self.categories.addItem(name)
        content = QWidget()
        layout = QVBoxLayout(content)
        heading = QLabel(title)
        heading.setObjectName("title")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        label = QLabel(description)
        label.setWordWrap(True)
        layout.addWidget(label)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.addLayout(form)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        self.pages.addWidget(scroll)
        return form

    def add(self, form, key, label, widget):
        self.widgets[key] = widget
        form.addRow(label, widget)

    def combo(self, form, key, label, choices):
        widget = QComboBox()
        for text, value in choices:
            widget.addItem(text, value)
        self.add(form, key, label, widget)

    def number(self, form, key, label, low, high, decimal=False):
        widget = QDoubleSpinBox() if decimal else QSpinBox()
        widget.setRange(low, high)
        if decimal:
            widget.setDecimals(2)
            widget.setSuffix("°")
        self.add(form, key, label, widget)

    def line(self, form, key, label, length):
        widget = QLineEdit()
        widget.setMaxLength(length)
        self.add(form, key, label, widget)

    def fill(self, values):
        for key, widget in self.widgets.items():
            path = key.split(".")
            value = values[path[0]][path[1]] if len(path) == 2 else values[path[0]]
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(max(0, widget.findData(value)))
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.setValue(value)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(value)
            else:
                widget.setText(value)
        self.changed()

    def values(self):
        result = {"block": {}, "employee": {}}
        for key, w in self.widgets.items():
            value = (
                w.currentData()
                if isinstance(w, QComboBox)
                else w.value()
                if isinstance(w, (QSpinBox, QDoubleSpinBox))
                else w.isChecked()
                if isinstance(w, QCheckBox)
                else w.toPlainText()
                if isinstance(w, QTextEdit)
                else w.text()
            )
            path = key.split(".")
            if len(path) == 2:
                result[path[0]][path[1]] = value
            else:
                result[key] = value
        return normalize_preferences(result)

    def changed(self, *args):
        self.apply_button.setEnabled(self.values() != self.committed)

    def apply(self):
        values = self.values()
        if values == self.committed:
            return True
        try:
            self.save(values)
        except Exception:
            QMessageBox.warning(
                self, "Opciones", "No se pudieron guardar las preferencias en este equipo. Inténtalo de nuevo."
            )
            return False
        self.committed = copy.deepcopy(values)
        self.changed()
        return True

    def accept(self):
        if self.apply():
            super().accept()
