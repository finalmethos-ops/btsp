import os
import subprocess
import sys
from pathlib import Path

import pytest

VALIDATION_MODULES = [
    "scripts.validate_001s_live",
    "scripts.validate_001t_acknowledgements",
    "scripts.validate_001t_foundation",
    "scripts.validate_001t_security",
    "scripts.validate_001u_integrity",
    "scripts.validate_001w_integrity",
]


@pytest.mark.parametrize("module_name", VALIDATION_MODULES)
def test_standalone_validation_script_loads_complete_model_registry(
    module_name: str,
) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["DATABASE_URL"] = "sqlite:///./validation-import-test.db"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                f"import {module_name}; "
                "from sqlalchemy.orm import configure_mappers; "
                "configure_mappers()"
            ),
        ],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
