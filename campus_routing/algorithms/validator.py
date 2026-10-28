"""
Dual-solver validation harness for Smart Campus Navigation.

Performs empirical cross-validation comparing the custom Dijkstra implementation
against NetworkX's reference solver across correctness, distance parity, and edge legality.

Note:
    This validation harness provides rigorous empirical cross-validation supported
    by parameterized test suites. It does not constitute a formal mathematical proof
    for all arbitrary infinite graph topologies.
"""

import math
from typing import Optional, Tuple

from campus_routing.algorithms.dijkstra import RouteResult, dijkstra_shortest_path
from campus_routing.algorithms.networkx_solver import networkx_shortest_path
from campus_routing.exceptions import (
    NodeNotFoundError,
    PathNotFoundError,
)
from campus_routing.models.graph import CampusGraph


class ValidationDiscrepancyError(AssertionError):
    """Raised when an empirical discrepancy is discovered between the solvers."""
    pass


def validate_route_against_networkx(
    graph: CampusGraph,
    source: str,
    target: str,
    accessible_only: bool = False,
    abs_tol: float = 1e-4,
) -> Tuple[RouteResult, RouteResult]:
    """
    Executes both the custom Dijkstra solver and the NetworkX reference solver,
    asserting algorithmic optimality and physical topological consistency.

    Args:
        graph: The CampusGraph instance.
        source: Origin node ID.
        target: Destination node ID.
        accessible_only: If True, filters out non-accessible edges.
        abs_tol: Maximum permitted difference between calculated optimal costs.

    Returns:
        Tuple of (custom_result, reference_result).

    Raises:
        ValidationDiscrepancyError: If cost parity, hop validity, or distance sum fails.
        NodeNotFoundError: If source or target does not exist (raised consistently by both).
        PathNotFoundError: If destination is unreachable (raised consistently by both).
    """
    custom_error: Optional[Exception] = None
    ref_error: Optional[Exception] = None
    custom_res: Optional[RouteResult] = None
    ref_res: Optional[RouteResult] = None

    # 1. Run custom solver
    try:
        custom_res = dijkstra_shortest_path(
            graph=graph,
            source=source,
            target=target,
            accessible_only=accessible_only,
        )
    except Exception as err:
        custom_error = err

    # 2. Run reference solver
    try:
        ref_res = networkx_shortest_path(
            graph=graph,
            source=source,
            target=target,
            accessible_only=accessible_only,
        )
    except Exception as err:
        ref_error = err

    # 3. Verify consistent exception handling
    if custom_error is not None or ref_error is not None:
        if type(custom_error) is not type(ref_error):
            raise ValidationDiscrepancyError(
                f"Solver error mismatch for query ({source} -> {target}): "
                f"Custom raised {type(custom_error).__name__} ('{custom_error}') vs "
                f"NetworkX raised {type(ref_error).__name__} ('{ref_error}')"
            )
        # If both raised the same exception type, re-raise it for caller handling
        assert custom_error is not None
        raise custom_error

    assert custom_res is not None and ref_res is not None

    # 4. Verify boundary endpoints
    if custom_res.nodes[0] != source or custom_res.nodes[-1] != target:
        raise ValidationDiscrepancyError(
            f"Custom route endpoints invalid: expected [{source} -> {target}], "
            f"got [{custom_res.nodes[0]} -> {custom_res.nodes[-1]}]"
        )
    if ref_res.nodes[0] != source or ref_res.nodes[-1] != target:
        raise ValidationDiscrepancyError(
            f"Reference route endpoints invalid: expected [{source} -> {target}], "
            f"got [{ref_res.nodes[0]} -> {ref_res.nodes[-1]}]"
        )

    # 5. Verify optimal routing cost parity within tolerance
    if not math.isclose(custom_res.total_cost, ref_res.total_cost, abs_tol=abs_tol):
        raise ValidationDiscrepancyError(
            f"Optimal routing cost discrepancy between solvers on path ({source} -> {target}): "
            f"Custom={custom_res.total_cost:.6f}, NetworkX={ref_res.total_cost:.6f}, "
            f"Difference={abs(custom_res.total_cost - ref_res.total_cost):.6e}"
        )

    # 6. Verify topological validity of every hop in custom route
    recomputed_custom_dist = 0.0
    recomputed_custom_cost = 0.0

    for i in range(len(custom_res.nodes) - 1):
        u, v = custom_res.nodes[i], custom_res.nodes[i + 1]
        edge = graph.get_edge(u, v)
        if edge is None:
            raise ValidationDiscrepancyError(
                f"Custom route contains non-existent edge ({u}, {v})"
            )
        if edge.is_blocked:
            raise ValidationDiscrepancyError(
                f"Custom route traverses blocked edge ({u}, {v})"
            )
        if accessible_only and not edge.is_accessible:
            raise ValidationDiscrepancyError(
                f"Custom route traverses non-accessible edge ({u}, {v}) under accessible_only mode"
            )
        if edge.is_directed and (edge.source_id != u or edge.target_id != v):
            raise ValidationDiscrepancyError(
                f"Custom route traverses directed edge in reverse: ({u} -> {v})"
            )

        recomputed_custom_dist += edge.distance_m
        recomputed_custom_cost += edge.effective_cost

    # 7. Verify internal distance summation consistency
    if not math.isclose(custom_res.total_distance_m, recomputed_custom_dist, abs_tol=1e-5):
        raise ValidationDiscrepancyError(
            f"Custom route reported distance ({custom_res.total_distance_m}) "
            f"does not match sum of physical edge distances ({recomputed_custom_dist})"
        )

    if not math.isclose(custom_res.total_cost, recomputed_custom_cost, abs_tol=1e-5):
        raise ValidationDiscrepancyError(
            f"Custom route reported cost ({custom_res.total_cost}) "
            f"does not match sum of edge costs ({recomputed_custom_cost})"
        )

    return custom_res, ref_res
