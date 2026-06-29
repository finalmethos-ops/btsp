from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class WorkflowCode(StrEnum):
    BPP = "BPP"
    BPP_PURCHASING = "BPP_PURCHASING"
    IND_PURCHASING = "IND_PURCHASING"
    INDEPENDENT = "INDEPENDENT"


class WorkflowLifecycle(StrEnum):
    DRAFT = "Draft"
    TESTING = "Testing"
    STAGING = "Staging"
    PRODUCTION = "Production"
    DEPRECATED = "Deprecated"
    RETIRED = "Retired"


@dataclass(frozen=True, slots=True)
class WorkflowRegistration:
    code: WorkflowCode
    name: str
    route: str
    permission_code: str
    business_area: str | None = None
    category: str | None = None
    configuration_namespace: str | None = None
    is_active: bool = True
    lifecycle: WorkflowLifecycle = WorkflowLifecycle.PRODUCTION


class WorkflowRegistryError(ValueError):
    pass


class WorkflowRegistry:
    def __init__(self, registrations: Iterable[WorkflowRegistration]) -> None:
        entries = tuple(registrations)
        entries_by_code: dict[str, WorkflowRegistration] = {}
        for entry in entries:
            if entry.code in entries_by_code:
                raise WorkflowRegistryError(f"Duplicate workflow registration: {entry.code}")
            entries_by_code[entry.code] = entry
        self._entries = entries
        self._entries_by_code = entries_by_code

    def list(self) -> tuple[WorkflowRegistration, ...]:
        return self._entries

    def get(self, code: str | WorkflowCode) -> WorkflowRegistration | None:
        return self._entries_by_code.get(str(code))

    def require(self, code: str | WorkflowCode) -> WorkflowRegistration:
        registration = self.get(code)
        if registration is None:
            raise WorkflowRegistryError(f"Workflow is not registered: {code}")
        return registration

    def require_active(self, code: str | WorkflowCode) -> WorkflowRegistration:
        registration = self.require(code)
        if not registration.is_active:
            raise WorkflowRegistryError(f"Workflow is not active: {code}")
        return registration


WORKFLOW_REGISTRY: Final = WorkflowRegistry(
    [
        WorkflowRegistration(
            code=WorkflowCode.BPP,
            name="BPP Ordering",
            route="/workflows/bpp",
            permission_code="orders.bpp.manage",
        ),
        WorkflowRegistration(
            code=WorkflowCode.BPP_PURCHASING,
            name="BPP Purchasing",
            route="/workflows/bpp",
            permission_code="workflow.bpp.submit",
            business_area="Purchasing",
            category="BPP Ordering",
            configuration_namespace="workflow.bpp_purchasing",
        ),
        WorkflowRegistration(
            code=WorkflowCode.INDEPENDENT,
            name="Independent Ordering",
            route="/workflows/independent",
            permission_code="orders.independent.manage",
        ),
        WorkflowRegistration(
            code=WorkflowCode.IND_PURCHASING,
            name="Independent Purchasing",
            route="/workflows/independent",
            permission_code="workflow.ind.submit",
            business_area="Purchasing",
            category="Independent Ordering",
            configuration_namespace="workflow.ind_purchasing",
            lifecycle=WorkflowLifecycle.TESTING,
        ),
    ]
)

# Compatibility views for existing backend consumers.
WORKFLOW_ROUTES: Final = {entry.code: entry.route for entry in WORKFLOW_REGISTRY.list()}
WORKFLOW_PERMISSION_PREFIXES: Final = {
    WorkflowCode.BPP: "bpp",
    WorkflowCode.BPP_PURCHASING: "bpp",
    WorkflowCode.INDEPENDENT: "independent",
    WorkflowCode.IND_PURCHASING: "independent",
}
