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
    QWidget,
    QScrollArea,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from .theme import brand_header


class FormScroll(QScrollArea):
    def sizeHint(self):
        return self.widget().sizeHint()


class Form(QDialog):
    def __init__(self, title, fields, values=None, parent=None, description="", accept_label="Guardar"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(560)
        self.setMaximumHeight(max(400, self.screen().availableGeometry().height() - 60))
        self.widgets = {}
        self.sections = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header, _ = brand_header(self)
        layout.addWidget(header)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(28, 22, 28, 24)
        body.setSpacing(14)
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        heading = QLabel(title)
        heading.setObjectName("title")
        body.addWidget(heading)
        if description:
            label = QLabel(description)
            label.setWordWrap(True)
            label.setObjectName("subtitle")
            label.setMaximumWidth(650)
            body.addWidget(label)
        form = QFormLayout()
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form_layout = form
        body.addLayout(form)
        values = values or {}
        for key, label, kind in fields:
            if kind == "section":
                section = QLabel(label)
                section.setObjectName("sectionTitle")
                self.sections[key] = section
                form.addRow(section)
                continue
            value = values.get(key, "")
            if isinstance(kind, list):
                widget = QComboBox()
                for text, data in kind:
                    widget.addItem(text, data)
                idx = widget.findData(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                if key in ("employee_id", "locker_id"):
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
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(accept_label)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("primary", True)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        scroll = FormScroll()
        scroll.setObjectName("formScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        footer = QWidget()
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(28, 14, 28, 20)
        footer_layout.addWidget(buttons)
        layout.addWidget(footer)
        self.resize(self.sizeHint().width(), min(self.sizeHint().height(), self.maximumHeight()))

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
