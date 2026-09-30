from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLabel, QDialogButtonBox, QScrollArea
from slms.setup import setup_form
from slms.theme import apply_theme


def test_setup_readable_after_dark_windows_palette(qtbot, qapp):
    original_palette, original_style, original_font = qapp.palette(), qapp.styleSheet(), qapp.font()
    try:
        dark = QPalette()
        dark.setColor(QPalette.ColorRole.WindowText, QColor("white"))
        dark.setColor(QPalette.ColorRole.Text, QColor("white"))
        dark.setColor(QPalette.ColorRole.Window, QColor("#222222"))
        qapp.setPalette(dark)
        apply_theme(qapp)
        form = setup_form()
        qtbot.addWidget(form)
        form.show()
        qtbot.waitExposed(form)
        label = form.form_layout.labelForField(form.widgets["db_password"])
        assert isinstance(label, QLabel)
        assert label.palette().color(QPalette.ColorRole.WindowText).lightness() < 100
        assert form.widgets["db_password"].palette().color(QPalette.ColorRole.Base).lightness() > 230
        assert form.widgets["db_password"].isVisible()
        assert form.widgets["password"].isVisible()
        form.resize(740, 480)
        qapp.processEvents()
        save = form.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        assert save.mapTo(form, QPoint(0, save.height())).y() <= form.height()
        scroll = form.findChild(QScrollArea)
        assert scroll.verticalScrollBar().maximum() > 0
        scroll.ensureWidgetVisible(form.widgets["password"])
        assert scroll.verticalScrollBar().value() > 0
        form.widgets["mode"].setCurrentIndex(1)
        assert form.widgets["url"].isVisible()
        assert not form.widgets["db_password"].isVisible()
        assert not form.sections["account_section"].isVisible()
        form.widgets["mode"].setCurrentIndex(2)
        assert form.widgets["password"].isVisible()
        assert not form.widgets["url"].isVisible()
        form.close()
    finally:
        qapp.setStyleSheet(original_style)
        qapp.setPalette(original_palette)
        qapp.setFont(original_font)
