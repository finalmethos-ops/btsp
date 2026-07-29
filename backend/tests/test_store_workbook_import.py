from io import BytesIO

import pytest
from openpyxl import Workbook

from app.services.store_workbook_import import (
    EXPECTED_HEADERS,
    StoreWorkbookError,
    parse_store_workbook,
)


def workbook_bytes(rows: list[tuple[object, ...]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(EXPECTED_HEADERS)
    for row in rows:
        worksheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_store_workbook_preserves_directory_details() -> None:
    payload = parse_store_workbook(
        workbook_bytes(
            [
                (
                    2,
                    "BEBE",
                    9200,
                    "BPP",
                    "Regional Manager",
                    "Owner Operator",
                    "General Manager",
                    "STORE002@EXAMPLE.COM",
                    "1644 2nd Ave SW.",
                    " Cullman ",
                    "al",
                    35055,
                )
            ]
        ),
        "admin@example.com",
    )

    row = payload.rows[0]
    assert row.store_number == "0002"
    assert row.name == "Buddy's Store 0002"
    assert row.entity_code == "BEBE"
    assert row.region_code == "9200"
    assert row.purchasing_program == "BPP"
    assert row.operating_company == "BEBE"
    assert row.regional_manager_name == "Regional Manager"
    assert row.owner_operator_name == "Owner Operator"
    assert row.general_manager_name == "General Manager"
    assert row.manager_email == "store002@example.com"
    assert row.address_line1 == "1644 2nd Ave SW."
    assert row.city == "Cullman"
    assert row.state_code == "AL"
    assert row.postal_code == "35055"


def test_store_workbook_rejects_unknown_program() -> None:
    content = workbook_bytes(
        [(2, "BEBE", 9200, "OTHER", "RM", "Owner", "GM", "a@b.com", "1 Main", "City", "AL", 1)]
    )

    with pytest.raises(StoreWorkbookError, match="Unsupported purchasing program"):
        parse_store_workbook(content, "admin@example.com")
