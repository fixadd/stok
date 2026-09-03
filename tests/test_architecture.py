from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
MIGRATIONS = ROOT / "migrations"


def _calls_in(path: Path, names: set[str]) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.attr
            if isinstance(func, ast.Attribute)
            else func.id
            if isinstance(func, ast.Name)
            else None
        )
        if name in names:
            hits.append((name, node.lineno))
    return hits


def test_runtime_routes_do_not_create_or_drop_schema():
    forbidden = {"create_all", "drop_all"}
    runtime_files = [APP / "legacy.py"] + sorted((APP / "routes").glob("*.py")) + sorted(
        (APP / "services").glob("*.py")
    )
    hits = []
    for path in runtime_files:
        hits.extend((path.relative_to(ROOT), *hit) for hit in _calls_in(path, forbidden))
    assert not hits, f"Runtime schema mutation calls remain: {hits}"


def test_schema_bootstrap_is_confined_to_migration_layer():
    baseline = MIGRATIONS / "versions" / "0001_baseline.py"
    text = baseline.read_text(encoding="utf-8")
    assert "db.metadata.create_all" in text


def test_services_do_not_import_legacy():
    for path in sorted((APP / "services").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "from ..legacy" not in text
        assert "from app.legacy" not in text


def test_runtime_does_not_depend_on_sqlite():
    runtime_files = [APP / "config.py", APP / "legacy.py"] + sorted(
        (APP / "routes").glob("*.py")
    ) + sorted((APP / "services").glob("*.py"))
    forbidden = ("sqlite:///", "sqlite+", "sqlite3")
    hits = []
    for path in runtime_files:
        source = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            if token in source:
                hits.append((str(path.relative_to(ROOT)), token))
    assert not hits, f"SQLite runtime dependencies remain: {hits}"


def test_docker_compose_uses_persistent_postgres_volume():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgres_data:/var/lib/postgresql/data" in compose
    assert "postgres:17" in compose
    assert "DATABASE_URL:" in compose
