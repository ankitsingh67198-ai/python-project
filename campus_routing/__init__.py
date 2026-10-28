"""
Smart Campus Navigation System for IIIT Kottayam.

Core reusable library containing graph data structures, custom Dijkstra routing,
NetworkX cross-validation, database persistence, and spatial utilities.
"""

__version__ = "0.1.0"
__author__ = "Senior Python Software Architect & Graph-Algorithm Engineer"

from campus_routing.config import (
    DEFAULT_DB_PATH,
    PROJECT_ROOT,
    REFERENCE_LATITUDE,
    REFERENCE_LONGITUDE,
)
from campus_routing.exceptions import (
    CampusRoutingError,
    CoordinateOutOfBoundsError,
    DatabaseError,
    DisconnectedGraphError,
    DuplicateEdgeError,
    EdgeNotFoundError,
    IncompleteCoordinateError,
    InvalidEdgeError,
    NodeNotFoundError,
    PathNotFoundError,
    ValidationError,
)

__all__ = [
    "__version__",
    "PROJECT_ROOT",
    "DEFAULT_DB_PATH",
    "REFERENCE_LATITUDE",
    "REFERENCE_LONGITUDE",
    "CampusRoutingError",
    "DatabaseError",
    "ValidationError",
    "CoordinateOutOfBoundsError",
    "IncompleteCoordinateError",
    "InvalidEdgeError",
    "NodeNotFoundError",
    "EdgeNotFoundError",
    "DuplicateEdgeError",
    "PathNotFoundError",
    "DisconnectedGraphError",
]
