"""Restore the supplied building contours on a NEW SLMS server, through its API."""

import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import uuid

import httpx


def prepare(data, snapshot):
    if data.get("format") != "slms-map-contours-v1" or len(data.get("plans", [])) != 1:
        raise ValueError("Se requiere el archivo de contornos de esta entrega (un plano).")
    if any(
        snapshot.get(k)
        for k in ("blocks", "lockers", "archived_blocks", "archived_lockers", "employees", "assignments")
    ):
        raise ValueError("Solo se permite en una base nueva, antes de importar bloques o empleados.")
    item = data["plans"][0]
    matches = [p for p in snapshot["plans"] if p["name"] == item["name"]]
    if len(matches) != 1:
        raise ValueError("El plano de destino no existe o su nombre no es único.")
    plan = matches[0]
    digest = hashlib.sha256(base64.b64decode(plan["background"], validate=True)).hexdigest()
    if digest != item["background_sha256"]:
        raise ValueError("La imagen del plano no coincide con la distribución entregada.")
    buildings = {b["code"]: b["id"] for b in snapshot["buildings"]}
    polygons = [dict(building_id=buildings[p["building_code"]], points=p["points"]) for p in item["polygons"]]
    payload = dict(
        id=plan["id"],
        name=plan["name"],
        kind=item["kind"],
        floor=item["floor"],
        building_id=buildings[item["building_code"]] if item["building_code"] else None,
        polygons=polygons,
    )
    return dict(
        id=str(uuid.uuid4()),
        device_id="initial-map-import",
        client_at=datetime.now(timezone.utc).isoformat(),
        action="plan.update",
        payload=payload,
        versions={"plan:" + plan["id"]: plan["version"]},
    )


def main():
    parser = argparse.ArgumentParser(description="Contornos iniciales: ejecutar en el servidor ANTES del inventario.")
    parser.add_argument("archivo", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--apply", action="store_true", help="Aplicar; sin esta opción solo valida.")
    args = parser.parse_args()
    url = urlsplit(args.url)
    if (
        url.scheme != "http"
        or url.hostname not in ("localhost", "127.0.0.1", "::1")
        or url.username
        or url.password
        or url.path not in ("", "/")
        or url.query
        or url.fragment
    ):
        parser.error("Ejecuta localmente en el servidor con una URL HTTP de loopback.")
    data = json.loads(args.archivo.read_text(encoding="utf-8"))
    username = input("Usuario administrador inicial de SLMS: ").strip()
    password = getpass.getpass("Contraseña de SLMS: ")
    with httpx.Client(base_url=args.url.rstrip("/"), timeout=60, trust_env=False) as client:
        response = client.post("/login", json=dict(username=username, password=password))
        password = None
        response.raise_for_status()
        auth = response.json()
        client.headers["Authorization"] = "Bearer " + auth["token"]
        try:
            if not auth["actor"].get("is_initial"):
                raise ValueError("Inicia sesión con la cuenta administradora inicial.")
            response = client.get("/snapshot")
            response.raise_for_status()
            command = prepare(data, response.json())
            print("Validado: plano e imagen coinciden. Base sin bloques ni empleados.")
            if not args.apply:
                print("No se modificó el mapa. Repite con --apply para guardar los contornos.")
                return
            response = client.post("/commands", json=command)
            response.raise_for_status()
            result = response.json()
            if result.get("status") != "confirmada":
                raise ValueError(result.get("message", "La solicitud no fue confirmada."))
            print("Contornos confirmados. Ahora puedes importar el Excel de inventario desde SLMS.")
        finally:
            client.post("/logout")


if __name__ == "__main__":
    main()
