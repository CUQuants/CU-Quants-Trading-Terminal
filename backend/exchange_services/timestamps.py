from decimal import Decimal, InvalidOperation


def seconds_to_milliseconds(value: object) -> str:
    if value is None or isinstance(value, bool):
        return ""
    try:
        seconds = Decimal(str(value))
        if not seconds.is_finite() or seconds < 0:
            return ""
        return str(int(seconds * 1000))
    except (InvalidOperation, ValueError, OverflowError):
        return ""
