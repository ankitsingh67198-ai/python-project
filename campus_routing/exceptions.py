"""
Domain-specific exceptions for Smart Campus Navigation System.
"""


class CampusRoutingError(Exception):
    """Base exception for all errors in the Campus Routing application."""
    pass


class DatabaseError(CampusRoutingError):
    """Raised when a database operation or transaction fails."""
    pass


class ValidationError(CampusRoutingError):
    """Raised when data fails domain validation or structural integrity rules."""
    pass


class CoordinateOutOfBoundsError(ValidationError):
    """Raised when latitude or longitude falls outside the engineering sanity envelope."""
    pass


class IncompleteCoordinateError(ValidationError):
    """Raised when one coordinate (lat or lon) is provided but the other is null."""
    pass


class InvalidNodeCategoryError(ValidationError):
    """Raised when an unrecognized node category is specified."""
    pass


class InvalidEdgeError(ValidationError):
    """Raised when edge parameters are invalid (e.g. self-loop, non-positive distance)."""
    pass


class NodeNotFoundError(CampusRoutingError):
    """Raised when a requested node does not exist in the database or graph."""
    pass


class EdgeNotFoundError(CampusRoutingError):
    """Raised when a requested edge does not exist in the database or graph."""
    pass


class DuplicateEdgeError(ValidationError):
    """Raised when attempting to insert an edge that already exists."""
    pass


class PathNotFoundError(CampusRoutingError):
    """Raised when no navigable path connects origin and destination nodes."""
    pass


class DisconnectedGraphError(CampusRoutingError):
    """Raised when graph partition or blockage renders the destination unreachable."""
    pass
