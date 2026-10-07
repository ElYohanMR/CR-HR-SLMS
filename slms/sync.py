import time
import httpx
from PySide6.QtCore import QThread, Signal


class SyncWorker(QThread):
    completed = Signal(object)

    def __init__(self, store, url, session):
        super().__init__()
        self.store, self.url, self.session = store, url, session

    def run(self):
        changes = []
        try:
            with httpx.Client(
                base_url=self.url,
                headers={"Authorization": "Bearer " + self.session["token"]},
                timeout=8,
                trust_env=False,
            ) as client:
                identity = client.get("/me")
                if identity.status_code == 401:
                    self.store.require_session(self.session["actor"]["id"])
                    self.completed.emit(
                        {
                            "state": "sesion",
                            "message": "Sesión vencida. Las solicitudes no se enviaron. Inicia sesión para enviarlas automáticamente.",
                        }
                    )
                    return
                identity.raise_for_status()
                tasks = self.store.queue(self.session["actor"]["id"])
                statuses = {x["id"]: x["status"] for x in tasks}
                for task in tasks:
                    if self.isInterruptionRequested():
                        return
                    if task["status"] not in ("pendiente", "requiere_sesion") or task["next_attempt"] > time.time():
                        continue
                    dependency = task["dependency"]
                    if dependency and statuses.get(dependency) != "confirmada":
                        continue
                    try:
                        response = client.post("/commands", json=task["command"])
                        if response.status_code == 401:
                            self.store.require_session(self.session["actor"]["id"])
                            self.store.result(
                                task["id"], "requiere_sesion", "Inicia sesión con la cuenta que creó esta solicitud."
                            )
                            self.completed.emit({"state": "sesion", "message": "Se necesita iniciar sesión."})
                            return
                        if response.status_code >= 500 or response.status_code == 429:
                            response.raise_for_status()
                        if response.status_code >= 400:
                            result = {
                                "status": "rechazada",
                                "message": str(response.json().get("detail", "Solicitud inválida.")),
                            }
                        else:
                            result = response.json()
                        self.store.result(task["id"], result["status"], result["message"], attempt=True)
                        statuses[task["id"]] = result["status"]
                        changes.append(result)
                    except (httpx.HTTPError, ValueError):
                        attempt = task["attempts"] + 1
                        self.store.result(
                            task["id"],
                            "error_temporal" if attempt >= 8 else "pendiente",
                            "No se recibió confirmación; el reintento conserva el identificador original.",
                            attempt=True,
                            next_attempt=time.time() + min(300, 2**attempt),
                        )
                        raise
                response = client.get("/snapshot")
                response.raise_for_status()
                snapshot = response.json()
                self.store.put("snapshot", snapshot)
                self.completed.emit(
                    {"state": "online", "snapshot": snapshot, "actor": identity.json(), "changes": changes}
                )
        except (httpx.HTTPError, ValueError):
            self.completed.emit(
                {"state": "offline", "message": "Sin conexión. Las solicitudes se guardan pendientes en este equipo."}
            )
        except Exception:
            self.completed.emit(
                {
                    "state": "error",
                    "message": "No se pudo leer o guardar la cola local. Revisa espacio y permisos antes de continuar.",
                }
            )
