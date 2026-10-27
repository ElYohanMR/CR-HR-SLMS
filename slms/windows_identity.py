"""Windows shell identity for the desktop application."""

import ctypes
import logging
import sys


APP_USER_MODEL_ID = "Samtec.SLMS.Desktop"


def configure_taskbar_identity():
    """Set a stable, version-independent identity before creating any windows."""
    if sys.platform != "win32":
        return
    try:
        set_app_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        set_app_id.argtypes = [ctypes.c_wchar_p]
        set_app_id.restype = ctypes.c_long
        result = set_app_id(APP_USER_MODEL_ID)
        if result < 0:
            logging.getLogger(__name__).warning("Windows taskbar identity failed: HRESULT %s", result)
    except (AttributeError, OSError):
        logging.getLogger(__name__).warning("Windows taskbar identity unavailable", exc_info=True)
