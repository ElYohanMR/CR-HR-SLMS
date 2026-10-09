"""Atomic restoration and explicit permanent removal of archived inventory."""

from sqlalchemy import select
from .models import Block, Locker, Assignment, InspectionRound, InspectionEntry, Audit, record


def apply_batch(db, actor, command):
    from .service import RuleError, get, check_version, required, mutate

    p, versions = command["payload"], command["versions"]
    purge = command["action"] == "inventory.purge"
    if actor.role != "admin" or (purge and not actor.is_initial):
        raise RuleError(
            "Solo el administrador inicial puede eliminar definitivamente."
            if purge
            else "Solo Administración puede restaurar inventario."
        )
    if purge and p.get("confirmation") != "ELIMINAR":
        raise RuleError("Confirma la eliminación definitiva escribiendo ELIMINAR.")
    reason = required(p, "reason", 2000)
    items = p.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 20000:
        raise RuleError("Selecciona entre 1 y 20000 elementos.")
    selected = {}
    for item in items:
        if (
            not isinstance(item, dict)
            or item.get("kind") not in ("block", "locker")
            or not isinstance(item.get("id"), str)
        ):
            raise RuleError("Selección de inventario inválida.")
        kind, id = item["kind"], item["id"]
        target = get(db, Block if kind == "block" else Locker, id, include_deleted=True)
        if not target.deleted_at:
            raise RuleError("Solo se pueden procesar elementos eliminados. Actualiza la lista.", "conflicto")
        check_version(target, versions, kind)
        selected[(kind, id)] = target
    blocks = {id: obj for (kind, id), obj in selected.items() if kind == "block"}
    # A checked parent already covers its children; separately removed lockers
    # only join a restoration if explicitly checked.
    normalized = []
    for (kind, id), obj in selected.items():
        parent = blocks.get(obj.block_id) if kind == "locker" else None
        if parent and (purge or parent.deleted_at == obj.deleted_at):
            continue
        normalized.append((kind, obj))
    normalized.sort(key=lambda pair: pair[0] != "block")
    if not purge:
        for kind, obj in normalized:
            mutate(db, actor, dict(command, action=kind + ".restore", payload={"id": obj.id, "reason": reason}))
        return {
            "status": "confirmada",
            "message": f"Restauración confirmada: {len(normalized)} elementos seleccionados.",
        }
    lockers = {obj.id: obj for kind, obj in normalized if kind == "locker"}
    for block in blocks.values():
        for locker in db.scalars(select(Locker).where(Locker.block_id == block.id)):
            lockers[locker.id] = locker
    if len(lockers) > 20000:
        raise RuleError("El lote incluye más de 20000 casilleros.")
    for locker in lockers.values():
        if not locker.deleted_at:
            raise RuleError("El bloque contiene casilleros activos. Elimina primero el bloque.", "conflicto")
        check_version(locker, versions, "locker")
    ids = set(lockers)
    # Keep assignment and inspection histories meaningful: permanent removal is
    # for unused inventory; recorded use must remain recoverable.
    if ids:
        # Avoid database parameter limits for large selections.
        for start in range(0, len(ids), 500):
            chunk = list(ids)[start : start + 500]
            if db.scalar(select(Assignment.id).where(Assignment.locker_id.in_(chunk)).limit(1)):
                raise RuleError(
                    "Hay casilleros con historial de asignaciones. Se conservan como eliminados; no se borró ningún elemento."
                )
            if db.scalar(select(InspectionEntry.id).where(InspectionEntry.locker_id.in_(chunk)).limit(1)):
                raise RuleError(
                    "Hay casilleros con revisiones físicas. Se conservan como eliminados; no se borró ningún elemento."
                )
        if any(ids.intersection(round.locker_ids) for round in db.scalars(select(InspectionRound))):
            raise RuleError("Hay casilleros incluidos en una revisión física. No se borró ningún elemento.")
    for kind, objects in (("locker", lockers.values()), ("block", blocks.values())):
        for obj in objects:
            db.add(
                Audit(
                    command_id=command["id"],
                    actor_id=actor.id,
                    action=kind + ".purge",
                    target_id=obj.id,
                    before=record(obj),
                    after={},
                    reason=reason,
                )
            )
            if kind == "locker" and obj.block_id not in blocks:
                parent = get(db, Block, obj.block_id, include_deleted=True)
                parent.version += 1
            db.delete(obj)
        db.flush()
    return {
        "status": "confirmada",
        "message": f"Eliminación definitiva confirmada: {len(blocks)} bloques y {len(lockers)} casilleros. Códigos liberados.",
    }
