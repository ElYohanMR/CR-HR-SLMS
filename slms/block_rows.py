"""Build one atomic inventory import from an evenly spaced row of blocks."""

import math


def plan_row(snapshot, plan_id, start, end, values):
    count, rows, columns = values["count"], values["rows"], values["columns"]
    if not 1 <= count <= 200 or not 1 <= rows <= 12 or not 1 <= columns <= 12 or count * rows * columns > 20000:
        raise ValueError("Revisa cantidad y dimensiones: máximo 200 bloques y 20000 casilleros.")
    if any(not math.isfinite(x) or not 0 <= x <= 1000 for x in (*start, *end)):
        raise ValueError("Marca ambos extremos dentro del plano.")
    if count > 1 and math.dist(start, end) < 0.01:
        raise ValueError("Marca dos extremos diferentes.")
    prefix, first_label, first_number = (
        values["prefix"].strip(),
        values["first_label"].strip(),
        values["first_number"].strip(),
    )
    if (
        not first_label.isascii()
        or not first_label.isdigit()
        or not first_number.isascii()
        or not first_number.isdigit()
    ):
        raise ValueError("El inicio del nombre y del número debe contener solo dígitos.")
    if len(first_label) > 10 or len(first_number) > 40:
        raise ValueError("Los números iniciales son demasiado largos.")
    names = {
        (b["building_id"], b["location"], b["label"].casefold())
        for b in snapshot.get("blocks", []) + snapshot.get("archived_blocks", [])
    }
    used = {x["number"] for x in snapshot.get("lockers", []) + snapshot.get("archived_lockers", [])}
    operations = []
    for i in range(count):
        label = prefix + str(int(first_label) + i).zfill(len(first_label))
        if not label or len(label) > 60 or (values["building_id"], values["location"], label.casefold()) in names:
            raise ValueError(f"El nombre {label} ya existe o no es válido.")
        numbers = [
            str(int(first_number) + i * rows * columns + n).zfill(len(first_number)) for n in range(rows * columns)
        ]
        if any(number in used or len(number) > 40 for number in numbers):
            raise ValueError(
                f"La numeración del bloque {label} coincide con casilleros existentes o supera 40 caracteres."
            )
        t = i / (count - 1) if count > 1 else 0
        operations.append(
            {
                "action": "block.create",
                "payload": {
                    "plan_id": plan_id,
                    "building_id": values["building_id"],
                    "side": values["side"],
                    "location": values["location"],
                    "label": label,
                    "rows": rows,
                    "columns": columns,
                    "x": round(start[0] + (end[0] - start[0]) * t, 2),
                    "y": round(start[1] + (end[1] - start[1]) * t, 2),
                    "rotation": values["rotation"],
                    "numbers": numbers,
                },
            }
        )
    return operations
