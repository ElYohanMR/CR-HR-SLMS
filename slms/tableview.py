"""Consistent sorting and stable selection for every desktop table."""

from datetime import datetime
from decimal import Decimal
import re
from zoneinfo import ZoneInfo

from PySide6.QtCore import QCollator, QLocale, Qt
from PySide6.QtWidgets import QTableWidgetItem


_collator = QCollator(QLocale("es_CR"))
_collator.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
_collator.setNumericMode(True)
_numbers = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
_dates = {"Fecha", "Fecha / hora", "Creada", "Eliminado el", "Confirmado el"}


class SortableItem(QTableWidgetItem):
    def __init__(self, value, key, header):
        text = str(value if value is not None else "")
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, key)
        self.order_key = self.sort_key(text.strip(), header)

    @staticmethod
    def sort_key(text, header):
        if text in ("", "—"):
            return (0, "")
        if header in _dates:
            try:
                date = datetime.strptime(text, "%d/%m/%Y %H:%M:%S")
            except ValueError:
                try:
                    date = datetime.fromisoformat(text)
                except ValueError:
                    date = None
            if date is not None:
                if date.tzinfo is None:
                    date = date.replace(tzinfo=ZoneInfo("America/Costa_Rica"))
                return (1, date.timestamp())
        if _numbers.fullmatch(text):
            return (2, Decimal(text.replace(",", ".")))
        return (3, text)

    def __lt__(self, other):
        if not isinstance(other, SortableItem):
            return super().__lt__(other)
        left, right = self.order_key, other.order_key
        if left[0] == right[0] == 3:
            return _collator.compare(left[1], right[1]) < 0
        return left < right


def enable_sorting(table):
    header = table.horizontalHeader()
    header.setSectionsClickable(True)
    # Keep the original order until the user chooses a column (especially history).
    header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
    header.setSortIndicatorShown(True)
    table.setSortingEnabled(True)
    for column in range(table.columnCount()):
        table.horizontalHeaderItem(column).setToolTip(
            "Haz clic para ordenar de menor a mayor o de A a Z. "
            "Otro clic invierte el orden. La flecha indica el orden actual."
        )


def fill_table(table, rows):
    checked = set(checked_ids(table))
    current = table.item(table.currentRow(), 0)
    selected = current.data(Qt.ItemDataRole.UserRole) if current else None
    sorting = table.isSortingEnabled()
    updates = table.updatesEnabled()
    signals = table.blockSignals(True)
    table.setUpdatesEnabled(False)
    try:
        # Sorting during setItem would move partially populated rows and mix records.
        table.setSortingEnabled(False)
        table.clearContents()
        table.setRowCount(len(rows))
        table.setCurrentCell(-1, -1)
        table.clearSelection()
        for row, (key, values) in enumerate(rows):
            for column, value in enumerate(values):
                label = table.horizontalHeaderItem(column).text()
                table.setItem(row, column, SortableItem(value, key, label))
                if column == 0:
                    table.item(row, 0).setCheckState(
                        Qt.CheckState.Checked if key in checked else Qt.CheckState.Unchecked
                    )
    finally:
        table.setSortingEnabled(sorting)
        # Restore by record ID after sorting, never by the previous row number.
        if selected is not None:
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == selected:
                    table.setCurrentCell(row, 0)
                    table.selectRow(row)
                    break
        table.blockSignals(signals)
        table.setUpdatesEnabled(updates)


def checked_ids(table):
    return [
        table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for row in range(table.rowCount())
        if table.item(row, 0)
        and table.item(row, 0).checkState() == Qt.CheckState.Checked
        and not table.isRowHidden(row)
    ]


def mark_rows(table, checked):
    for row in range(table.rowCount()):
        if not table.isRowHidden(row) and table.item(row, 0):
            table.item(row, 0).setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
