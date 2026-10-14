"""Build one atomic inventory import from an evenly spaced row of blocks."""

import math

from .numbering import arrange_numbers, DEFAULT_FIRST, DEFAULT_SECOND


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
    names = {(b["building_id"], b["location"], b["label"].casefold()): b for b in snapshot.get("blocks", [])}
    archived = {
        (b["building_id"], b["location"], b["label"].casefold()): b for b in snapshot.get("archived_blocks", [])
    }
    used = {x["number"]: x for x in snapshot.get("lockers", []) + snapshot.get("archived_lockers", [])}
    operations = []
    for i in range(count):
        label = prefix + str(int(first_label) + i).zfill(len(first_label))
        key = (values["building_id"], values["location"], label.casefold())
        if not label or len(label) > 60:
            raise ValueError(f"El nombre {label} no es válido.")
        if key in archived:
            raise ValueError(
                f"El bloque {label} está eliminado y su código sigue reservado. "
                "No necesitas borrar el historial. Ve a Inventario → Más acciones → "
                "Elementos eliminados / restaurar, restaura los bloques que quieras incluir y sincroniza. "
                "Después vuelve a crear la fila: los bloques restaurados se reubicarán conservando sus casilleros."
            )
        existing = names.get(key)
        numbers = [
            str(int(first_number) + i * rows * columns + n).zfill(len(first_number)) for n in range(rows * columns)
        ]
        if existing:
            if any(
                existing[k] != expected
                for k, expected in (
                    ("plan_id", plan_id),
                    ("rows", rows),
                    ("columns", columns),
                )
            ):
                raise ValueError(
                    f"El bloque {label} ya existe con otro plano o dimensiones. "
                    "La fila solo puede cambiar su ubicación, no reconstruir sus casilleros."
                )
            lockers = sorted(
                (x for x in snapshot.get("lockers", []) if x["block_id"] == existing["id"]),
                key=lambda x: (x["row"], x["column"]),
            )
            if len(lockers) != rows * columns or {x["number"] for x in lockers} != set(numbers):
                raise ValueError(
                    f"La numeración de {label} no coincide con la fila propuesta. "
                    "Revisa su primer número y dimensiones; se conservan sus números y asignaciones. "
                    "Si eliminaste casilleros por separado, restáuralos primero."
                )
            # Repositioning a block never renumbers it, even when defaults have changed.
            numbers = [x["number"] for x in lockers]
        else:
            numbers = arrange_numbers(
                numbers, rows, columns,
                values.get("numbering_first", DEFAULT_FIRST), values.get("numbering_second", DEFAULT_SECOND),
            )
        if any(
            (number in used and (not existing or used[number]["block_id"] != existing["id"])) or len(number) > 40
            for number in numbers
        ):
            raise ValueError(
                f"La numeración del bloque {label} coincide con casilleros existentes o supera 40 caracteres."
            )
        t = i / (count - 1) if count > 1 else 0
        operations.append(
            {
                "action": "block.update" if existing else "block.create",
                "versions": {"block:" + existing["id"]: existing["version"]} if existing else {},
                "payload": {
                    **({"id": existing["id"]} if existing else {}),
                    "plan_id": plan_id,
                    "building_id": values["building_id"],
                    "side": existing["side"] if existing else values["side"],
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
