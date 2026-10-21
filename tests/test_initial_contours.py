import base64
import copy
import hashlib

import pytest

from scripts.import_initial_contours import prepare


def sample():
    image = b"fixture-image"
    points = [[10, 10], [50, 10], [50, 60]]
    source = {
        "format": "slms-map-contours-v1",
        "plans": [
            {
                "name": "Campus",
                "kind": "exterior",
                "floor": "",
                "building_code": None,
                "background_sha256": hashlib.sha256(image).hexdigest(),
                "polygons": [{"building_code": "E1", "points": points}],
            }
        ],
    }
    target = {
        "plans": [
            {"id": "destination-plan", "version": 7, "name": "Campus", "background": base64.b64encode(image).decode()}
        ],
        "buildings": [{"id": "destination-building", "code": "E1"}],
    }
    return source, target


def test_maps_building_codes_to_destination_ids_and_uses_current_version():
    source, target = sample()
    before = copy.deepcopy(target)
    command = prepare(source, target)
    assert command["payload"]["polygons"][0]["building_id"] == "destination-building"
    assert command["payload"]["id"] == "destination-plan"
    assert command["versions"] == {"plan:destination-plan": 7}
    assert "background" not in command["payload"]
    assert target == before


@pytest.mark.parametrize(
    "kind", ["blocks", "lockers", "archived_blocks", "archived_lockers", "employees", "assignments"]
)
def test_rejects_nonempty_destination(kind):
    source, target = sample()
    target[kind] = [{"id": "existing"}]
    with pytest.raises(ValueError, match="base nueva"):
        prepare(source, target)


def test_rejects_changed_background_and_ambiguous_plan():
    source, target = sample()
    target["plans"][0]["background"] = base64.b64encode(b"different").decode()
    with pytest.raises(ValueError, match="imagen"):
        prepare(source, target)
    source, target = sample()
    target["plans"].append(copy.deepcopy(target["plans"][0]))
    with pytest.raises(ValueError, match="único"):
        prepare(source, target)
