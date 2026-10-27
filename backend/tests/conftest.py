import importlib

modules = [
    "app.analytics.router", "app.audit.router", "app.auth.router", "app.calendar.router", "app.clients.router",
    "app.command_center.router", "app.company.router", "app.core.config", "app.crm.router", "app.finance.router",
    "app.freelancers.router", "app.freelancers.workflow_router",
]
try:
    loaded = [importlib.import_module(name).__name__ for name in modules]
    router_mod = importlib.import_module("app.freelancer_work.router")
    raise RuntimeError(f"DEBUG_PRE_MAIN_OK loaded={loaded} freelancer={router_mod!r}")
except Exception as exc:
    raise RuntimeError(f"DEBUG_PRE_MAIN_ERROR type={type(exc).__name__} repr={exc!r}") from exc
