"""Locker traversal translated to the existing physical coordinates (column 0 = right)."""

DIRECTIONS = [
    ("De izquierda a derecha", "left_to_right"),
    ("De derecha a izquierda", "right_to_left"),
    ("De arriba a abajo", "top_to_bottom"),
    ("De abajo a arriba", "bottom_to_top"),
]
DEFAULT_FIRST = "right_to_left"
DEFAULT_SECOND = "top_to_bottom"
HORIZONTAL = {"left_to_right", "right_to_left"}
VERTICAL = {"top_to_bottom", "bottom_to_top"}


def second_choices(first):
    allowed = VERTICAL if first in HORIZONTAL else HORIZONTAL
    return [(label, value) for label, value in DIRECTIONS if value in allowed]


def normalize_order(first, second):
    if first not in HORIZONTAL | VERTICAL:
        first = DEFAULT_FIRST
    allowed = {value for _, value in second_choices(first)}
    if second not in allowed:
        second = DEFAULT_SECOND if first in HORIZONTAL else DEFAULT_FIRST
    return first, second


def arrange_numbers(numbers, rows, columns, first=DEFAULT_FIRST, second=DEFAULT_SECOND):
    """Return numbers in storage order, leaving their labels and leading zeros intact."""
    if (first, second) != normalize_order(first, second):
        raise ValueError("Selecciona dos direcciones perpendiculares para la numeración.")
    if len(numbers) != rows * columns:
        raise ValueError(f"Indica exactamente {rows * columns} números, uno por casillero.")
    row_order = list(range(rows))
    column_order = list(range(columns))
    if "bottom_to_top" in (first, second):
        row_order.reverse()
    if "left_to_right" in (first, second):
        column_order.reverse()
    positions = (
        [(row, column) for row in row_order for column in column_order]
        if first in HORIZONTAL
        else [(row, column) for column in column_order for row in row_order]
    )
    result = [None] * len(numbers)
    for number, (row, column) in zip(numbers, positions):
        result[row * columns + column] = number
    return result


def bind_order_combos(first, second):
    """Restrict the second combo before any form change handlers run."""
    def update(*_):
        _, value = normalize_order(first.currentData(), second.currentData())
        blocked = second.blockSignals(True)
        try:
            second.clear()
            for label, code in second_choices(first.currentData()):
                second.addItem(label, code)
            second.setCurrentIndex(second.findData(value))
        finally:
            second.blockSignals(blocked)

    first.currentIndexChanged.connect(update)
    update()


def numbering_fields():
    return [
        ("numbering_first", "Primer paso de numeración", DIRECTIONS),
        ("numbering_second", "Segundo paso de numeración", DIRECTIONS),
    ]
