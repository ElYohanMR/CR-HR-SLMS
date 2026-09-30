from pathlib import Path
import base64
import ctypes
from ctypes import wintypes
import json
import os
import sys


def home():
    path = Path(
        os.environ.get("SLMS_HOME", str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SamtecLockers" / "data"))
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset(name):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / "assets" / name


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]


def protect(data, decrypt=False):
    """Windows DPAPI, scoped to the current Windows user."""
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    target = Blob()
    fn = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


def save_private(name, value):
    path = home() / name
    temp = path.with_suffix(".tmp")
    temp.write_bytes(base64.b64encode(protect(json.dumps(value).encode())))
    temp.replace(path)


def read_private(name):
    path = home() / name
    if not path.exists():
        return None
    return json.loads(protect(base64.b64decode(path.read_bytes()), decrypt=True))
