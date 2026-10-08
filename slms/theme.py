"""Shared Samtec-inspired desktop theme, independent of the Windows color mode."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from .config import asset


STYLE = """
QWidget { font-family:"Montserrat", "Segoe UI"; font-size:13px; color:#333333; }
QMainWindow, QDialog { background:#f5f5f5; }
QLabel { color:#333333; background:transparent; }
QLabel#title { font-size:25px; font-weight:600; color:#333333; }
QLabel#subtitle { color:#606060; padding-bottom:8px; }
QFrame#brandHeader { background:#444444; border-bottom:3px solid #fa661b; }
QFrame#brandHeader QLabel { color:white; }
QLabel#brandTitle { font-size:22px; font-weight:600; }
QLabel#brandCaption { color:#e2e2e2; font-size:11px; }
QLabel#brandDivider { color:#999999; font-size:32px; padding:0 8px; }
QFrame#brandHeader QPushButton { background:#444444; color:white; border:1px solid #888888; }
QFrame#brandHeader QPushButton:hover { background:#555555; border-color:#fa661b; }
QLabel#metric { background:white; border:1px solid #dddddd; border-top:3px solid #fa661b; border-radius:3px; padding:22px; font-size:23px; font-weight:600; }
QLabel#banner { padding:12px; background:white; border:1px solid #dddddd; border-left:4px solid #fa661b; }
QLabel#sectionTitle { font-size:13px; font-weight:600; color:#333333; padding:14px 0 5px 0; border-bottom:1px solid #dddddd; }
QListWidget#nav { background:#444444; color:#eeeeee; border:0; border-radius:3px; padding:8px 0; font-size:13px; outline:0; }
QListWidget#nav::item { padding:16px 15px; border-left:3px solid transparent; }
QListWidget#nav::item:hover { background:#505050; }
QListWidget#nav::item:selected { background:#333333; border-left:3px solid #fa661b; color:white; font-weight:600; }
QPushButton { background:white; color:#333333; border:1px solid #bcbcbc; border-radius:3px; padding:9px 14px; font-weight:600; }
QPushButton:hover { background:#fff1e9; border-color:#fa661b; }
QPushButton[primary="true"] { background:#fa661b; color:#222222; border:1px solid #fa661b; }
QPushButton[primary="true"]:hover { background:#ff803e; border-color:#ff803e; }
QPushButton:checked { background:#333333; color:white; border-color:#333333; }
QPushButton:focus { border:2px solid #a7430b; padding:8px 13px; }
QPushButton:disabled { background:#e7e7e7; color:#767676; border-color:#d5d5d5; }
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTextEdit { background:white; color:#333333; border:1px solid #bcbcbc; padding:8px; border-radius:3px; selection-background-color:#ffddc9; selection-color:#222222; }
QLineEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus,QTextEdit:focus { border:1px solid #a7430b; }
QLineEdit { placeholder-text-color:#707070; }
QLineEdit:disabled,QComboBox:disabled,QTextEdit:disabled { background:#eeeeee; color:#767676; }
QComboBox QAbstractItemView { background:white; color:#333333; selection-background-color:#ffddc9; selection-color:#222222; }
QComboBox::drop-down { border:0; width:24px; }
QComboBox::down-arrow { image:url("@CHEVRON@"); width:12px; height:8px; }
QTableWidget { color:#333333; background:white; alternate-background-color:#f8f8f8; border:1px solid #dddddd; gridline-color:#eeeeee; selection-background-color:#ffddc9; selection-color:#222222; }
QHeaderView::section { background:#eeeeee; color:#444444; padding:10px; border:0; border-bottom:1px solid #dddddd; font-weight:600; }
QHeaderView::section:hover { background:#fff1e9; }
QHeaderView::up-arrow { image:url("@SORT_UP@"); width:12px; height:8px; }
QHeaderView::down-arrow { image:url("@SORT_DOWN@"); width:12px; height:8px; }
QTableWidget::item { padding:4px; }
QTabWidget::pane { background:white; border:1px solid #dddddd; }
QTabBar::tab { background:#eeeeee; color:#333333; padding:10px 15px; }
QTabBar::tab:selected { background:white; border-bottom:3px solid #fa661b; }
QStatusBar { background:#eeeeee; color:#555555; border-top:1px solid #dddddd; }
QToolTip { background:#333333; color:white; border:1px solid #555555; padding:6px; }
QMenu { background:white; color:#333333; border:1px solid #dddddd; }
QMenu::item:selected { background:#ffddc9; color:#222222; }
QMenu::item:disabled { color:#999999; }
QCheckBox { color:#333333; spacing:8px; }
QGroupBox { color:#333333; border:1px solid #dddddd; margin-top:15px; padding:10px; }
QScrollArea#formScroll { background:transparent; border:0; }
""".replace("@CHEVRON@", asset("chevron-down.svg").as_posix()).replace(
    "@SORT_UP@", asset("sort-up.svg").as_posix()
).replace("@SORT_DOWN@", asset("sort-down.svg").as_posix())


def apply_theme(app):
    # Fusion otherwise inherits white WindowText from a dark Windows palette.
    app.setStyle("Fusion")
    QFontDatabase.addApplicationFont(str(asset("Montserrat.ttf")))
    app.setFont(QFont("Montserrat", 10))
    palette = QPalette()
    colors = {
        "Window": "#f5f5f5",
        "WindowText": "#333333",
        "Base": "#ffffff",
        "AlternateBase": "#f8f8f8",
        "Text": "#333333",
        "Button": "#ffffff",
        "ButtonText": "#333333",
        "Highlight": "#ffddc9",
        "HighlightedText": "#222222",
        "ToolTipBase": "#333333",
        "ToolTipText": "#ffffff",
        "Link": "#a7430b",
        "LinkVisited": "#754520",
        "PlaceholderText": "#707070",
        "Light": "#ffffff",
        "Midlight": "#eeeeee",
        "Mid": "#bcbcbc",
        "Dark": "#666666",
        "Shadow": "#333333",
        "BrightText": "#ffffff",
    }
    for role, color in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#767676"))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)


def brand_header(parent=None):
    header = QFrame(parent)
    header.setObjectName("brandHeader")
    row = QHBoxLayout(header)
    row.setContentsMargins(24, 16, 24, 16)
    row.setSpacing(14)
    logo = QLabel()
    logo.setPixmap(
        QPixmap(str(asset("samtec-logo.png"))).scaled(
            136, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
    )
    logo.setAccessibleName("Samtec")
    row.addWidget(logo)
    divider = QLabel("|")
    divider.setObjectName("brandDivider")
    row.addWidget(divider)
    title = QLabel("LOCKERS")
    title.setObjectName("brandTitle")
    row.addWidget(title)
    row.addStretch()
    return header, row
