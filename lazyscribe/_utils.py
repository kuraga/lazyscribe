"""Util methods."""

from datetime import datetime, timezone
from typing import Any

from attrs import Attribute, asdict


def serializer(inst: type, field: "Attribute[Any]", value: Any) -> Any:
    """Datetime and dependencies converter for :meth:`attrs.asdict`.

    Parameters
    ----------
    inst : type
        Included for compatibility.
    field : attrs.Attribute[Any]
        The field name.
    value : Any
        The field value.

    Returns
    -------
    Any
        Converted value for easy serialization.
    """
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if field is not None and field.name == "dependencies":
        deps: list[str] = [f"{exp.project}|{exp.slug}" for exp in value.values()]
        return deps
    if field is not None and field.name == "tests":
        tests: list[dict[str, Any]] = [asdict(test) for test in value]
        return tests

    return value


def utcnow() -> datetime:
    """Return the naive datetime now in UTC.

    Returns
    -------
    datetime.datetime
        Now in UTC, without timezone info.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
