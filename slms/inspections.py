"""Physical observations never implicitly release a person's assignment."""

from sqlalchemy import select
from .locker_condition import set_physical_condition
from .models import InspectionRound, InspectionEntry, Locker, Audit, now, record

OUTCOMES = {
    "vacio": "Vacío y utilizable",
    "coincide": "Ocupación coincide con la asignación",
    "desconocido": "Ocupado sin identificar",
    "dano": "Dañado / necesita mantenimiento",
    "diferencia": "No coincide con el sistema",
    "ausente": "No se encontró físicamente",
}
DISCREPANCIES = {"desconocido", "dano", "diferencia", "ausente"}


def apply_inspection(db, actor, command):
    from .service import get, check_version, required, active_assignment, RuleError

    action, p, versions = command["action"], command["payload"], command["versions"]
    before = {}
    if action == "inspection.create":
        ids = p.get("locker_ids")
        if not isinstance(ids, list) or not 1 <= len(ids) <= 20000 or any(not isinstance(x, str) for x in ids):
            raise RuleError("Selecciona entre 1 y 20000 casilleros.")
        if len(ids) != len(set(ids)):
            raise RuleError("Hay casilleros repetidos en la revisión.")
        for id in ids:
            get(db, Locker, id)
        target = InspectionRound(title=required(p, "title", 150), locker_ids=ids, created_by=actor.id)
        db.add(target)
    elif action in ("inspection.record", "inspection.complete"):
        round = get(db, InspectionRound, p.get("round_id"))
        if round.completed_at:
            raise RuleError("Esta revisión ya fue cerrada.", "conflicto")
        if action == "inspection.complete":
            check_version(round, versions, "inspection_round")
            entries = set(db.scalars(select(InspectionEntry.locker_id).where(InspectionEntry.round_id == round.id)))
            if entries != set(round.locker_ids):
                raise RuleError("Faltan casilleros por revisar o solicitudes por sincronizar.", "conflicto")
            target, before = round, record(round)
            round.completed_at = now()
            round.version += 1
        else:
            if p.get("locker_id") not in round.locker_ids or p.get("outcome") not in OUTCOMES:
                raise RuleError("Casillero o resultado de revisión inválido.")
            locker = get(db, Locker, p["locker_id"], include_deleted=True)
            check_version(locker, versions, "locker")
            assignment = active_assignment(db, locker_id=locker.id)
            if p["outcome"] == "vacio" and assignment:
                raise RuleError(
                    "El sistema conserva una asignación. Registra No coincide; resuelve la devolución por separado.",
                    "conflicto",
                )
            if p["outcome"] == "coincide" and not assignment:
                raise RuleError("No existe una asignación vigente. Registra Ocupado sin identificar.", "conflicto")
            if locker.deleted_at and p["outcome"] != "ausente":
                raise RuleError("El casillero está eliminado. Revisa el inventario actual.", "conflicto")
            notes = str(p.get("notes", "")).strip()
            if len(notes) > 2000 or (p["outcome"] in DISCREPANCIES and not notes):
                raise RuleError("Describe la discrepancia (máximo 2000 caracteres).")
            target = db.scalar(select(InspectionEntry).filter_by(round_id=round.id, locker_id=locker.id))
            if target:
                check_version(target, versions, "inspection_entry")
                before = record(target)
                target.version += 1
            elif p.get("entry_id"):
                raise RuleError("El resultado anterior cambió. Actualiza la revisión.", "conflicto")
            else:
                target = InspectionEntry(round_id=round.id, locker_id=locker.id)
                db.add(target)
            target.outcome, target.notes = p["outcome"], notes
            target.actor_id, target.at, target.observed_at = actor.id, now(), command["client_at"]
            target.assignment_id = assignment.id if assignment else None
            old_locker = record(locker)
            condition = {"vacio": "utilizable", "dano": "mantenimiento"}.get(p["outcome"])
            if p["outcome"] in ("desconocido", "diferencia", "ausente"):
                condition = "pendiente"
            if condition and not locker.deleted_at:
                set_physical_condition(locker, condition)
            # Every observation checks/increments the locker version, so an old offline
            # observation cannot silently replace a more recent physical inspection.
            locker.version += 1
            db.add(
                Audit(
                    command_id=command["id"],
                    actor_id=actor.id,
                    action="locker.inspected",
                    target_id=locker.id,
                    before=old_locker,
                    after=record(locker),
                    reason=OUTCOMES[p["outcome"]],
                )
            )
    else:
        raise RuleError("Operación de revisión desconocida.")
    db.flush()
    db.add(
        Audit(
            command_id=command["id"],
            actor_id=actor.id,
            action=action,
            target_id=target.id,
            before=before,
            after=record(target),
            reason=str(p.get("notes", "")),
        )
    )
    return {"status": "confirmada", "message": "Revisión confirmada por el servidor.", "target_id": target.id}
