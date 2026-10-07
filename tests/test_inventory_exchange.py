import copy
import pytest
from slms.inventory_io import export_rows, read_inventory, write_inventory, prepare_import
from conftest import cmd


def new_rows(snapshot, label="E01", prefix="000"):
    rows = export_rows(snapshot)[:12]
    for index, row in enumerate(rows):
        row.update(
            id_bloque="",
            version_bloque="",
            bloque=label,
            filas="3",
            columnas="4",
            fila=str(index // 4 + 1),
            columna=str(index % 4 + 1),
            numero=prefix + str(index),
            x="800",
            y="600",
            rotacion="-15",
        )
    return rows


@pytest.mark.parametrize("extension", ["xlsx", "csv"])
def test_inventory_roundtrip_and_leading_zeros(system, tmp_path, extension):
    _, client, _ = system
    data = client.get("/snapshot").json()
    rows = new_rows(data)
    path = tmp_path / ("inventory." + extension)
    write_inventory(path, rows)
    assert read_inventory(path) == rows
    operations, versions = prepare_import(read_inventory(path), data)
    request = cmd("inventory.import", {"operations": operations}, versions)
    result = client.post("/commands", json=request).json()
    assert result["status"] == "confirmada"
    assert client.post("/commands", json=request).json() == result
    data = client.get("/snapshot").json()
    created = [item for item in data["lockers"] if item["block_id"] == result["target_ids"][0]]
    assert len(created) == 12
    assert all(item["condition"] == "pendiente" for item in created)
    assert created[0]["number"].startswith("000")
    write_inventory(path, export_rows(data))
    assert prepare_import(read_inventory(path), data) == ([], {})


def test_inventory_updates_preserve_assignments_and_atomic_rollback(system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    employee, locker = data["employees"][0], data["lockers"][0]
    assert (
        client.post(
            "/commands",
            json=cmd(
                "assignment.assign",
                {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Prueba"},
                {"employee:" + employee["id"]: employee["version"], "locker:" + locker["id"]: locker["version"]},
            ),
        ).json()["status"]
        == "confirmada"
    )
    data = client.get("/snapshot").json()
    rows = export_rows(data)
    for row in rows:
        row.update(x="777", y="250", bloque="RENAMED")
    operations, versions = prepare_import(rows, data)
    good = copy.deepcopy(operations)
    create, _ = prepare_import(new_rows(data), data)
    # The second operation conflicts; the preceding block movement must roll back.
    create[0]["payload"]["numbers"][0] = data["lockers"][0]["number"]
    failed = client.post(
        "/commands", json=cmd("inventory.import", {"operations": operations + create}, versions)
    ).json()
    assert failed["status"] == "conflicto"
    after = client.get("/snapshot").json()
    assert after["blocks"] == data["blocks"]
    assert after["assignments"] == data["assignments"]
    assert after["lockers"] == data["lockers"]
    assert len(after["audit"]) == len(data["audit"])
    assert (
        client.post("/commands", json=cmd("inventory.import", {"operations": good}, versions)).json()["status"]
        == "confirmada"
    )
    after = client.get("/snapshot").json()
    assert after["blocks"][0]["x"] == 777
    assert after["assignments"] == data["assignments"]
    assert after["lockers"] == data["lockers"]
    assert (
        client.post("/commands", json=cmd("inventory.import", {"operations": good}, versions)).json()["status"]
        == "conflicto"
    )


@pytest.mark.parametrize(
    "change", ["duplicate", "missing", "coordinate", "inconsistent", "fraction", "stale", "renumber"]
)
def test_bad_inventory_is_rejected(system, change):
    _, client, _ = system
    data = client.get("/snapshot").json()
    rows = export_rows(data)
    if change == "duplicate":
        rows.append(rows[0].copy())
    elif change == "missing":
        rows.pop()
    elif change == "coordinate":
        rows[0]["x"] = "nan"
    elif change == "inconsistent":
        rows[0]["y"] = "12"
    elif change == "fraction":
        rows[0]["filas"] = "3.5"
    elif change == "stale":
        rows[0]["version_bloque"] = "99"
    else:
        rows[0]["numero"] = "new-number"
    with pytest.raises(ValueError):
        prepare_import(rows, data)


def test_excel_formula_is_rejected_and_text_export_is_literal(tmp_path):
    from openpyxl import load_workbook
    from slms.inventory_io import HEADERS

    path = tmp_path / "formula.xlsx"
    row = {key: "" for key in HEADERS}
    row["numero"] = "=1+1"
    write_inventory(path, [row])
    assert read_inventory(path)[0]["numero"] == "=1+1"
    book = load_workbook(path)
    book["Inventario"]["O2"] = "=1+1"
    book.save(path)
    book.close()
    with pytest.raises(ValueError, match="fórmulas"):
        read_inventory(path)


def test_import_requires_admin(system):
    engine, client, session = system
    from sqlalchemy.orm import Session
    from slms.models import Admin

    data = client.get("/snapshot").json()
    operations, versions = prepare_import(new_rows(data), data)
    with Session(engine) as db:
        db.get(Admin, session["actor"]["id"]).role = "operator"
        db.commit()
    assert (
        client.post("/commands", json=cmd("inventory.import", {"operations": operations}, versions)).json()["status"]
        == "rechazada"
    )
