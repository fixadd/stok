from app.queries.common import apply_limit


class DummyQuery:
    def __init__(self):
        self.value = None

    def limit(self, value):
        self.value = value
        return self


def test_apply_limit_uses_default_bound():
    query = DummyQuery()
    assert apply_limit(query).value == 500


def test_apply_limit_clamps_requested_value():
    assert apply_limit(DummyQuery(), limit=5000).value == 2000
    assert apply_limit(DummyQuery(), limit=0).value == 1


def test_apply_limit_falls_back_for_invalid_input():
    assert apply_limit(DummyQuery(), limit="invalid").value == 500
