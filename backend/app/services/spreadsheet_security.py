from collections.abc import Iterable
from typing import Any


def spreadsheet_safe_cell(value: Any) -> Any:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


def spreadsheet_safe_row(values: Iterable[Any]) -> list[Any]:
    return [spreadsheet_safe_cell(value) for value in values]
