"""Local, per-account defaults. They never modify server records."""

import copy
import math

from .numbering import DEFAULT_FIRST, DEFAULT_SECOND, normalize_order

DEFAULTS = {
    "ui_scale": 100,
    "satellite": True,
    "block": {
        "building_id": "",
        "side": "N",
        "location": "EXT",
        "rows": 4,
        "columns": 3,
        "rotation": 10.0,
        "prefix": "N",
        "count": 4,
        "numbering_first": DEFAULT_FIRST,
        "numbering_second": DEFAULT_SECOND,
    },
    "employee": {"department": "", "shift": "", "active": True, "notes": ""},
}
SCALES = (90, 100, 110, 125, 150)


def normalize_preferences(raw):
    result = copy.deepcopy(DEFAULTS)
    if not isinstance(raw, dict):
        return result
    if type(raw.get("ui_scale")) is int and raw["ui_scale"] in SCALES:
        result["ui_scale"] = raw["ui_scale"]
    if type(raw.get("satellite")) is bool:
        result["satellite"] = raw["satellite"]
    for section in ("block", "employee"):
        values = raw.get(section)
        if not isinstance(values, dict):
            continue
        for key, default in result[section].items():
            value = values.get(key, default)
            if type(value) is not type(default) and not (key == "rotation" and type(value) in (int, float)):
                continue
            if key in ("rows", "columns") and not 1 <= value <= 12:
                continue
            if key == "count" and not 1 <= value <= 200:
                continue
            if key == "rotation" and (not math.isfinite(value) or not -360 <= value <= 360):
                continue
            if key == "side" and value not in ("N", "S", "E", "O"):
                continue
            if key == "location" and value not in ("EXT", "INT"):
                continue
            if isinstance(value, str):
                limit = {"building_id": 200, "department": 120, "shift": 80, "notes": 2000,
                         "prefix": 40, "side": 1, "location": 3,
                         "numbering_first": 20, "numbering_second": 20}[key]
                value = value[:limit].strip()
            result[section][key] = round(float(value), 2) if key == "rotation" else value
    block = result["block"]
    block["numbering_first"], block["numbering_second"] = normalize_order(
        block["numbering_first"], block["numbering_second"]
    )
    return result


class Preferences:
    def load_preferences(self):
        self.preferences = normalize_preferences(self.store.get("preferences:" + self.session["actor"]["id"]))

    def apply_preferences(self):
        from PySide6.QtWidgets import QTableWidget
        from .theme import scaled_style

        scale = self.preferences["ui_scale"]
        self.setStyleSheet(scaled_style(scale))
        self.nav.setFixedWidth(round(205 * scale / 100))
        for table in self.findChildren(QTableWidget):
            table.verticalHeader().setDefaultSectionSize(round(30 * scale / 100))
        self.map.set_satellite(self.preferences["satellite"])

    def save_preferences(self, values):
        values = normalize_preferences(values)
        self.store.put("preferences:" + self.session["actor"]["id"], values)
        self.preferences = values
        self.apply_preferences()

    def settings_dialog(self):
        from .settings_dialog import SettingsDialog

        SettingsDialog(self.preferences, self.data.get("buildings", []), self.save_preferences, self).exec()

    def new_block_defaults(self):
        values = dict(self.preferences["block"])
        if not any(b["id"] == values["building_id"] for b in self.data["buildings"]):
            values.pop("building_id", None)
        return values
