"""Exercise settings in the executable's isolated demo profile."""

import copy
from PySide6.QtWidgets import QApplication
from .config import home
from .settings_dialog import SettingsDialog


def capture_preferences(window):
    original = copy.deepcopy(window.preferences)
    original_data = copy.deepcopy(window.data)
    dialog = SettingsDialog(window.preferences, window.data["buildings"], window.save_preferences, window)
    dialog.show()
    for index, name in enumerate(("apariencia", "mapa", "bloques", "empleados")):
        dialog.categories.setCurrentRow(index)
        QApplication.processEvents()
        dialog.grab().save(str(home() / f"opciones-{name}.png"))
    dialog.widgets["ui_scale"].setCurrentIndex(dialog.widgets["ui_scale"].findData(125))
    dialog.widgets["satellite"].setCurrentIndex(1)
    dialog.widgets["block.rotation"].setValue(12)
    dialog.widgets["employee.shift"].setText("T3")
    assert dialog.apply()
    window.load_preferences()
    assert window.preferences["block"]["rotation"] == 12
    assert window.preferences["employee"]["shift"] == "T3"
    assert not window.map.background_item.isVisible()
    assert window.data == original_data
    dialog.categories.setCurrentRow(0)
    QApplication.processEvents()
    dialog.grab().save(str(home() / "opciones-125.png"))
    dialog.close()
    window.nav.setCurrentRow(1)
    window.map.fit()
    QApplication.processEvents()
    window.grab().save(str(home() / "mapa-contornos.png"))
    window.save_preferences(original)
    assert window.preferences == original
