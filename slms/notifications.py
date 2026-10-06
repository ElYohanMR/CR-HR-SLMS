"""Transactional notification drafts. Corporate delivery remains disabled."""

from .models import MailSettings, Notification, now


def notification(db, command_id, employee, action, locker=None):
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
    body = f"{summary}.\nEmpleado: {name} · ID {employee.employee_number}.\n"
    body += f"Casillero: {locker.number}.\n" if locker else "Sin casillero vigente al registrar la baja.\n"
    if departure or release:
        body += "La asignación ha finalizado.\n" if locker else ""
        if locker and locker.condition == "pendiente":
            body += "El casillero está pendiente de verificación física antes de volver a asignarlo.\n"
    # Departure reasons and internal notes are deliberately excluded from all email bodies.
    body += f"Confirmación del servidor: {now()}.\n\nSIMULACIÓN: este correo no se ha enviado."
    status = "sin_destinatario" if not recipient else "simulado_sin_hr" if needs_hr and not hr else "simulado"
    db.add(
        Notification(
            command_id=command_id,
            recipient=recipient,
            cc=cc,
            subject="Samtec Lockers · " + summary,
            body=body,
            status=status,
        )
    )
