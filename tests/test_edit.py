"""Value coercion + editability rules."""

import pytest

from tuivisu.edit import NotEditableError, coerce, is_editable


@pytest.mark.parametrize(
    ("dtype", "text", "expected"),
    [
        ("Boolean", "true", True),
        ("Boolean", "0", False),
        ("Boolean", "ON", True),
        ("Int32", "42", 42),
        ("Byte", "0x10", 16),
        ("Int64", "-5", -5),
        ("Double", "3.14", 3.14),
        ("Float", "-1.5", -1.5),
        ("String", "  hello ", "hello"),
    ],
)
def test_coerce_ok(dtype: str, text: str, expected: object) -> None:
    assert coerce(dtype, text) == expected


@pytest.mark.parametrize(
    ("dtype", "text"),
    [("Boolean", "maybe"), ("Int32", "1.5"), ("Double", "abc")],
)
def test_coerce_rejects_bad_input(dtype: str, text: str) -> None:
    with pytest.raises(ValueError):
        coerce(dtype, text)


def test_coerce_rejects_non_scalar_type() -> None:
    with pytest.raises(NotEditableError):
        coerce("ExtensionObject", "x")


def test_is_editable() -> None:
    assert is_editable("Boolean", False)
    assert is_editable("Int32", 0)
    assert is_editable("Double", 0.0)
    assert is_editable("String", "")
    # arrays and structs are not editable
    assert not is_editable("Byte", [0, 0, 0])
    assert not is_editable("ExtensionObject", object())
