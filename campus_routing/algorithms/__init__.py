"""
Routing and graph algorithms package for Smart Campus Navigation.

Exports:
    RouteResult: Data container for shortest path results.
    dijkstra_shortest_path: Custom priority-queue Dijkstra implementation.
    networkx_shortest_path: NetworkX reference implementation.
    validate_route_against_networkx: Dual-solver equivalence validation harness.
    ValidationDiscrepancyError: Raised when solvers diverge in cost or validity.
"""

from campus_routing.algorithms.dijkstra import RouteResult, dijkstra_shortest_path
from campus_routing.algorithms.networkx_solver import (
    build_networkx_graph,
    networkx_shortest_path,
)
from campus_routing.algorithms.validator import (
    ValidationDiscrepancyError,
    validate_route_against_networkx,
)

__all__ = [
    "RouteResult",
    "dijkstra_shortest_path",
    "build_networkx_graph",
    "networkx_shortest_path",
    "validate_route_against_networkx",
    "ValidationDiscrepancyError",
]
