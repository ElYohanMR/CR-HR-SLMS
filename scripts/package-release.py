"""Bundle a verified desktop build, documentation, licenses and committed source."""

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED
from slms import __version__

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--preview-profile", type=Path, required=True)
parser.add_argument("--release", type=Path)
args = parser.parse_args()
project = Path(__file__).resolve().parent.parent
release = args.release or Path(os.environ["LOCALAPPDATA"]) / "SamtecLockers/release/SamtecLockers"
assert (release / "SamtecLockers.exe").is_file()
assert json.loads((args.preview_profile / "self-test.json").read_text())["ok"]
args.output.mkdir(parents=True, exist_ok=True)

for source, target in (
    ("docs/OPERACION.md", "Guia-de-uso.md"),
    ("docs/TI.md", "Guia-TI.md"),
    ("docs/VALIDACION.md", "Validacion.md"),
):
    shutil.copy2(project / source, release / target)
(release / "LEEME.md").write_text(
    f"# Samtec Lockers {__version__}\n\n"
    "Extrae toda esta carpeta y abre SamtecLockers.exe. Conserva _internal junto al ejecutable.\n\n"
    "El primer arranque permite configurar PostgreSQL, conectar al servidor de TI o usar una demostración. "
    "Introduce las contraseñas directamente en el asistente. Configurar conexion.cmd vuelve a abrirlo.\n\n"
    "La configuración y los datos locales se guardan en %LOCALAPPDATA%/SamtecLockers/data. "
    "Actualizar esta carpeta del programa conserva esa configuración.\n\n"
    "Consulta Guia-de-uso.md, Guia-TI.md y Validacion.md. Las licencias de dependencias están en licencias; "
    "la procedencia del logo y la fuente está en _internal/assets/README.md.\n",
    encoding="utf-8",
)
(release / "Configurar conexion.cmd").write_text(
    '@echo off\ncd /d "%~dp0"\nstart "" "%~dp0SamtecLockers.exe" --configure\n', encoding="ascii"
)
for distribution in metadata.distributions():
    for file in distribution.files or []:
        if ".dist-info/" not in file.as_posix():
            continue
        if not any(part.lower().startswith(("license", "licence", "copying", "notice")) for part in file.parts):
            continue
        source = Path(distribution.locate_file(file))
        if source.is_file():
            target = release / "licencias" / distribution.metadata["Name"] / Path(*file.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

binary_zip = args.output / "Samtec-Lockers-Windows.zip"
with ZipFile(binary_zip, "w", ZIP_DEFLATED) as archive:
    for path in sorted(release.rglob("*")):
        if path.is_file():
            archive.write(path, "SamtecLockers/" + path.relative_to(release).as_posix())
source_zip = args.output / "Samtec-Lockers-Codigo.zip"
subprocess.run(
    ["git", "archive", "--format=zip", "--prefix=SamtecLockers-Codigo/", "-o", str(source_zip), "HEAD"],
    cwd=project,
    check=True,
)
for name in (
    "configuracion",
    "acceso",
    "resumen",
    "mapa",
    "inventario",
    "inventario-menu",
    "bloque-derecha-izquierda",
    "empleados",
    "baja",
    "devolucion",
    "avisos-hr",
    "fila-bloques",
    "revisiones-fisicas",
    "conflictos",
    "seleccion-multiple",
    "eliminacion-definitiva",
    "mapa-deshacer",
    "mapa-deshacer-menu",
    "opciones-apariencia",
    "opciones-mapa",
    "opciones-bloques",
    "opciones-empleados",
    "opciones-125",
    "mapa-contornos",
):
    shutil.copy2(args.preview_profile / (name + ".png"), args.output / ("Samtec-Lockers-" + name + ".png"))
shutil.copy2(project / "docs/OPERACION.md", args.output / "Samtec-Lockers-Guia-de-uso.md")
shutil.copy2(project / "docs/VALIDACION.md", args.output / "Samtec-Lockers-Validacion.md")
(args.output / "SHA256.json").write_text(
    json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (binary_zip, source_zip)}, indent=2),
    encoding="utf-8",
)
print("Created " + str(binary_zip))
print("Created " + str(source_zip))
