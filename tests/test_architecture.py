from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


def _calls_in(path: Path, names: set[str]) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
        if name in names:
            hits.append((name, node.lineno))
    return hits


def test_schema_creation_is_owned_by_migrations():
    forbidden = {"create_all", "drop_all"}
    hits = _calls_in(APP / "legacy.py", forbidden)
    assert not hits, f"Legacy schema mutation calls remain: {hits}"


def test_services_do_not_import_legacy():
    for path in sorted((APP / "services").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "from ..legacy" not in text
        assert "from app.legacy" not in text


def test_docker_compose_uses_persistent_postgres_volume():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgres_data:/var/lib/postgresql/data" in compose
    assert "postgres:17" in compose
    assert "DATABASE_URL:" in compose
