"""Audited workflow. Cutting a padlock never changes the locker assignment."""
import base64
import binascii
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import PureWindowsPath

from sqlalchemy import select
from .models import CutRequest, CutEvidence, Employee, Locker, Block, Building, Audit, now, record

STATUSES = {"solicitada": "Solicitada", "en_proceso": "En proceso",
            "finalizada": "Finalizada", "cancelada": "Cancelada"}
EVIDENCE = {"identidad": "Empleado con su tarjeta Samtec ID frente al casillero",
            "antes": "Candado antes del corte", "despues": "Candado después del corte"}
CHANNELS = {"teams": "Teams", "correo": "Correo electrónico", "otro": "Otro medio"}
MAX_PHOTO = 6_000_000


def validate_photo(content):
    """Decode safely with the same bounded image reader shipped with the desktop."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QImageReader
    if not content or len(content) > MAX_PHOTO:
        raise ValueError("La fotografía debe ocupar como máximo 6 MB.")
    buffer = QBuffer()
    buffer.setData(QByteArray(content))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    fmt = bytes(reader.format()).lower()
    size = reader.size()
    if fmt not in (b"png", b"jpeg", b"jpg") or not size.isValid() or size.width() * size.height() > 24_000_000:
        raise ValueError("Selecciona una fotografía JPG o PNG de hasta 24 megapíxeles.")
    if reader.read().isNull():
        raise ValueError("La fotografía está incompleta o no se puede leer.")
    return "image/png" if fmt == b"png" else "image/jpeg"


def apply_cut(db, actor, command):
    from .service import RuleError, required, get, check_version
    p, action, versions = command["payload"], command["action"], command["versions"]

    def field(key, length=200):
        if not isinstance(p.get(key), str):
            raise RuleError(f"Completa el campo {key}.")
        return required(p, key, length)

    if action == "cut.create":
        employee, locker = get(db, Employee, p.get("employee_id")), get(db, Locker, p.get("locker_id"))
        check_version(employee, versions, "employee")
        check_version(locker, versions, "locker")
        if not employee.active:
            raise RuleError("El empleado está inactivo. Revisa su ficha antes de crear la solicitud.")
        if db.scalar(select(CutRequest.id).where(CutRequest.locker_id == locker.id,
                                               CutRequest.status.in_(("solicitada", "en_proceso")))):
            raise RuleError("Este casillero ya tiene una solicitud de corte abierta.", "conflicto")
        block = get(db, Block, locker.block_id)
        building = get(db, Building, block.building_id)
        target = CutRequest(employee_id=employee.id, locker_id=locker.id, created_by=actor.id,
                            reference={"employee_number": employee.employee_number,
                                       "employee_name": " ".join(filter(None, [employee.first_name, employee.surname,
                                                                               employee.second_surname])),
                                       "locker_number": locker.number,
                                       "location": f"{building.code}-{block.location}-{block.label}-{locker.number}"})
        db.add(target)
        before = {}
    else:
        target = get(db, CutRequest, p.get("id"))
        check_version(target, versions, "cut_request")
        before = record(target)
        if target.status in ("finalizada", "cancelada"):
            raise RuleError("La solicitud está cerrada y conserva su historial.", "conflicto")
        target.version += 1
    if action in ("cut.create", "cut.update"):
        if action == "cut.update" and target.status != "solicitada":
            raise RuleError("Los datos iniciales solo se pueden editar mientras está Solicitada.")
        target.supervisor, target.reason = field("supervisor"), field("reason", 2000)
        if not isinstance(p.get("channel"), str) or p["channel"] not in CHANNELS:
            raise RuleError("Selecciona cómo se recibió la solicitud.")
        target.channel = p["channel"]
    elif action == "cut.assign":
        target.assignee = field("assignee")
        # Explain changes of responsible person in the immutable audit trail.
        if target.status == "en_proceso":
            field("reason", 2000)
        target.status, target.assigned_at = "en_proceso", now()
    elif action == "cut.evidence":
        if target.status != "en_proceso" or not isinstance(p.get("kind"), str) or p["kind"] not in EVIDENCE:
            raise RuleError("Asigna primero al encargado y selecciona el tipo de evidencia.")
        encoded = p.get("photo")
        if not isinstance(encoded, str) or len(encoded) > 8_000_000:
            raise RuleError("La fotografía supera el máximo de 6 MB.")
        try:
            content = base64.b64decode(encoded, validate=True)
            media_type = validate_photo(content)
        except (ValueError, binascii.Error) as exc:
            raise RuleError("Fotografía inválida. " + str(exc)) from exc
        digest = hashlib.sha256(content).hexdigest()
        current = list(db.scalars(select(CutEvidence).where(CutEvidence.request_id == target.id,
                                                          CutEvidence.current.is_(True))))
        if any(e.sha256 == digest for e in current):
            raise RuleError("Esa fotografía ya está registrada. Cada evidencia requiere una imagen distinta.")
        replaced = next((e for e in current if e.kind == p["kind"]), None)
        previous = record(replaced) if replaced else {}
        if replaced:
            field("reason", 2000)
            replaced.current = False
        evidence = CutEvidence(request_id=target.id, kind=p["kind"],
                               filename=PureWindowsPath(field("filename", 240)).name,
                               media_type=media_type, sha256=digest, size=len(content),
                               content=content, uploaded_by=actor.id)
        db.add(evidence)
        db.flush()
        db.add(Audit(command_id=command["id"], actor_id=actor.id, action="cut.photo",
                     target_id=evidence.id, before=previous,
                     after=record(evidence), reason=str(p.get("reason", ""))))
    elif action == "cut.complete":
        if target.status != "en_proceso" or not target.assignee:
            raise RuleError("Asigna al encargado antes de finalizar.")
        kinds = set(db.scalars(select(CutEvidence.kind).where(CutEvidence.request_id == target.id,
                                                            CutEvidence.current.is_(True))))
        if kinds != set(EVIDENCE):
            raise RuleError("Faltan fotografías: identidad frente al casillero, antes del corte y después del corte.")
        if p.get("identity_verified") is not True:
            raise RuleError("Confirma la presencia del empleado y la verificación de su tarjeta Samtec ID.")
        try:
            date = datetime.fromisoformat(p.get("performed_at", ""))
            if date.tzinfo is None or not datetime.fromisoformat(target.created_at) <= date <= datetime.now(timezone.utc) + timedelta(minutes=5):
                raise ValueError()
        except (ValueError, TypeError):
            raise RuleError("La fecha del corte debe estar entre la creación de la solicitud y la fecha actual.")
        target.result = field("result", 4000)
        target.performed_at = date.astimezone(timezone.utc).isoformat()
        target.identity_verified = True
        target.status, target.completed_at, target.completed_by = "finalizada", now(), actor.id
    elif action == "cut.cancel":
        target.result = field("reason", 2000)
        target.status, target.completed_at, target.completed_by = "cancelada", now(), actor.id
    else:
        raise RuleError("Operación de corte desconocida.")
    db.flush()
    db.add(Audit(command_id=command["id"], actor_id=actor.id, action=action, target_id=target.id,
                 before=before, after=record(target), reason=str(p.get("reason", ""))))
    return {"status": "confirmada", "message": "Solicitud de corte confirmada por el servidor.",
            "target_id": target.id}
