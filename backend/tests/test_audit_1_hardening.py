import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_DEVELOPMENT_SECRET, Settings


VERSIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _load_revision_metadata(path: Path) -> tuple[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                values[target.id] = ast.literal_eval(node.value)
    return values["revision"], values.get("down_revision")


def test_migration_graph_has_unique_revision_ids_and_single_head():
    revisions: dict[str, Path] = {}
    parents: dict[str, list[str]] = {}

    for path in sorted(VERSIONS_DIR.glob("*.py")):
        revision, down_revision = _load_revision_metadata(path)
        assert isinstance(revision, str)
        assert revision not in revisions, f"duplicate revision id: {revision}"
        revisions[revision] = path
        if down_revision is None:
            parents[revision] = []
        elif isinstance(down_revision, tuple):
            parents[revision] = list(down_revision)
        else:
            parents[revision] = [down_revision]

    referenced = {parent for values in parents.values() for parent in values}
    heads = set(revisions) - referenced
    assert heads == {"0032_migration_graph_reconciliation"}


def test_non_development_requires_explicit_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key=DEFAULT_DEVELOPMENT_SECRET)


def test_development_can_use_local_default_secret():
    settings = Settings(environment="development")
    assert settings.secret_key == DEFAULT_DEVELOPMENT_SECRET
