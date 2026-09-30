from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
)


class Form(QDialog):
    def __init__(self, title, fields, values=None, parent=None, description=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.widgets = {}
        layout = QVBoxLayout(self)
        if description:
            label = QLabel(description)
            label.setWordWrap(True)
            layout.addWidget(label)
        form = QFormLayout()
        self.form_layout = form
        layout.addLayout(form)
        values = values or {}
        for key, label, kind in fields:
            value = values.get(key, "")
            if isinstance(kind, list):
                widget = QComboBox()
                for text, data in kind:
                    widget.addItem(text, data)
                idx = widget.findData(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                if key in ("employee_id", "locker_id"):
                    from PySide6.QtCore import Qt
                    from PySide6.QtWidgets import QCompleter

                    widget.setEditable(True)
                    widget.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
                    widget.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                    widget.completer().setFilterMode(Qt.MatchFlag.MatchContains)
                    widget.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            elif kind == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(value))
            elif kind == "int":
                widget = QSpinBox()
                widget.setRange(1, 12)
                widget.setValue(int(value or 4))
            elif kind == "float":
                widget = QDoubleSpinBox()
                widget.setRange(-360, 1000)
                widget.setValue(float(value or 0))
            elif kind == "text":
                widget = QTextEdit(str(value))
                widget.setMaximumHeight(110)
            else:
                widget = QLineEdit(str(value))
                widget.setMaxLength(10000 if key == "numbers" else 500)
                if kind == "password":
                    widget.setEchoMode(QLineEdit.EchoMode.Password)
            self.widgets[key] = widget
            form.addRow(label, widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Guardar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        values = {}
        for key, w in self.widgets.items():
            if isinstance(w, QComboBox):
                value = (
                    w.currentData() if not w.isEditable() or w.currentText() == w.itemText(w.currentIndex()) else None
                )
            elif isinstance(w, QCheckBox):
                value = w.isChecked()
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                value = w.value()
            elif isinstance(w, QTextEdit):
                value = w.toPlainText()
            else:
                value = w.text()
            values[key] = value
        return values


def info(parent, text):
    QMessageBox.information(parent, "Samtec Lockers", text)


def confirm(parent, text):
    return (
        QMessageBox.question(parent, "Confirmar", text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        == QMessageBox.StandardButton.Yes
    )
