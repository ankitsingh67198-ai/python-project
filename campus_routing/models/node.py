"""
Node domain model for Smart Campus Navigation.

Represents campus landmarks, building entrances, and pathway junctions.
Enforces strict coordinate completeness and domain integrity rules.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from campus_routing.config import (
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    VALID_NODE_CATEGORIES,
    VALID_PROVENANCE_VALUES,
    VALID_VERIFICATION_STATUSES,
)
from campus_routing.exceptions import (
    CoordinateOutOfBoundsError,
    IncompleteCoordinateError,
    InvalidNodeCategoryError,
    ValidationError,
)


@dataclass(frozen=True)
class Node:
    """
    Immutable domain entity representing a physical campus location or network junction.

    Attributes:
        id: Unique identifier (e.g., 'ACAD_01', 'GATE_MAIN', 'JUNC_01').
        name: Human-readable name or label.
        category: Functional category from VALID_NODE_CATEGORIES.
        latitude: Latitude in degrees North, or None if unsurveyed.
        longitude: Longitude in degrees East, or None if unsurveyed.
        elevation_m: Elevation above sea level in metres, or None if unsurveyed.
        is_landmark: True if user-selectable landmark; False if pure routing waypoint.
        description: Optional descriptive text.
        source_provenance: Provenance tier (e.g. 'OFFICIAL_INSTITUTIONAL', 'SYNTHETIC_DEMO').
        verification_status: Verification level (e.g. 'OFFICIAL_REFERENCE', 'SYNTHETIC_DEMO').
    """

    id: str
    name: str
    category: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: Optional[float] = None
    is_landmark: bool = True
    description: Optional[str] = None
    source_provenance: str = "OFFICIAL_INSTITUTIONAL"
    verification_status: str = "UNVERIFIED"

    def __post_init__(self) -> None:
        """Validates node parameters upon initialization."""
        if not self.id or not isinstance(self.id, str) or not self.id.strip():
            raise ValidationError("Node 'id' must be a non-empty string.")

        if not self.name or not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Node 'name' must be a non-empty string.")

        if self.category not in VALID_NODE_CATEGORIES:
            raise InvalidNodeCategoryError(
                f"Invalid category '{self.category}'. Must be one of: {sorted(VALID_NODE_CATEGORIES)}"
            )

        # Coordinate completeness check
        has_lat = self.latitude is not None
        has_lon = self.longitude is not None

        if has_lat != has_lon:
            raise IncompleteCoordinateError(
                f"Incomplete coordinates for node '{self.id}': latitude={self.latitude}, longitude={self.longitude}. "
                "Both coordinates must be supplied, or both must be None."
            )

        # Coordinate range check (when coordinates are supplied)
        if has_lat and has_lon:
            assert self.latitude is not None and self.longitude is not None
            if not (MIN_LATITUDE <= self.latitude <= MAX_LATITUDE):
                raise CoordinateOutOfBoundsError(
                    f"Latitude {self.latitude} for node '{self.id}' outside sanity envelope [{MIN_LATITUDE}, {MAX_LATITUDE}]"
                )
            if not (MIN_LONGITUDE <= self.longitude <= MAX_LONGITUDE):
                raise CoordinateOutOfBoundsError(
                    f"Longitude {self.longitude} for node '{self.id}' outside sanity envelope [{MIN_LONGITUDE}, {MAX_LONGITUDE}]"
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
    def has_coordinates(self) -> bool:
        """Returns True if this node possesses valid spatial coordinates."""
        return self.latitude is not None and self.longitude is not None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes node to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
            "is_landmark": self.is_landmark,
            "description": self.description,
            "source_provenance": self.source_provenance,
            "verification_status": self.verification_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        """Instantiates Node from dictionary representation."""
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            category=str(data["category"]),
            latitude=float(data["latitude"]) if data.get("latitude") is not None else None,
            longitude=float(data["longitude"]) if data.get("longitude") is not None else None,
            elevation_m=float(data["elevation_m"]) if data.get("elevation_m") is not None else None,
            is_landmark=bool(data.get("is_landmark", True)),
            description=str(data["description"]) if data.get("description") is not None else None,
            source_provenance=str(data.get("source_provenance", "OFFICIAL_INSTITUTIONAL")),
            verification_status=str(data.get("verification_status", "UNVERIFIED")),
        )
