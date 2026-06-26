from app.services.store_service import check_region_scope


class FakeScalars:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    def all(self) -> list[str]:
        return self.values


class FakeSession:
    def __init__(self, allowed_store_numbers: list[str]) -> None:
        self.allowed_store_numbers = allowed_store_numbers

    def scalars(self, _statement: object) -> FakeScalars:
        return FakeScalars(self.allowed_store_numbers)


def test_check_region_scope_blocks_unavailable_or_wrong_region_stores() -> None:
    db = FakeSession(allowed_store_numbers=["1001", "1002"])

    blocked = check_region_scope(
        db=db,  # type: ignore[arg-type]
        user_region_code="SOUTHEAST",
        target_store_numbers=["1001", "1002", "9001"],
    )

    assert blocked == ["9001"]
