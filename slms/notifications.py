"""Transactional notification drafts. Corporate delivery remains disabled."""

from datetime import datetime
from zoneinfo import ZoneInfo
from .models import MailSettings, Notification, Block, Building, now


def notification(db, command_id, employee, action, locker=None, actor=None):
    settings = db.get(MailSettings, "mail")
    hr = settings.hr_email if settings else ""
    copy_hr = settings.copy_hr_on_release if settings else True
    departure = action == "employee.deactivate"
    release = action == "assignment.release"
    recipient = hr if departure else employee.email
    cc = []
    needs_hr = departure or (release and copy_hr)
    if release and copy_hr and hr:
        if not recipient:
            recipient = hr
        elif hr.casefold() != recipient.casefold():
            cc.append(hr)
    titles = {
        "employee.deactivate": "Baja de empleado registrada",
        "assignment.release": "Liberación de casillero confirmada",
        "assignment.assign": "Asignación de casillero confirmada",
        "assignment.transfer": "Cambio de casillero confirmado",
    }
    summary = titles[action]
    name = " ".join(filter(None, (employee.first_name, employee.surname, employee.second_surname)))
    at = now()
    date = datetime.fromisoformat(at).astimezone(ZoneInfo("America/Costa_Rica"))
    code = locker.number if locker else ""
    if locker:
        block = db.get(Block, locker.block_id)
        building = db.get(Building, block.building_id) if block else None
        if block and building:
            code = f"{building.code}-{block.location}-{block.label}-{locker.number}"
    if departure:
        body = f"Hola, equipo de Recursos Humanos:\n\nSe registró la baja de {name} (ID {employee.employee_number}) en Samtec Lockers.\n"
    else:
        body = f"Hola, {name}:\n\n"
        if action == "assignment.assign":
            body += f"Recursos Humanos y Recepción le informan que se le ha asignado el casillero {locker.number}.\n"
        elif action == "assignment.transfer":
            body += f"Recursos Humanos y Recepción le informan que su casillero asignado ahora es el {locker.number}.\n"
        else:
            body += f"Se ha registrado la devolución de su casillero {locker.number}.\n"
    if locker:
        body += f"Ubicación: {code}.\n"
    if departure or release:
        body += "La asignación ha finalizado.\n" if locker else "Sin casillero vigente al registrar la baja.\n"
        if locker and locker.condition == "pendiente":
            body += "El casillero está pendiente de verificación física antes de volver a asignarlo.\n"
    if actor:
        body += f"Registrado por: {actor.name}.\n"
    body += f"Fecha: {date:%d/%m/%Y} a las {date:%H:%M} (Costa Rica, UTC−06:00).\n"
    body += (f"\nSi tiene alguna consulta, comuníquese con Recursos Humanos y Recepción: {hr}.\n"
             if hr else "\nSi tiene alguna consulta, comuníquese con Recursos Humanos o Recepción.\n")
    body += "\nSaludos cordiales,\nRecursos Humanos y Recepción\nSamtec"
    # No internal notes or departure reasons belong in an employee-facing message.
    status = "sin_destinatario" if not recipient else "simulado_sin_hr" if needs_hr and not hr else "simulado"
    db.add(
        Notification(
            command_id=command_id,
            at=at,
            recipient=recipient,
            cc=cc,
            subject="Samtec Lockers · " + summary,
            body=body,
            status=status,
        )
    )
