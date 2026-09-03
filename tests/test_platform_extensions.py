from pathlib import Path


def test_platform_extension_migration_exists_and_is_postgres_oriented():
    migration = Path("migrations/versions/0009_platform_extensions.py").read_text(encoding="utf-8")
    for table in ("configuration_rules", "lookup_dependencies", "report_definitions", "notification_rules", "api_tokens"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration
    assert "jsonb" in migration
    assert "sqlite" not in migration.lower()


def test_platform_routes_are_registered():
    init = Path("app/__init__.py").read_text(encoding="utf-8")
    routes = Path("app/routes/platform_config.py").read_text(encoding="utf-8")
    assert "register_platform_config_routes" in init
    assert "/api/platform/rules" in routes
    assert "/api/platform/dependencies" in routes
    assert "/api/platform/reports" in routes
    assert "/api/platform/notifications" in routes
