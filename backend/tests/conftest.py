import importlib

try:
    pkg = importlib.import_module("app.freelancer_work")
    router_mod = importlib.import_module("app.freelancer_work.router")
    raise RuntimeError(f"DEBUG_IMPORT_OK pkg={pkg!r} router={router_mod!r}")
except Exception as exc:
    raise RuntimeError(f"DEBUG_IMPORT_ERROR type={type(exc).__name__} repr={exc!r}") from exc
