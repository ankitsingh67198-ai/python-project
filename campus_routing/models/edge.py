"""
Edge domain model for Smart Campus Navigation.

Represents a walkable pathway connecting two campus nodes.
Tracks physical distance in metres separately from optional algorithmic routing costs.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional, Tuple

from campus_routing.config import (
    VALID_PROVENANCE_VALUES,
    VALID_SURFACE_TYPES,
    VALID_VERIFICATION_STATUSES,
)
from campus_routing.exceptions import InvalidEdgeError, ValidationError


@dataclass(frozen=True)
class Edge:
    """
    Immutable domain entity representing a physical pathway segment.

    Attributes:
        source_id: Origin node ID.
        target_id: Destination node ID.
        distance_m: Measured or surveyed physical ground distance in metres.
        is_directed: True if path can only be traversed source -> target; False if bidirectional.
        surface_type: Surface material from VALID_SURFACE_TYPES.
        is_accessible: True if step-free / wheelchair accessible; False if has stairs/barriers.
        is_blocked: True if pathway is temporarily closed or obstructed.
        block_reason: Optional explanation for blockage (e.g. 'Construction', 'Waterlogging').
        source_provenance: Provenance tier (e.g. 'OFFICIAL_INSTITUTIONAL', 'SYNTHETIC_DEMO').
        verification_status: Verification level (e.g. 'OFFICIAL_REFERENCE', 'SYNTHETIC_DEMO').
        cost: Optional routing cost (impedance score). Defaults to physical distance when None.
    """

    source_id: str
    target_id: str
    distance_m: float
    is_directed: bool = False
    surface_type: str = "paved"
    is_accessible: bool = True
    is_blocked: bool = False
    block_reason: Optional[str] = None
    source_provenance: str = "SYNTHETIC_DEMO"
    verification_status: str = "UNVERIFIED"
    cost: Optional[float] = None

    def __post_init__(self) -> None:
        """Validates pathway attributes upon instantiation."""
        if not self.source_id or not isinstance(self.source_id, str):
            raise InvalidEdgeError("Edge 'source_id' must be a non-empty string.")

        if not self.target_id or not isinstance(self.target_id, str):
            raise InvalidEdgeError("Edge 'target_id' must be a non-empty string.")

        if self.source_id == self.target_id:
            raise InvalidEdgeError(
                f"Self-loop edge rejected: source and target are both '{self.source_id}'"
            )

        # Distance validation
        if not isinstance(self.distance_m, (int, float)) or not math.isfinite(self.distance_m):
            raise InvalidEdgeError(
                f"Physical distance must be a finite number. Received: {self.distance_m}"
            )

        if self.distance_m <= 0.0:
            raise InvalidEdgeError(
                f"Physical distance must be strictly positive (> 0.0). Received: {self.distance_m}"
            )

        # Optional cost validation
        if self.cost is not None:
            if not isinstance(self.cost, (int, float)) or not math.isfinite(self.cost):
                raise InvalidEdgeError(
                    f"Routing cost must be a finite number when provided. Received: {self.cost}"
                )
            if self.cost < 0.0:
                raise InvalidEdgeError(
                    f"Routing cost must be non-negative (>= 0.0). Received: {self.cost}"
                )

        if self.surface_type not in VALID_SURFACE_TYPES:
            raise ValidationError(
                f"Invalid surface_type '{self.surface_type}'. Must be one of: {sorted(VALID_SURFACE_TYPES)}"
            )

        if self.source_provenance not in VALID_PROVENANCE_VALUES:
            raise ValidationError(
                f"Invalid source_provenance '{self.source_provenance}'. Must be one of: {sorted(VALID_PROVENANCE_VALUES)}"
            )

        if self.verification_status not in VALID_VERIFICATION_STATUSES:
            raise ValidationError(
                f"Invalid verification_status '{self.verification_status}'. Must be one of: {sorted(VALID_VERIFICATION_STATUSES)}"
            )

    @property
    def effective_cost(self) -> float:
        """
        Returns the routing impedance weight.
        Defaults to physical distance in metres if no custom cost is configured.
        """
        return self.cost if self.cost is not None else self.distance_m

    def canonical_endpoints(self) -> Tuple[str, str]:
        """
        Returns the canonical tuple of endpoints.
        For undirected edges: (min(source_id, target_id), max(source_id, target_id)).
        For directed edges: (source_id, target_id).
        """
        if not self.is_directed:
            return (min(self.source_id, self.target_id), max(self.source_id, self.target_id))
        return (self.source_id, self.target_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes edge to dictionary representation."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "distance_m": self.distance_m,
            "is_directed": self.is_directed,
            "surface_type": self.surface_type,
            "is_accessible": self.is_accessible,
            "is_blocked": self.is_blocked,
            "block_reason": self.block_reason,
            "source_provenance": self.source_provenance,
            "verification_status": self.verification_status,
            "cost": self.cost,
            "effective_cost": self.effective_cost,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        """Instantiates Edge from dictionary representation."""
        return cls(
            source_id=str(data["source_id"]),
            target_id=str(data["target_id"]),
            distance_m=float(data["distance_m"]),
            is_directed=bool(data.get("is_directed", False)),
            surface_type=str(data.get("surface_type", "paved")),
            is_accessible=bool(data.get("is_accessible", True)),
            is_blocked=bool(data.get("is_blocked", False)),
            block_reason=str(data["block_reason"]) if data.get("block_reason") is not None else None,
            source_provenance=str(data.get("source_provenance", "SYNTHETIC_DEMO")),
            verification_status=str(data.get("verification_status", "UNVERIFIED")),
            cost=float(data["cost"]) if data.get("cost") is not None else None,
        )
