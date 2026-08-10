"""Register the complete SQLAlchemy model graph for isolated test modules."""

# Some domain tests construct ``Base.metadata`` directly. Load the same complete
# registry used by standalone production validation processes.
from app.models import registry  # noqa: F401
