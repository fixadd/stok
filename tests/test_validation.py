from app.services.validation import non_negative_int, optional_text, positive_int, required_text


def test_required_text_trims_and_rejects_empty():
    assert required_text("  abc  ", "Ad") == ("abc", None)
    value, error = required_text("   ", "Ad")
    assert value is None
    assert error == "Ad zorunludur."


def test_required_text_enforces_max_length():
    value, error = required_text("abcdef", "Kod", max_length=3)
    assert value is None
    assert error == "Kod en fazla 3 karakter olabilir."


def test_optional_text_is_bounded():
    assert optional_text("  abc  ") == "abc"
    assert optional_text("abcdef", max_length=3) == "abc"


def test_positive_and_non_negative_integers():
    assert positive_int("5", "Adet") == (5, None)
    assert positive_int("0", "Adet")[0] is None
    assert non_negative_int("0", "Adet") == (0, None)
    assert non_negative_int("-1", "Adet")[0] is None
