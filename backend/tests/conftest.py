import importlib
import traceback

try:
    importlib.import_module("app.main")
    raise RuntimeError("DEBUG_MAIN_IMPORT_OK")
except Exception as exc:
    raise RuntimeError(f"DEBUG_MAIN_IMPORT_ERROR {type(exc).__name__}: {exc}\n{traceback.format_exc()}") from exc
