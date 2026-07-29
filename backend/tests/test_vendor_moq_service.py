from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.catalog import CatalogProduct, CatalogVendor, VendorMOQRule
from app.schemas.catalog import VendorMOQRuleWrite
from app.services.vendor_moq_service import (
    create_rule,
    evaluate_vendor_moq,
    set_contributors,
)


def test_single_active_moq_automatically_applies_to_every_model() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            CatalogVendor(
                vendor_code="V-SINGLE",
                name="Single MOQ Vendor",
                is_active=True,
                source_file="test.xlsx",
            )
        )
        products = [
            CatalogProduct(
                product_code=f"SINGLE-{number}",
                vendor_code="V-SINGLE",
                name=f"Model {number}",
                unit_price=Decimal("100.00"),
                currency="USD",
                minimum_order_quantity=1,
                moq_rule_id=None,
                is_available=True,
                is_active=True,
                source_file="test.xlsx",
            )
            for number in (1, 2)
        ]
        db.add_all(products)
        db.commit()

        rule = create_rule(
            db,
            "V-SINGLE",
            VendorMOQRuleWrite(
                code="GLOBAL",
                name="Global MOQ",
                threshold_type="unit_quantity",
                threshold_value=2,
                is_active=True,
            ),
        )

        db.expire_all()
        assert all(product.moq_rule_id == rule.id for product in products)
        request = SimpleNamespace(
            vendor_code="V-SINGLE",
            line_items=[
                SimpleNamespace(
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                    catalog_product=products[0],
                )
            ],
        )
        assert len(evaluate_vendor_moq(db, request)) == 1


def test_moq_contributors_calculate_in_the_configured_direction_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            CatalogVendor(
                vendor_code="V-MOQ",
                name="MOQ Vendor",
                is_active=True,
                source_file="test.xlsx",
            )
        )
        appliance = VendorMOQRule(
            vendor_code="V-MOQ",
            code="APPLIANCE",
            name="Appliances",
            threshold_type="order_amount",
            threshold_value=Decimal("2500.00"),
            is_active=True,
        )
        television = VendorMOQRule(
            vendor_code="V-MOQ",
            code="TV",
            name="Televisions",
            threshold_type="order_amount",
            threshold_value=Decimal("1800.00"),
            is_active=True,
        )
        db.add_all([appliance, television])
        db.flush()
        appliance_product = CatalogProduct(
            product_code="APP-1",
            vendor_code="V-MOQ",
            name="Appliance",
            unit_price=Decimal("1000.00"),
            currency="USD",
            minimum_order_quantity=1,
            moq_rule_id=appliance.id,
            is_available=True,
            is_active=True,
            source_file="test.xlsx",
        )
        television_product = CatalogProduct(
            product_code="TV-1",
            vendor_code="V-MOQ",
            name="Television",
            unit_price=Decimal("800.00"),
            currency="USD",
            minimum_order_quantity=1,
            moq_rule_id=television.id,
            is_available=True,
            is_active=True,
            source_file="test.xlsx",
        )
        db.add_all([appliance_product, television_product])
        db.commit()

        # TVs count toward Appliances, while Appliances do not count back toward TVs.
        set_contributors(db, "V-MOQ", appliance.id, [television.id])
        request = SimpleNamespace(
            vendor_code="V-MOQ",
            line_items=[
                SimpleNamespace(
                    quantity=Decimal("1"),
                    unit_price=Decimal("1000.00"),
                    catalog_product=appliance_product,
                ),
                SimpleNamespace(
                    quantity=Decimal("2"),
                    unit_price=Decimal("800.00"),
                    catalog_product=television_product,
                ),
            ],
        )

        messages = [issue.message for issue in evaluate_vendor_moq(db, request)]

        assert not any(message.startswith("Appliances requires") for message in messages)
        assert any(message.startswith("Televisions requires") for message in messages)
