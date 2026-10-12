import base64
import hashlib
import json
import math
import re
from sqlalchemy import select, text, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from .database import password_hash
from .models import (
    Admin,
    Building,
    Plan,
    Block,
    Locker,
    Employee,
    Assignment,
    Receipt,
    Audit,
    MailSettings,
    Session,
    now,
    record,
)
from .notifications import notification


class RuleError(Exception):
    def __init__(self, message, status="rechazada"):
        self.status = status
        super().__init__(message)


def required(data, key, maxlen=200):
    value = str(data.get(key, "")).strip()
    if not value or len(value) > maxlen:
        raise RuleError(f"El campo {key} es obligatorio y admite hasta {maxlen} caracteres.")
    return value


def get(db, model, key, include_deleted=False):
    item = db.get(model, key)
    if item is None or (getattr(item, "deleted_at", None) and not include_deleted):
        raise RuleError("El registro ya no existe. Actualiza la información.", "conflicto")
    return item


def check_version(obj, versions, kind):
    if versions.get(f"{kind}:{obj.id}") != obj.version:
        raise RuleError(
            "Otro administrador cambió este registro. Revisa los datos actualizados y crea una nueva solicitud.",
            "conflicto",
        )


def active_assignment(db, **filters):
    return db.scalar(select(Assignment).filter_by(**filters).where(Assignment.ended_at.is_(None)))


def numeric(data, key, minimum, maximum, default):
    try:
        value = float(data.get(key, default))
    except (ValueError, TypeError):
        raise RuleError(f"{key} debe ser un número.")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise RuleError(f"{key} debe estar entre {minimum} y {maximum}.")
    return value


