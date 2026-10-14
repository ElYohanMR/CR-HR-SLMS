"""Reserved integration surface. No Microsoft credentials are collected."""
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QLabel, QVBoxLayout
from .config import asset


def add_microsoft_login(form):
    row = QVBoxLayout()
    button = QPushButton("Iniciar con Microsoft")
    button.setObjectName("microsoftSignIn")
    icon = QIcon(str(asset("microsoft.svg")))
    icon.addPixmap(icon.pixmap(QSize(21, 21)), QIcon.Mode.Disabled)
    button.setIcon(icon)
    button.setIconSize(QSize(21, 21))
    button.setMinimumHeight(41)
    button.setStyleSheet("QPushButton { background: white; color: #5e5e5e; border: 1px solid #8c8c8c; font-family: 'Segoe UI'; padding: 8px 12px; }")
    button.setEnabled(False)
    button.setToolTip("El acceso con tu cuenta de trabajo estará disponible cuando TI habilite la integración.")
    row.addWidget(button)
    note = QLabel("Cuenta de trabajo · Pendiente de habilitación por TI")
    note.setWordWrap(True)
    row.addWidget(note)
    form.form_layout.addRow(row)
    return button
