from app.services.authz import is_safe_redirect_target


def test_redirect_rejects_external_and_protocol_relative_targets():
    assert not is_safe_redirect_target("https://evil.example/path")
    assert not is_safe_redirect_target("http://evil.example/path")
    assert not is_safe_redirect_target("//evil.example/path")
    assert not is_safe_redirect_target("javascript:alert(1)")
    assert not is_safe_redirect_target("\\\\evil.example\\path")
    assert not is_safe_redirect_target("/\\evil.example")


def test_redirect_accepts_local_absolute_paths():
    assert is_safe_redirect_target("/dashboard")
    assert is_safe_redirect_target("/giris?next=/dashboard")
    assert is_safe_redirect_target("/envanter?filter=aktif&page=2")


def test_redirect_rejects_empty_or_non_string_targets():
    assert not is_safe_redirect_target("")
    assert not is_safe_redirect_target(None)
    assert not is_safe_redirect_target(123)
