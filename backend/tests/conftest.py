import app
from pathlib import Path

print(f"DEBUG_APP_PATH={list(app.__path__)}")
print(f"DEBUG_APP_CHILDREN={[str(p) for root in app.__path__ for p in sorted(Path(root).iterdir())]}")
