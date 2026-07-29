from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.invoice import VendorInvoiceLineCreate
from app.schemas.purchasing import PurchaseLineWrite
from app.schemas.receiving import PurchaseReceiptLineCreate
from app.schemas.vendor_integration import VendorASNLinePayload


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (
            PurchaseLineWrite,
            {"product_code": "SKU", "quantity": "1.5"},
        ),
        (
            PurchaseReceiptLineCreate,
            {
                "purchase_order_line_id": 1,
                "received_quantity": "1.5",
                "accepted_quantity": "1.5",
                "rejected_quantity": 0,
            },
        ),
        (
            VendorASNLinePayload,
            {"purchase_order_line_id": 1, "product_code": "SKU", "quantity": "1.5"},
        ),
    ],
)
def test_transaction_quantities_must_be_whole(schema: type, payload: dict) -> None:
    with pytest.raises(ValidationError, match="no more than 0 decimal places"):
        schema.model_validate(payload)


def test_currency_values_allow_no_more_than_two_decimal_places() -> None:
    with pytest.raises(ValidationError, match="no more than 2 decimal places"):
        VendorInvoiceLineCreate(
            line_number=1,
            purchase_order_line_id=1,
            product_code="SKU",
            quantity=1,
            unit_price=Decimal("10.001"),
            extended_amount=Decimal("10.001"),
        )
