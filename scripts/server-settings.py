"""Configuration utility for IT; secrets remain in Windows DPAPI."""

import argparse
from slms.config import read_private, save_private

parser = argparse.ArgumentParser(
    description="Ajustar la escucha del servidor local. Reinicia el servicio después del cambio."
)
parser.add_argument("--bind", default="127.0.0.1")
parser.add_argument("--port", type=int, default=8765)
args = parser.parse_args()
if not 1 <= args.port <= 65535:
    parser.error("Puerto inválido")
config = read_private("connection.dat")
if not config or config["mode"] == "remote":
    parser.error("Configura primero un servidor local desde la aplicación.")
config["bind"], config["port"] = args.bind, args.port
config["url"] = f"http://127.0.0.1:{args.port}"
save_private("connection.dat", config)
print("Configuración guardada. Reinicia el servicio. Utiliza HTTPS para los clientes de red.")
