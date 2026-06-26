from enum import StrEnum
from typing import Final


class WorkflowCode(StrEnum):
    BPP = "BPP"
    INDEPENDENT = "INDEPENDENT"


WORKFLOW_ROUTES: Final[dict[str, str]] = {
    WorkflowCode.BPP: "/workflows/bpp",
    WorkflowCode.INDEPENDENT: "/workflows/independent",
}

WORKFLOW_PERMISSION_PREFIXES: Final[dict[str, str]] = {
    WorkflowCode.BPP: "bpp",
    WorkflowCode.INDEPENDENT: "independent",
}
