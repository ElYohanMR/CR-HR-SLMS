import pytest

from conftest import cmd
from slms.block_rows import plan_row
from slms.numbering import arrange_numbers


# Expected front-facing layout, independently specified for every traversal.
LAYOUTS = [
    ("left_to_right", "top_to_bottom", [[1, 2, 3], [4, 5, 6]]),
    ("left_to_right", "bottom_to_top", [[4, 5, 6], [1, 2, 3]]),
    ("right_to_left", "top_to_bottom", [[3, 2, 1], [6, 5, 4]]),
    ("right_to_left", "bottom_to_top", [[6, 5, 4], [3, 2, 1]]),
    ("top_to_bottom", "left_to_right", [[1, 3, 5], [2, 4, 6]]),
    ("top_to_bottom", "right_to_left", [[5, 3, 1], [6, 4, 2]]),
    ("bottom_to_top", "left_to_right", [[2, 4, 6], [1, 3, 5]]),
    ("bottom_to_top", "right_to_left", [[6, 4, 2], [5, 3, 1]]),
]


@pytest.mark.parametrize("first,second,expected", LAYOUTS)
def test_all_eight_layouts_saved_and_existing_blocks_not_renumbered(system, first, second, expected):
    _, client, _ = system
    snapshot = client.get("/snapshot").json()
    values = dict(count=1, rows=2, columns=3, prefix="TEST", first_label="01", first_number="0001",
                  building_id=snapshot["buildings"][0]["id"], location="EXT", side="E", rotation=10,
                  numbering_first=first, numbering_second=second)
    operations = plan_row(snapshot, "campus", (100, 100), (200, 200), values)
    result = client.post("/commands", json=cmd("inventory.import", {"operations": operations})).json()
    assert result["status"] == "confirmada", result
    after = client.get("/snapshot").json()
    block = next(b for b in after["blocks"] if b["label"] == "TEST01")
    lockers = [x for x in after["lockers"] if x["block_id"] == block["id"]]
    physical = {(x["row"], 2 - x["column"]): x["number"] for x in lockers}
    assert [[physical[r, c] for c in range(3)] for r in range(2)] == [
        [str(n).zfill(4) for n in row] for row in expected
    ]
    # New defaults affect only the newly created second block in a mixed row.
    values.update(count=2, numbering_first="right_to_left", numbering_second="top_to_bottom")
    operations = plan_row(after, "campus", (300, 300), (400, 400), values)
    assert operations[0]["action"] == "block.update"
    assert operations[1]["payload"]["numbers"] == [str(n).zfill(4) for n in range(7, 13)]
    versions = {k: v for op in operations for k, v in op["versions"].items()}
    result = client.post("/commands", json=cmd("inventory.import", {"operations": operations}, versions)).json()
    assert result["status"] == "confirmada", result
    assert [x for x in client.get("/snapshot").json()["lockers"] if x["block_id"] == block["id"]] == lockers


def test_manual_labels_single_axis_and_invalid_inputs():
    assert arrange_numbers(["A", "009", "Z", "7"], 2, 2, "top_to_bottom", "left_to_right") == [
        "Z", "A", "7", "009"
    ]
    assert arrange_numbers(["1", "2", "3"], 3, 1, "bottom_to_top", "left_to_right") == ["3", "2", "1"]
    assert arrange_numbers(["1", "2", "3"], 1, 3, "top_to_bottom", "left_to_right") == ["3", "2", "1"]
    with pytest.raises(ValueError, match="perpendiculares"):
        arrange_numbers(["1"], 1, 1, "left_to_right", "right_to_left")
    with pytest.raises(ValueError, match="exactamente"):
        arrange_numbers(["1"], 2, 3)
