import sys
import traceback
from slms.config import home

try:
    from slms.__main__ import main
    main()
except Exception:
    (home()/"startup-error.log").write_text(traceback.format_exc(),encoding="utf-8")
    sys.exit(1)
