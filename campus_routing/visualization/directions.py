"""
Route directions module for Smart Campus Navigation.

Translates an algorithmic RouteResult into structured, human-readable
directional instructions based on graph node sequence and coordinates.

IMPORTANT: All directions are explicitly qualified as approximate straight-line
guidance when intermediate cadastral survey or curve geometry is unavailable.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional

from campus_routing.algorithms.dijkstra import RouteResult
from campus_routing.exceptions import (
    IncompleteCoordinateError,
    NodeNotFoundError,
    ValidationError,
)
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node


DIRECTIONS_DISCLAIMER: str = (
    "APPROXIMATE GUIDANCE ONLY: Step directions and bearings are computed from "
    "straight-line segment endpoints. They do not reflect subtle pathway curves, "
    "micro-topography, construction detours, or verified physical walking lines."
)


@dataclass(frozen=True)
class DirectionStep:
    """
    Structured representation of a single pathway traversal step.

    Attributes:
        step_number: 1-indexed sequential step identifier.
        from_node_id: Identifier of origin node for this step.
        from_node_name: Human-readable name of origin node.
        to_node_id: Identifier of destination node for this step.
        to_node_name: Human-readable name of destination node.
        distance_m: Measured or recorded physical ground distance in metres.
        cost: Algorithmic impedance or travel cost for this step.
        bearing_deg: Forward azimuth bearing in degrees [0, 360).
        cardinal_direction: Compass heading (e.g. 'North-East', 'South').
        instruction: Human-readable navigation text.
        surface_type: Surface classification of pathway segment.
        is_accessible: Step-free / wheelchair accessibility flag.
    """

    step_number: int
    from_node_id: str
    from_node_name: str
    to_node_id: str
    to_node_name: str
    distance_m: float
    cost: float
    bearing_deg: Optional[float]
    cardinal_direction: Optional[str]
    instruction: str
    surface_type: str = "paved"
    is_accessible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serializes step to dictionary format."""
        return {
            "step_number": self.step_number,
            "from_node_id": self.from_node_id,
            "from_node_name": self.from_node_name,
            "to_node_id": self.to_node_id,
            "to_node_name": self.to_node_name,
            "distance_m": round(self.distance_m, 2),
            "cost": round(self.cost, 2),
            "bearing_deg": round(self.bearing_deg, 1) if self.bearing_deg is not None else None,
            "cardinal_direction": self.cardinal_direction,
            "instruction": self.instruction,
            "surface_type": self.surface_type,
            "is_accessible": self.is_accessible,
        }


