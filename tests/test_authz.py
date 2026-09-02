from types import SimpleNamespace

from app.services.authz import (
    SYSTEM_ROLE_LEVELS,
    current_actor_name,
    get_system_role,
    has_system_role,
    is_safe_redirect_target,
)


def test_system_role_levels_are_ordered():
    assert SYSTEM_ROLE_LEVELS["user"] < SYSTEM_ROLE_LEVELS["admin"] < SYSTEM_ROLE_LEVELS["superadmin"]


def test_has_system_role_allows_equal_or_higher_role():
    user = SimpleNamespace(system_role="admin")
    assert has_system_role(user, "user") is True
    assert has_system_role(user, "admin") is True
    assert has_system_role(user, "superadmin") is False


def test_get_system_role_defaults_to_user():
    assert get_system_role(None) == "user"
    assert get_system_role(SimpleNamespace(system_role=None)) == "user"
    assert get_system_role(SimpleNamespace(system_role=" ADMIN ")) == "admin"


def test_safe_redirect_accepts_only_local_paths():
    assert is_safe_redirect_target("/dashboard") is True
    assert is_safe_redirect_target("/login?next=/dashboard") is True
    assert is_safe_redirect_target("https://example.com") is False
    assert is_safe_redirect_target("//example.com") is False
    assert is_safe_redirect_target("") is False
    assert is_safe_redirect_target(None) is False


def test_current_actor_name_uses_session_user(monkeypatch):
    user = SimpleNamespace(first_name="Ada", last_name="Lovelace", username="ada")
    monkeypatch.setattr("app.services.authz.get_active_user", lambda: user)
    assert current_actor_name() == "Ada Lovelace"


def test_current_actor_name_falls_back_to_username_or_system(monkeypatch):
    monkeypatch.setattr(
        "app.services.authz.get_active_user",
        lambda: SimpleNamespace(first_name="", last_name="", username="ada"),
    )
    assert current_actor_name() == "ada"

    monkeypatch.setattr("app.services.authz.get_active_user", lambda: None)
    assert current_actor_name() == "Sistem"
