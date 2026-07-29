from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.catalog import CatalogProduct, CatalogProductCostHistory
from app.models.identity import User
from app.schemas.catalog import CatalogProductCostHistoryResponse, CatalogProductResponse

router = APIRouter(prefix="/model-catalog", tags=["model-catalog"])


@router.get("", response_model=list[CatalogProductResponse])
def search_model_catalog(
    search: str | None = Query(default=None, max_length=160),
    vendor_code: str | None = Query(default=None, max_length=64),
    department: str | None = Query(default=None, max_length=128),
    product_category_code: str | None = Query(default=None, max_length=128),
    classification: str = Query(default="all", pattern="^(all|clump|part_of_clump|single_item)$"),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.models.read")),
) -> list[CatalogProductResponse]:
    statement = (
        select(CatalogProduct)
        .where(CatalogProduct.model_number.is_not(None))
        .order_by(
            case(
                (CatalogProduct.is_clump.is_(True), 0),
                (CatalogProduct.part_of_clump.is_(False), 1),
                else_=2,
            ),
            CatalogProduct.model_number,
        )
        .limit(limit)
    )
    if vendor_code:
        statement = statement.where(CatalogProduct.vendor_code == vendor_code)
    if department:
        statement = statement.where(CatalogProduct.department == department)
    if product_category_code:
        statement = statement.where(CatalogProduct.product_category_code == product_category_code)
    if classification == "clump":
        statement = statement.where(CatalogProduct.is_clump.is_(True))
    elif classification == "part_of_clump":
        statement = statement.where(CatalogProduct.part_of_clump.is_(True))
    elif classification == "single_item":
        statement = statement.where(
            CatalogProduct.is_clump.is_(False),
            CatalogProduct.part_of_clump.is_(False),
        )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                CatalogProduct.product_code.ilike(term),
                CatalogProduct.name.ilike(term),
                CatalogProduct.model_number.ilike(term),
                CatalogProduct.brand.ilike(term),
                CatalogProduct.department.ilike(term),
                CatalogProduct.product_category_code.ilike(term),
            )
        )
    return list(db.scalars(statement).all())


@router.get(
    "/{product_code}/cost-history",
    response_model=list[CatalogProductCostHistoryResponse],
)
def read_model_cost_history(
    product_code: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.models.read")),
) -> list[CatalogProductCostHistoryResponse]:
    exists = db.scalar(select(CatalogProduct.id).where(CatalogProduct.product_code == product_code))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return list(
        db.scalars(
            select(CatalogProductCostHistory)
            .where(CatalogProductCostHistory.product_code == product_code)
            .order_by(CatalogProductCostHistory.effective_from.desc())
        ).all()
    )
