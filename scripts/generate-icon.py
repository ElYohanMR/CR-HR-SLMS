"""Render the existing SLMS SVG as a multi-resolution Windows ICO."""

from pathlib import Path
import struct

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main():
    assets = Path(__file__).resolve().parent.parent / "assets"
    renderer = QSvgRenderer(str(assets / "lockers.svg"))
    if not renderer.isValid():
        raise RuntimeError("No se pudo leer el icono SVG de SLMS.")
    frames = []
    for size in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        try:
            renderer.render(painter)
        finally:
            painter.end()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise RuntimeError("No se pudo generar una imagen del icono.")
        buffer.close()
        frames.append((size, bytes(data)))
    offset = 6 + 16 * len(frames)
    directory = bytearray(struct.pack("<HHH", 0, 1, len(frames)))
    for size, data in frames:
        directory.extend(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    target = assets / "lockers.ico"
    target.write_bytes(directory + b"".join(data for _, data in frames))
    print(target)


if __name__ == "__main__":
    main()
