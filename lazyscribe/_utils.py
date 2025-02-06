"""Util methods."""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, no_type_check

from attrs import asdict, fields, filters

from lazyscribe.artifacts.base import Artifact


@no_type_check
def serializer(inst, field, value):  # noqa: ANN001, ANN202
    """Convert datetime and dependencies for :py:meth:`attrs.asdict`."""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if field is not None and field.name == "dependencies":
        new = [f"{exp.project}|{exp.slug}" for exp in value.values()]
        return new
    if field is not None and field.name == "tests":
        new = [asdict(test) for test in value]
        return new
    if field is not None and field.name == "artifacts":
        new = list(serialize_artifacts(value))
        return new

    return value


def serialize_artifacts(alist: list[Artifact]) -> Iterator[dict[str, Any]]:
    """Serialize list of artifacts."""
    yield from (
        {
            **asdict(
                artifact,
                filter=filters.exclude(
                    fields(type(artifact)).value,
                    fields(type(artifact)).writer_kwargs,
                    fields(type(artifact)).dirty,
                ),
                value_serializer=lambda _, __, value: value.isoformat(
                    timespec="seconds"
                )
                if isinstance(value, datetime)
                else value,
            ),
            "handler": artifact.alias,
        }
        for artifact in alist
    )


def utcnow() -> datetime:
    """Return the naive datetime now in UTC.

    Returns
    -------
    datetime.datetime
        Now in UTC, without timezone info.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
