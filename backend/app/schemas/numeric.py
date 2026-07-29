from decimal import Decimal
from typing import Annotated

from pydantic import Field

PositiveWholeQuantity = Annotated[
    Decimal,
    Field(gt=0, max_digits=14, decimal_places=0),
]
NonNegativeWholeQuantity = Annotated[
    Decimal,
    Field(ge=0, max_digits=14, decimal_places=0),
]
NonNegativeCurrencyAmount = Annotated[
    Decimal,
    Field(ge=0, max_digits=14, decimal_places=2),
]
