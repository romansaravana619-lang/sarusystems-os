import app
import importlib.util
from pathlib import Path

roots = [Path(p) for p in app.__path__]
fw = roots[0] / "freelancer_work"
raise RuntimeError(f"DEBUG_APP_PATH={roots}; FW_EXISTS={fw.exists()}; FW_CONTENTS={[p.name for p in fw.iterdir()] if fw.exists() else 'missing'}; FW_SPEC={importlib.util.find_spec('app.freelancer_work')}")
