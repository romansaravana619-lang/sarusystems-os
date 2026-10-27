import importlib

try:
    importlib.import_module("app.freelancers.workflow_router")
    router_mod = importlib.import_module("app.freelancer_work.router")
    raise RuntimeError(f"DEBUG_IMPORT_ORDER_OK router={router_mod!r}")
except Exception as exc:
    raise RuntimeError(f"DEBUG_IMPORT_ORDER_ERROR type={type(exc).__name__} repr={exc!r}") from exc
