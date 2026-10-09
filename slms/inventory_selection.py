"""Explicit previews for actions on checkbox selections."""

from PySide6.QtWidgets import QDialog
from .forms import Form, info
from .tableview import checked_ids


class InventorySelection:
    def initial_admin(self):
        actor = self.lookup("admins", self.session["actor"]["id"]) or self.session["actor"]
        return actor.get("is_initial", False) and actor["role"] == "admin" and actor.get("active", True)

    def archived_batch(self, table, items, dialog, purge=False):
        if not self.allowed("admin") or (purge and not self.initial_admin()):
            return
        if not self.data.get("features", {}).get("inventory_batch"):
            info(
                self,
                "Esta operación requiere el servidor actualizado. Reinicia Windows, abre la aplicación y sincroniza.",
            )
            return
        keys = checked_ids(table)
        if not keys:
            info(self, "Marca al menos una casilla de la lista.")
            return
        selected = [items[key] for key in keys if key in items]
        versions, affected = {}, {}
        for kind, item in selected:
            versions.update(self.versions((kind, item)))
            if kind == "locker":
                affected[item["id"]] = item
            else:
                for locker in self.data.get("archived_lockers", []):
                    if locker["block_id"] == item["id"] and (purge or locker["deleted_at"] == item["deleted_at"]):
                        affected[locker["id"]] = locker
                        versions.update(self.versions(("locker", locker)))
        if purge:
            ids = set(affected)
            if any(a["locker_id"] in ids for a in self.data["assignments"]) or any(
                ids.intersection(r["locker_ids"]) for r in self.data.get("inspection_rounds", [])
            ):
                info(
                    self,
                    "La selección incluye casilleros con asignaciones o revisiones registradas. "
                    "Se conservan como eliminados; no se borró ningún elemento.",
                )
                return
        labels = ["Bloque " + x["label"] if kind == "block" else "Casillero " + x["number"] for kind, x in selected]
        fields = [("selection", "Elementos marcados", "text"), ("reason", "Motivo", "text")]
        if purge:
            fields.append(("confirmation", "Escribe ELIMINAR", "line"))
        description = f"{len(selected)} filas marcadas; incluye {len(affected)} casilleros diferentes. " + (
            "Se borrarán definitivamente y sus códigos quedarán libres. No se pueden restaurar. "
            "El registro de auditoría de la eliminación se conserva."
            if purge
            else "Se restauran en una sola operación. Los casilleros quedan pendientes de verificación."
        )
        form = Form(
            "Eliminar definitivamente" if purge else "Restaurar marcados",
            fields,
            {"selection": "\n".join(labels)},
            dialog,
            description=description,
            accept_label="Eliminar definitivamente" if purge else "Restaurar",
        )
        form.widgets["selection"].setReadOnly(True)
        form.widgets["selection"].setPlainText("\n".join(labels))
        if form.exec() != QDialog.DialogCode.Accepted:
            return
        values = form.values()
        if not values["reason"].strip() or (purge and values["confirmation"].strip() != "ELIMINAR"):
            info(self, "Escribe el motivo" + (" y la confirmación ELIMINAR." if purge else "."))
            return
        payload = {"items": [{"kind": kind, "id": x["id"]} for kind, x in selected], "reason": values["reason"].strip()}
        if purge:
            payload["confirmation"] = "ELIMINAR"
        request = self.submit("inventory.purge" if purge else "inventory.restore_many", payload, versions)
        if request:
            dialog.accept()
