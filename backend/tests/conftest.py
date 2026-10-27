import importlib

modules = [
    "app.auth.router", "app.users.router", "app.roles.router", "app.audit.router", "app.command_center.router",
    "app.company.router", "app.crm.router", "app.sales.router", "app.clients.router", "app.services.router",
    "app.projects.router", "app.tasks.router", "app.freelancer_work.router",
]
try:
    loaded = [importlib.import_module(name).__name__ for name in modules]
    raise RuntimeError(f"DEBUG_IMPORT_SEQUENCE_OK loaded={loaded}")
except Exception as exc:
    raise RuntimeError(f"DEBUG_IMPORT_SEQUENCE_ERROR type={type(exc).__name__} repr={exc!r}") from exc
