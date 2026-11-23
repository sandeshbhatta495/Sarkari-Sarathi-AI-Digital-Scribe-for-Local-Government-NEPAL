"""Date helpers: AD (Gregorian) -> BS (Bikram Sambat), shown in Nepali digits.

Uses the nepali-datetime package. Nepal has no daylight saving time, so
Kathmandu time is a fixed UTC+05:45 offset.
"""
import datetime
import re

import nepali_datetime

NEPAL_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=45), "NPT")

_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DateError(ValueError):
    """A date value is missing, badly formatted, or outside the supported range."""


def to_nepali_digits(value):
    """Replace ASCII digits 0-9 with Nepali digits. Other characters stay as they are."""
    return str(value).translate(_DIGITS)


def ad_to_bs_nepali(value, field=""):
    """Convert an AD date to a BS date text like '२०८३-०८-०७'.

    value: 'YYYY-MM-DD' text (what the HTML date input sends) or a datetime.date.
    field: optional field name, used only in error messages.
    Raises DateError for a missing, malformed or out-of-range date.
    """
    label = f" ({field})" if field else ""

    if isinstance(value, datetime.datetime):
        ad = value.date()
    elif isinstance(value, datetime.date):
        ad = value
    else:
        text = "" if value is None else str(value).strip()
        if not text:
            raise DateError(f"Date is required{label}")
        if not _ISO_DATE.match(text):
            raise DateError(f"Date must be in YYYY-MM-DD format{label}: {text!r}")
        try:
            ad = datetime.date.fromisoformat(text)
        except ValueError as exc:
            raise DateError(f"Invalid date{label}: {text!r}") from exc

    try:
        bs = nepali_datetime.date.from_datetime_date(ad)
    except Exception as exc:
        raise DateError(f"Date is outside the supported range{label}: {ad.isoformat()}") from exc

    return to_nepali_digits(f"{bs.year:04d}-{bs.month:02d}-{bs.day:02d}")


def today_bs_nepali(now=None):
    """Today's BS date in Nepali digits, using Kathmandu time.

    now: optional datetime, for tests. A naive datetime is treated as Kathmandu time.
    """
    now = now or datetime.datetime.now(NEPAL_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=NEPAL_TZ)
    return ad_to_bs_nepali(now.astimezone(NEPAL_TZ).date())
