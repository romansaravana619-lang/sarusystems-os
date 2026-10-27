def test_debug_app_package_path():
    import app
    from pathlib import Path
    roots = [Path(p) for p in app.__path__]
    assert False, f"APP_PATHS={roots}; ROOT_CONTENTS={[sorted(p.iterdir()) if p.exists() else 'missing' for p in roots]}"