def mutate(db, actor, command):
    action, p, versions = command["action"], command["payload"], command["versions"]
    before, target = {}, None
    admin_actions = ("building.", "plan.", "block.", "admin.", "mail_settings.", "inventory.")
    if actor.role == "viewer" or (action.startswith(admin_actions) and actor.role != "admin"):
        raise RuleError("Tu cuenta no tiene permiso para esta operación.")
    if action in ("locker.delete", "locker.restore") and actor.role != "admin":
        raise RuleError("Solo Administración puede eliminar o restaurar inventario.")
    if action.startswith("inspection."):
        from .inspections import apply_inspection
        return apply_inspection(db, actor, command)
    if action.startswith("cut."):
        from .cuts import apply_cut
        return apply_cut(db, actor, command)
    if action in ("inventory.restore_many", "inventory.purge"):
        from .inventory_batch import apply_batch
        return apply_batch(db, actor, command)
    if action == "inventory.import":
        operations = p.get("operations")
        if not isinstance(operations, list) or not 1 <= len(operations) <= 2000:
            raise RuleError("La importación debe contener de 1 a 2000 bloques.")
        results = []
        for operation in operations:
            if (
                not isinstance(operation, dict)
                or operation.get("action") not in ("block.create", "block.update")
                or not isinstance(operation.get("payload"), dict)
            ):
                raise RuleError("La importación solo admite creación y ubicación de bloques.")
            result = mutate(db, actor, dict(command, action=operation["action"], payload=operation["payload"]))
            results.append(result["target_id"])
        return {
            "status": "confirmada",
            "message": f"Importación confirmada: {len(results)} bloques.",
            "target_ids": results,
        }
    if action in ("employee.create", "employee.update"):
        if action.endswith("update"):
            target = get(db, Employee, p.get("id"))
            check_version(target, versions, "employee")
            before = record(target)
        else:
            target = Employee()
            db.add(target)
        for field in ("employee_number", "first_name", "surname"):
            setattr(target, field, required(p, field, 80 if field == "employee_number" else 100))
        for field, length in (
            ("second_surname", 100),
            ("email", 254),
            ("department", 120),
            ("shift", 80),
            ("notes", 10000),
        ):
            value = str(p.get(field, "")).strip()
            if len(value) > length:
                raise RuleError(f"El campo {field} es demasiado largo.")
            setattr(target, field, value)
        if target.email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", target.email):
            raise RuleError("El correo no tiene un formato válido.")
        if not isinstance(p.get("active", True), bool):
            raise RuleError("El estado activo debe ser verdadero o falso.")
        if not p.get("active", True) and target.id and target.active:
            raise RuleError("Usa Dar de baja y liberar para conservar el motivo y preparar la notificación a HR.")
        target.active = p.get("active", True)
    elif action == "employee.deactivate":
        target = get(db, Employee, p.get("employee_id"))
        check_version(target, versions, "employee")
        if not target.active:
            raise RuleError("La persona ya está inactiva.", "conflicto")
        departure_type = p.get("departure_type")
        if departure_type not in ("despido", "renuncia", "fin_contrato", "otra_baja"):
            raise RuleError("Selecciona un tipo de baja válido.")
        reason = required(p, "reason", 2000)
        verified = p.get("locker_verified", False)
        if not isinstance(verified, bool):
            raise RuleError("La verificación física debe ser verdadera o falsa.")
        current = active_assignment(db, employee_id=target.id)
        if (current.id if current else None) != p.get("assignment_id"):
            raise RuleError("La asignación cambió. Actualiza la información antes de dar de baja.", "conflicto")
        before = record(target)
        locker = None
        at = now()
        if current:
            locker = get(db, Locker, current.locker_id)
            check_version(locker, versions, "locker")
            old_assignment = record(current)
            old_locker = record(locker)
            current.ended_at, current.ended_by, current.end_reason = at, actor.id, reason
            current.version += 1
            locker.condition = "utilizable" if verified else "pendiente"
            locker.version += 1
            db.add(
                Audit(
                    command_id=command["id"],
                    actor_id=actor.id,
                    at=at,
                    action="assignment.release",
                    target_id=current.id,
                    before={"assignment": old_assignment, "locker": old_locker},
                    after=dict(record(current), locker_condition=locker.condition),
                    reason=reason,
                )
            )
        target.active = False
        target.extra = dict(
            target.extra or {}, departure={"type": departure_type, "reason": reason, "at": at, "by": actor.id}
        )
        notification(db, command["id"], target, action, locker)
    elif action == "mail_settings.update":
        target = get(db, MailSettings, "mail")
        check_version(target, versions, "mail_settings")
        before = record(target)
        email = str(p.get("hr_email", "")).strip()
        if len(email) > 254 or (email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)):
            raise RuleError("El correo de HR no tiene un formato válido.")
        if not isinstance(p.get("copy_hr_on_release", True), bool):
            raise RuleError("La opción de copia a HR debe ser verdadera o falsa.")
        target.hr_email = email
        target.copy_hr_on_release = p.get("copy_hr_on_release", True)
    elif action in ("building.create", "building.update"):
        target = get(db, Building, p.get("id")) if action.endswith("update") else Building()
        if target.id:
            check_version(target, versions, "building")
            before = record(target)
        target.code = required(p, "code", 30).upper()
        target.name = required(p, "name", 150)
        db.add(target)
    elif action in ("plan.create", "plan.update"):
        target = get(db, Plan, p.get("id")) if action.endswith("update") else Plan()
        if target.id:
            check_version(target, versions, "plan")
            before = {k: v for k, v in record(target).items() if k != "background"}
        target.name = required(p, "name", 150)
        target.kind = p.get("kind", "exterior")
        if target.kind not in ("exterior", "interior"):
            raise RuleError("El plano debe ser exterior o interior.")
        target.floor = str(p.get("floor", ""))[:50]
        target.building_id = p.get("building_id") or None
        if target.building_id:
            get(db, Building, target.building_id)
        polygons = p.get("polygons", [])
        if not isinstance(polygons, list) or len(polygons) > 100:
            raise RuleError("Contornos inválidos.")
        for polygon in polygons:
            get(db, Building, polygon.get("building_id"))
            points = polygon.get("points", [])
            if not 3 <= len(points) <= 100:
                raise RuleError("Cada contorno debe tener entre 3 y 100 puntos.")
            for point in points:
                if len(point) != 2 or any(
                    not isinstance(n, (int, float)) or not math.isfinite(n) or not 0 <= n <= 1000 for n in point
                ):
                    raise RuleError("Los puntos deben estar dentro del plano (0 a 1000).")
        target.polygons = polygons
        if "background" in p:
            value = p["background"]
            if not isinstance(value, str) or len(value) > 8_000_000:
                raise RuleError("La imagen excede el máximo permitido (6 MB).")
            try:
                raw = base64.b64decode(value, validate=True)
            except Exception:
                raise RuleError("La imagen no es válida.")
            if value and not (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff")):
                raise RuleError("Utiliza una imagen PNG o JPEG.")
            target.background = value
        db.add(target)
    elif action == "block.create":
        get(db, Plan, p.get("plan_id"))
        get(db, Building, p.get("building_id"))
        rows = int(numeric(p, "rows", 1, 12, 4))
        cols = int(numeric(p, "columns", 1, 12, 3))
        numbers = p.get("numbers", [])
        if (
            len(numbers) != rows * cols
            or len(set(numbers)) != len(numbers)
            or any(not isinstance(n, str) or not n.strip() or len(n) > 40 for n in numbers)
        ):
            raise RuleError("Indica un número físico único por cada casillero, en orden de filas.")
        if p.get("side") not in ("N", "S", "E", "O") or p.get("location") not in ("EXT", "INT"):
            raise RuleError("Ubicación inválida.")
        target = Block(
            plan_id=p["plan_id"],
            building_id=p["building_id"],
            label=required(p, "label", 60),
            rows=rows,
            columns=cols,
            side=p["side"],
            location=p["location"],
            x=numeric(p, "x", 0, 1000, 500),
            y=numeric(p, "y", 0, 1000, 500),
            rotation=numeric(p, "rotation", -360, 360, 0),
        )
        db.add(target)
        db.flush()
        for i, number in enumerate(numbers):
            db.add(Locker(block_id=target.id, number=number.strip(), row=i // cols, column=i % cols))
    elif action in ("block.delete", "locker.delete", "block.restore", "locker.restore"):
        is_block, restoring = action.startswith("block."), action.endswith("restore")
        kind = "block" if is_block else "locker"
        target = get(db, Block if is_block else Locker, p.get("id"), include_deleted=True)
        if target.deleted_at and not restoring:
            return {
                "status": "confirmada",
                "message": "El elemento ya estaba eliminado; no se volvió a modificar.",
                "target_id": target.id,
            }
        check_version(target, versions, kind)
        reason = required(p, "reason", 2000)
        if restoring and not target.deleted_at:
            raise RuleError("Este elemento ya está en el inventario.", "conflicto")
        before = record(target)
        if is_block:
            query = select(Locker).where(Locker.block_id == target.id)
            query = (
                query.where(Locker.deleted_at == target.deleted_at)
                if restoring
                else query.where(Locker.deleted_at.is_(None))
            )
            children = list(db.scalars(query))
            for locker in children:
                check_version(locker, versions, "locker")
                if active_assignment(db, locker_id=locker.id):
                    raise RuleError("Libera las asignaciones activas antes de eliminar el bloque.", "conflicto")
        else:
            get(db, Block, target.block_id)
            children = []
            if active_assignment(db, locker_id=target.id):
                raise RuleError("Libera la asignación activa antes de eliminar el casillero.", "conflicto")
        stamp = None if restoring else now()
        for locker in children:
            old = record(locker)
            locker.deleted_at = stamp
            if restoring:
                locker.condition = "pendiente"
            locker.version += 1
            db.add(
                Audit(
                    command_id=command["id"],
                    actor_id=actor.id,
                    action="locker.restore" if restoring else "locker.delete",
                    target_id=locker.id,
                    before=old,
                    after=record(locker),
                    reason=reason,
                )
            )
        target.deleted_at = stamp
        if restoring and not is_block:
            target.condition = "pendiente"
        if not is_block:
            # Invalidate a block removal prepared before this membership change.
            get(db, Block, target.block_id).version += 1
    elif action == "block.update":
        target = get(db, Block, p.get("id"))
        check_version(target, versions, "block")
        before = record(target)
        target.label = required(p, "label", 60)
        for key, low, high in (("x", 0, 1000), ("y", 0, 1000), ("rotation", -360, 360)):
            setattr(target, key, numeric(p, key, low, high, getattr(target, key)))
    elif action == "lockers.verify":
        target = get(db, Block, p.get("block_id"))
        check_version(target, versions, "block")
        pending = list(
            db.scalars(
                select(Locker).where(
                    Locker.block_id == target.id, Locker.condition == "pendiente", Locker.deleted_at.is_(None)
                )
            )
        )
        if not pending:
            raise RuleError("No hay casilleros pendientes de verificar en este bloque.", "conflicto")
        before = {"pending_count": len(pending)}
        for locker in pending:
            check_version(locker, versions, "locker")
            old = record(locker)
            locker.condition = "utilizable"
            locker.version += 1
            db.add(
                Audit(
                    command_id=command["id"],
                    actor_id=actor.id,
                    action="locker.update",
                    target_id=locker.id,
                    before=old,
                    after=record(locker),
                    reason=required(p, "reason", 2000),
                )
            )
    elif action == "locker.update":
        target = get(db, Locker, p.get("id"))
        check_version(target, versions, "locker")
        before = record(target)
        condition = p.get("condition", target.condition)
        if condition not in ("pendiente", "utilizable", "mantenimiento", "retirado"):
            raise RuleError("Condición inválida.")
        if condition != "utilizable" and active_assignment(db, locker_id=target.id):
            raise RuleError("Libera el casillero antes de cambiar su condición.")
        target.number = required(p, "number", 40)
        target.condition = condition
        target.notes = str(p.get("notes", ""))[:10000]
    elif action in ("assignment.assign", "assignment.transfer", "assignment.release"):
        employee = get(db, Employee, p.get("employee_id"))
        check_version(employee, versions, "employee")
        current = active_assignment(db, employee_id=employee.id)
        reason = required(p, "reason", 2000)
        if action == "assignment.release" and not isinstance(p.get("locker_verified", False), bool):
            raise RuleError("La verificación física debe ser verdadera o falsa.")
        before = {"assignment": record(current) if current else None}
        if action != "assignment.assign":
            if not current or current.id != p.get("assignment_id"):
                raise RuleError("La asignación vigente cambió. Actualiza la información.", "conflicto")
            old_locker = get(db, Locker, current.locker_id)
            check_version(old_locker, versions, "locker")
        elif current:
            raise RuleError("La persona ya tiene un casillero asignado.", "conflicto")
        if action != "assignment.release":
            if not employee.active:
                raise RuleError("La persona está inactiva.")
            locker = get(db, Locker, p.get("locker_id"))
            check_version(locker, versions, "locker")
            if locker.condition != "utilizable":
                raise RuleError("Este casillero necesita verificación o no está utilizable.")
            if active_assignment(db, locker_id=locker.id):
                raise RuleError("El casillero ya tiene una asignación vigente.", "conflicto")
        if current:
            current.ended_at, current.ended_by, current.end_reason = now(), actor.id, reason
            current.version += 1
            if action == "assignment.release":
                before["locker"] = record(old_locker)
                old_locker.condition = "utilizable" if p.get("locker_verified", False) else "pendiente"
            old_locker.version += 1
            db.flush()
        if action == "assignment.release":
            target = current
        else:
            target = Assignment(employee_id=employee.id, locker_id=locker.id, started_by=actor.id, reason=reason)
            db.add(target)
            locker.version += 1
        employee.version += 1
        db.flush()
        notification(db, command["id"], employee, action, get(db, Locker, target.locker_id))
    elif action in ("admin.create", "admin.update"):
        target = get(db, Admin, p.get("id")) if action.endswith("update") else Admin()
        if "is_initial" in p:
            raise RuleError("La identidad del administrador inicial no se puede modificar.")
        if target.is_initial and actor.id != target.id:
            raise RuleError("Solo el administrador inicial puede modificar su propia cuenta.")
        if target.id:
            check_version(target, versions, "admin")
            before = record(target)
        role = p.get("role", "operator")
        if role not in ("admin", "operator", "viewer"):
            raise RuleError("Rol inválido.")
        if target.id == actor.id and (role != "admin" or not p.get("active", True)):
            raise RuleError("No puedes quitarte el acceso de administrador desde tu propia cuenta.")
        target.username = required(p, "username", 120).lower()
        target.name = required(p, "name", 200)
        target.role, target.active = role, bool(p.get("active", True))
        if p.get("password") or not target.id:
            if len(p.get("password", "")) < 10:
                raise RuleError("La contraseña necesita al menos 10 caracteres.")
            target.password_hash = password_hash(p["password"])
            if target.id:
                db.execute(delete(Session).where(Session.admin_id == target.id))
        db.add(target)
    else:
        raise RuleError("Operación desconocida.")
    if before and not action.startswith("assignment."):
        target.version += 1
    db.flush()
    after = record(target)
    if action == "assignment.release":
        after["locker_condition"] = get(db, Locker, target.locker_id).condition
    after.pop("background", None)
    db.add(
        Audit(
            command_id=command["id"],
            actor_id=actor.id,
            action=action,
            target_id=target.id,
            before=before,
            after=after,
            reason=str(p.get("reason", "")),
        )
    )
    return {"status": "confirmada", "message": "Operación confirmada por el servidor.", "target_id": target.id}


def execute(engine, actor_id, command):
    digest = hashlib.sha256(json.dumps(command, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with sessionmaker(engine)() as db:
        if engine.dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        else:
            # Three operator workstations: serialize short mutation transactions.
            db.execute(text("SELECT pg_advisory_xact_lock(731962401)"))
        actor = get(db, Admin, actor_id)
        if not actor.active:
            raise RuleError("Cuenta desactivada.")
        previous = db.get(Receipt, command["id"])
        if previous:
            if previous.actor_id != actor_id or previous.payload_hash != digest:
                raise RuleError("El identificador de solicitud fue reutilizado con otro contenido.", "conflicto")
            return previous.result
        try:
            with db.begin_nested():
                result = mutate(db, actor, command)
        except RuleError as exc:
            result = {"status": exc.status, "message": str(exc)}
        except IntegrityError:
            result = {
                "status": "conflicto",
                "message": "Ya existe ese número, usuario o asignación. Revisa los registros actuales.",
            }
        db.add(
            Receipt(
                id=command["id"],
                actor_id=actor_id,
                payload_hash=digest,
                device_id=command["device_id"],
                client_at=command["client_at"],
                result=result,
            )
        )
        db.commit()
        return result
