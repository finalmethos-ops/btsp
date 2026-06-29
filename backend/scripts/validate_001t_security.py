import json
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.identity import Role
from app.models.vendor_integration import VendorConnectorExecution, VendorEndpoint
from app.services.vendor_connector_security import configuration_contains_secret

REQUIRED_SYSTEM_PERMISSIONS = {
    "vendor.integrations.manage",
    "vendor.integrations.read",
    "vendor.integrations.ingest",
    "vendor.acknowledgements.process",
    "vendor.logistics.process",
    "vendor.connectors.operate",
    "vendor.connectors.work",
}


def main() -> None:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        endpoints = list(db.scalars(select(VendorEndpoint)).all())
        executions = list(db.scalars(select(VendorConnectorExecution)).all())
        system_role = db.scalar(select(Role).where(Role.code == "SYSTEM_ADMIN"))

        unsafe_endpoint_ids = [
            endpoint.id
            for endpoint in endpoints
            if configuration_contains_secret(endpoint.configuration)
        ]
        invalid_lease_ids = [
            execution.id
            for execution in executions
            if execution.status == "running"
            and (
                execution.lease_token_hash is None
                or len(execution.lease_token_hash) != 64
                or execution.lease_expires_at is None
            )
        ]
        expired_lease_ids = [
            execution.id
            for execution in executions
            if execution.status == "running"
            and execution.lease_expires_at is not None
            and execution.lease_expires_at.replace(tzinfo=execution.lease_expires_at.tzinfo or UTC)
            <= now
        ]
        system_permissions = (
            {permission.code for permission in system_role.permissions}
            if system_role is not None
            else set()
        )
        missing_permissions = sorted(REQUIRED_SYSTEM_PERMISSIONS - system_permissions)

        assert not unsafe_endpoint_ids, "Endpoint configuration contains credential material"
        assert not invalid_lease_ids, "Running connector executions have invalid lease digests"
        assert not expired_lease_ids, "Expired connector leases require scheduler/worker recovery"
        assert not missing_permissions, "SYSTEM_ADMIN is missing vendor permissions"

        print(
            json.dumps(
                {
                    "checked_at": now.isoformat(),
                    "dead_letter_count": sum(
                        execution.status == "dead_letter" for execution in executions
                    ),
                    "endpoint_count": len(endpoints),
                    "execution_count": len(executions),
                    "running_lease_count": sum(
                        execution.status == "running" for execution in executions
                    ),
                    "status": "ok",
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
