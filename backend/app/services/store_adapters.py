from collections.abc import Protocol

from app.schemas.store_batch import StoreBatchRequest


class StoreSourceAdapter(Protocol):
    source_system: str

    def load(self) -> StoreBatchRequest:
        """Load store rows from an external source into the normalized batch request shape."""


class InMemoryStoreAdapter:
    def __init__(self, payload: StoreBatchRequest) -> None:
        self.payload = payload
        self.source_system = payload.source_system

    def load(self) -> StoreBatchRequest:
        return self.payload