@dataclass(frozen=True)
class RouteDirections:
    """
    Collection of directional instructions for a complete RouteResult.

    Attributes:
        route: The underlying RouteResult object.
        steps: Sequential list of DirectionStep items.
        total_distance_m: Accumulated physical distance in metres.
        total_cost: Accumulated algorithmic routing cost.
        is_approximate: Always True for straight-line synthetic/planar segments.
        disclaimer: Clear legal and cartographic limitation notice.
    """

    route: RouteResult
    steps: List[DirectionStep] = field(default_factory=list)
    total_distance_m: float = 0.0
    total_cost: float = 0.0
    is_approximate: bool = True
    disclaimer: str = DIRECTIONS_DISCLAIMER

    @property
    def step_count(self) -> int:
        """Returns the number of movement steps in the route."""
        return len(self.steps)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes directions object to dictionary."""
        return {
            "node_sequence": self.route.nodes,
            "total_distance_m": round(self.total_distance_m, 2),
            "total_cost": round(self.total_cost, 2),
            "is_approximate": self.is_approximate,
            "disclaimer": self.disclaimer,
            "steps": [s.to_dict() for s in self.steps],
        }

    def formatted_text(self) -> str:
        """Renders directions as formatted text block."""
        lines = [
            f"=== ROUTE DIRECTIONS ({'APPROXIMATE' if self.is_approximate else 'SURVEYED'}) ===",
            f"Total Distance: {self.total_distance_m:.1f} m | Routing Cost: {self.total_cost:.1f}",
            f"Notice: {self.disclaimer}",
            "-" * 60,
        ]
        if not self.steps:
            lines.append("Origin and destination are identical. No movement required.")
        else:
            for step in self.steps:
                lines.append(f"{step.step_number}. {step.instruction}")
        return "\n".join(lines)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates initial great-circle bearing (forward azimuth) from point 1 to point 2.

    Returns:
        Bearing in degrees normalized to [0, 360).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    bearing_rad = math.atan2(y, x)
    bearing_deg = (math.degrees(bearing_rad) + 360.0) % 360.0
    return bearing_deg


def bearing_to_cardinal(bearing_deg: float) -> str:
    """
    Converts a compass bearing [0, 360) into an 8-point cardinal direction.
    """
    normalized = bearing_deg % 360.0
    compass_sectors = [
        ("North", 22.5),
        ("North-East", 67.5),
        ("East", 112.5),
        ("South-East", 157.5),
        ("South", 202.5),
        ("South-West", 247.5),
        ("West", 292.5),
        ("North-West", 337.5),
        ("North", 360.0),
    ]
    for name, upper_bound in compass_sectors:
        if normalized < upper_bound:
            return name
    return "North"


def generate_route_directions(graph: CampusGraph, route: RouteResult) -> RouteDirections:
    """
    Constructs structured step-by-step navigation instructions from a calculated RouteResult.

    Args:
        graph: The CampusGraph containing node locations and pathway attributes.
        route: The calculated RouteResult from the routing engine.

    Returns:
        RouteDirections containing sequential steps and cartographic disclaimers.

    Raises:
        ValidationError: If the route is empty.
        NodeNotFoundError: If any node ID in the route does not exist in the graph.
        IncompleteCoordinateError: If any route node lacks spatial coordinates.
    """
    if not route.nodes:
        raise ValidationError("RouteResult contains an empty node sequence.")

    # Validate all nodes exist and possess valid coordinates
    nodes: List[Node] = []
    for node_id in route.nodes:
        if not graph.has_node(node_id):
            raise NodeNotFoundError(
                f"Cannot generate directions: route node '{node_id}' does not exist in graph."
            )
        node = graph.get_node(node_id)
        if not node.has_coordinates:
            raise IncompleteCoordinateError(
                f"Cannot generate directional bearings: node '{node_id}' ({node.name}) "
                "lacks spatial coordinates."
            )
        nodes.append(node)

    # Trivial single-node route
    if len(nodes) == 1:
        return RouteDirections(
            route=route,
            steps=[],
            total_distance_m=0.0,
            total_cost=0.0,
            is_approximate=True,
            disclaimer=DIRECTIONS_DISCLAIMER,
        )

    steps: List[DirectionStep] = []
    for i in range(len(nodes) - 1):
        u = nodes[i]
        v = nodes[i + 1]

        # Retrieve edge connecting u and v
        edge = graph.get_edge(u.id, v.id)
        step_distance = edge.distance_m if edge else 0.0
        step_cost = edge.effective_cost if edge else step_distance
        surface = edge.surface_type if edge else "paved"
        accessible = edge.is_accessible if edge else True

        # Calculate directional heading
        assert u.latitude is not None and u.longitude is not None
        assert v.latitude is not None and v.longitude is not None
        bearing = calculate_bearing(u.latitude, u.longitude, v.latitude, v.longitude)
        cardinal = bearing_to_cardinal(bearing)

        # Formulate instruction
        accessibility_note = " (accessible)" if accessible else " (has stairs/unpaved)"
        instruction = (
            f"Proceed {cardinal} toward {v.name} for approximately {step_distance:.1f} m "
            f"via {surface} pathway{accessibility_note}."
        )

        step = DirectionStep(
            step_number=i + 1,
            from_node_id=u.id,
            from_node_name=u.name,
            to_node_id=v.id,
            to_node_name=v.name,
            distance_m=step_distance,
            cost=step_cost,
            bearing_deg=bearing,
            cardinal_direction=cardinal,
            instruction=instruction,
            surface_type=surface,
            is_accessible=accessible,
        )
        steps.append(step)

    return RouteDirections(
        route=route,
        steps=steps,
        total_distance_m=route.total_distance_m,
        total_cost=route.total_cost,
        is_approximate=True,
        disclaimer=DIRECTIONS_DISCLAIMER,
    )
