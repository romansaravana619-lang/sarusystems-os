import app
from pathlib import Path

roots = [Path(p) for p in app.__path__]
raise RuntimeError(f"DEBUG_APP_PATH={roots}; ROOT_CONTENTS={[sorted(p.name for p in root.iterdir()) if root.exists() else 'missing' for root in roots]}")
