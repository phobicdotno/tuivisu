"""Parsing of user-typed edit values into the PLC's data type.

Keeps the (text -> typed value) rules in one tested place, separate from the
UI. Only scalar IEC types are editable; arrays and structs are not.
"""

from __future__ import annotations

_BOOL_TRUE = {"1", "true", "t", "yes", "y", "on"}
_BOOL_FALSE = {"0", "false", "f", "no", "n", "off"}

_BOOL_TYPES = {"Boolean"}
_INT_TYPES = {
    "SByte",
    "Byte",
    "Int16",
    "UInt16",
    "Int32",
    "UInt32",
    "Int64",
    "UInt64",
}
_FLOAT_TYPES = {"Float", "Double"}
_STRING_TYPES = {"String"}

_SCALAR_TYPES = _BOOL_TYPES | _INT_TYPES | _FLOAT_TYPES | _STRING_TYPES


class NotEditableError(ValueError):
    """The variable's data type cannot be edited as a scalar."""


def is_editable(data_type: str, value: object) -> bool:
    """True when a value of this OPC UA variant type can be typed and written."""
    if isinstance(value, list | tuple):
        return False  # arrays
    return data_type in _SCALAR_TYPES


def coerce(data_type: str, text: str) -> bool | int | float | str:
    """Convert typed text to a value of ``data_type``; raise on bad input."""
    text = text.strip()
    if data_type in _BOOL_TYPES:
        low = text.lower()
        if low in _BOOL_TRUE:
            return True
        if low in _BOOL_FALSE:
            return False
        raise ValueError(f"expected a boolean (true/false), got {text!r}")
    if data_type in _INT_TYPES:
        try:
            return int(text, 0)
        except ValueError as exc:
            raise ValueError(f"expected an integer, got {text!r}") from exc
    if data_type in _FLOAT_TYPES:
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(f"expected a number, got {text!r}") from exc
    if data_type in _STRING_TYPES:
        return text
    raise NotEditableError(f"{data_type} is not an editable scalar type")
