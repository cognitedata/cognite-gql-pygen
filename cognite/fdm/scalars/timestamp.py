from __future__ import annotations

import logging
import re
from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, TypeVar

logger = logging.getLogger(__name__)


__all__ = [
    "Timestamp",
]


TimestampParsable = TypeVar("TimestampParsable", str, datetime)


class _Timestamp(str):
    """
    String in the format 'YYYY-MM-DDTHH:MM:SS[.millis][Z|time zone]' with optional milliseconds having precision
    of 1-3 decimal digits and optional timezone with format ±HH:MM, ±HHMM, ±HH or Z, where Z represents UTC, Year
    must be between 0001 and 9999.

    This class is a custom Pydantic type:

    >>> from pydantic import BaseModel
    >>> class Foo(BaseModel):
    ...     bar: Timestamp

    # timezones:
    >>> Foo(bar="2023-04-05T06:07:08")
    Foo(bar=Timestamp('2023-04-05T06:07:08'))
    >>> Foo(bar="2023-04-05T06:07:08+09:00")
    Foo(bar=Timestamp('2023-04-05T06:07:08+09:00'))
    >>> Foo(bar="2023-04-05T06:07:08+0900")
    Foo(bar=Timestamp('2023-04-05T06:07:08+09:00'))
    >>> Foo(bar="2023-04-05T06:07:08+09")
    Foo(bar=Timestamp('2023-04-05T06:07:08+09:00'))
    >>> Foo(bar="2023-04-05T06:07:08Z")
    Foo(bar=Timestamp('2023-04-05T06:07:08+00:00'))

    # milliseconds:
    >>> Foo(bar="2023-04-05T06:07:08.123456")
    Foo(bar=Timestamp('2023-04-05T06:07:08.123'))
    >>> Foo(bar="2023-04-05T06:07:08.1256Z")
    Foo(bar=Timestamp('2023-04-05T06:07:08.126+00:00'))
    >>> Foo(bar="2023-04-05T06:07:08.12Z")
    Foo(bar=Timestamp('2023-04-05T06:07:08.120+00:00'))

    # edge years:
    >>> Foo(bar="9999-04-05T06:07:08.12Z")
    Foo(bar=Timestamp('9999-04-05T06:07:08.120+00:00'))
    >>> Foo(bar="0001-04-05T06:07:08.12Z")
    Foo(bar=Timestamp('0001-04-05T06:07:08.120+00:00'))

    # pass in datetime objects:
    >>> from datetime import datetime, timedelta, timezone
    >>> Foo(bar=datetime(2023, 4, 5, 6, 7, 8))
    Foo(bar=Timestamp('2023-04-05T06:07:08.000'))
    >>> Foo(bar=datetime(2023, 4, 5, 6, 7, 8, 123456))
    Foo(bar=Timestamp('2023-04-05T06:07:08.123'))
    >>> Foo(bar=datetime(2023, 4, 5, 6, 7, 8, 345678))
    Foo(bar=Timestamp('2023-04-05T06:07:08.346'))
    >>> Foo(bar=datetime(2023, 4, 5, 6, 7, 8, 345678, timezone(timedelta(hours=-5), 'EST')))
    Foo(bar=Timestamp('2023-04-05T06:07:08.346-05:00'))
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        logger.warning(f"modify schema: {field_schema}")

    @classmethod
    def validate(cls, value: TimestampParsable) -> _Timestamp:
        if isinstance(value, str):
            # Add minutes to the timezone offset if missing
            if re.match(r".*[+-]\d\d$", value):
                value = f"{value}00"

            formats = (
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
            )

            def try_parse():
                for fmt in formats:
                    with suppress(ValueError):
                        return datetime.strptime(value, fmt), fmt
                raise ValueError(f"Cannot parse Timestamp: {value}")

            parsed_value, matched_format = try_parse()
            is_subsecond = ".%f" in matched_format

        else:
            parsed_value = value  # assuming datetime
            is_subsecond = True  # cannot distinguish between None and 0 for microseconds

        # Milliseconds need some special treatment:
        microseconds = parsed_value.microsecond
        str_value = parsed_value.replace(microsecond=0).isoformat()
        if is_subsecond:
            milliseconds = round(microseconds / 1000)
            str_value = f"{str_value[:19]}.{milliseconds:03}{str_value[19:]}"

        return cls(str_value)

    def __repr__(self) -> str:
        return f"Timestamp({super().__repr__()})"

    def datetime(self) -> datetime:
        return datetime.fromisoformat(self)


# Keeping mypy and strawberry and pydantic happy:

_Timestamp.__name__ = "Timestamp"

if TYPE_CHECKING:
    Timestamp = Annotated[TimestampParsable, _Timestamp]
else:
    Timestamp = _Timestamp
