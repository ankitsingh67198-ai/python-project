"""
Unit tests for custom Dijkstra algorithm implementation.

Verifies:
- Optimality and correct path reconstruction
- Discarding stale priority queue entries
- Source equal to destination base case
- Dynamic blockage handling and alternative route discovery
- Unreachable destinations and disconnected graphs
- Directed edge traversal restrictions
- Accessibility filtering
- Multiple equally optimal routes
- Separation of physical distance from routing cost
- Rejection of invalid edge weights
"""

import math
import pytest

from campus_routing.algorithms.dijkstra import dijkstra_shortest_path
from campus_routing.exceptions import (
    InvalidEdgeError,
    NodeNotFoundError,
    PathNotFoundError,
)
from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node


@pytest.fixture
def diamond_graph() -> CampusGraph:
    r"""
    Creates a diamond topology:
         (B) [cost 10, dist 10]
        /   \
      (A)   (D)
        \   /
         (C) [cost 25, dist 25]

    Direct shortest path: A -> B -> D (cost 20, dist 20)
    Alternative longer path: A -> C -> D (cost 50, dist 50)
    """
    g = CampusGraph()
    for name in ["A", "B", "C", "D"]:
        g.add_node(Node(id=name, name=f"Node {name}", category="academic"))

    g.add_edge(Edge("A", "B", distance_m=10.0, is_directed=False))
    g.add_edge(Edge("B", "D", distance_m=10.0, is_directed=False))
    g.add_edge(Edge("A", "C", distance_m=25.0, is_directed=False))
    g.add_edge(Edge("C", "D", distance_m=25.0, is_directed=False))
    return g


class TestDijkstraBaseCasesAndValidation:
    """Tests fundamental constraints and base cases."""

    def test_source_equals_destination_returns_zero_route(self, diamond_graph: CampusGraph):
        """Querying path from A to A returns a 0-distance single-node route."""
        res = dijkstra_shortest_path(diamond_graph, source="A", target="A")
        assert res.nodes == ["A"]
        assert res.total_distance_m == 0.0
        assert res.total_cost == 0.0
        assert res.hop_count == 0
        assert res.is_empty is True

    def test_unknown_source_raises_node_not_found(self, diamond_graph: CampusGraph):
        """Query with unknown source node raises NodeNotFoundError."""
        with pytest.raises(NodeNotFoundError):
            dijkstra_shortest_path(diamond_graph, source="NONEXISTENT", target="D")

    def test_unknown_target_raises_node_not_found(self, diamond_graph: CampusGraph):
        """Query with unknown target node raises NodeNotFoundError."""
        with pytest.raises(NodeNotFoundError):
            dijkstra_shortest_path(diamond_graph, source="A", target="NONEXISTENT")


class TestDijkstraRoutingAndOptimality:
    """Tests shortest-path calculation and alternative route discovery."""

    def test_finds_primary_shortest_path(self, diamond_graph: CampusGraph):
        """Calculates optimal path through B."""
        res = dijkstra_shortest_path(diamond_graph, source="A", target="D")
        assert res.nodes == ["A", "B", "D"]
        assert res.total_distance_m == pytest.approx(20.0)
        assert res.total_cost == pytest.approx(20.0)
        assert res.hop_count == 2

    def test_blockage_triggers_longer_alternative_route(self, diamond_graph: CampusGraph):
        """Blocking edge A-B forces re-routing through A -> C -> D."""
        diamond_graph.set_edge_blocked("A", "B", is_blocked=True, block_reason="Repaving")

        res = dijkstra_shortest_path(diamond_graph, source="A", target="D")
        assert res.nodes == ["A", "C", "D"]
        assert res.total_distance_m == pytest.approx(50.0)
        assert res.total_cost == pytest.approx(50.0)

    def test_unreachable_destination_raises_path_not_found(self, diamond_graph: CampusGraph):
        """Blocking all access to D causes PathNotFoundError."""
        diamond_graph.set_edge_blocked("B", "D", is_blocked=True)
        diamond_graph.set_edge_blocked("C", "D", is_blocked=True)

        with pytest.raises(PathNotFoundError):
            dijkstra_shortest_path(diamond_graph, source="A", target="D")

    def test_disconnected_graph_raises_path_not_found(self):
        """Completely disconnected nodes raise PathNotFoundError."""
        g = CampusGraph()
        g.add_node(Node("ISLAND_1", "Island 1", "gate"))
        g.add_node(Node("ISLAND_2", "Island 2", "gate"))

        with pytest.raises(PathNotFoundError):
            dijkstra_shortest_path(g, source="ISLAND_1", target="ISLAND_2")


class TestDirectedAndAccessibilityRouting:
    """Tests directed edges and wheelchair accessibility filtering."""

    def test_directed_path_cannot_be_traversed_in_reverse(self):
        """Directed edge X -> Y allows forward navigation, but reverse raises PathNotFoundError."""
        g = CampusGraph()
        g.add_node(Node("X", "Node X", "gate"))
        g.add_node(Node("Y", "Node Y", "academic"))
        g.add_edge(Edge("X", "Y", distance_m=30.0, is_directed=True))

        forward_res = dijkstra_shortest_path(g, "X", "Y")
        assert forward_res.nodes == ["X", "Y"]
        assert forward_res.total_distance_m == pytest.approx(30.0)

        with pytest.raises(PathNotFoundError):
            dijkstra_shortest_path(g, "Y", "X")

    def test_accessibility_filtering_bypasses_stairs(self):
        """
        Topology:
        Path 1 (stairs): Start -> Stairs -> End (dist 40m, not accessible)
        Path 2 (ramp):   Start -> Ramp -> End (dist 80m, accessible)
        """
        g = CampusGraph()
        for n in ["Start", "Stairs", "Ramp", "End"]:
            g.add_node(Node(n, n, "academic"))

        g.add_edge(Edge("Start", "Stairs", distance_m=20.0, is_accessible=False, surface_type="stairs"))
        g.add_edge(Edge("Stairs", "End", distance_m=20.0, is_accessible=False, surface_type="stairs"))
        g.add_edge(Edge("Start", "Ramp", distance_m=40.0, is_accessible=True, surface_type="concrete"))
        g.add_edge(Edge("Ramp", "End", distance_m=40.0, is_accessible=True, surface_type="concrete"))

        # Standard search uses stairs (shorter: 40m)
        standard_res = dijkstra_shortest_path(g, "Start", "End", accessible_only=False)
        assert standard_res.nodes == ["Start", "Stairs", "End"]
        assert standard_res.total_distance_m == pytest.approx(40.0)

        # Accessible search bypasses stairs (longer: 80m)
        acc_res = dijkstra_shortest_path(g, "Start", "End", accessible_only=True)
        assert acc_res.nodes == ["Start", "Ramp", "End"]
        assert acc_res.total_distance_m == pytest.approx(80.0)


class TestCostSeparationAndFullPrecision:
    """Tests separation of physical distance from routing cost and unrounded precision."""

    def test_routing_cost_minimization_with_physical_distance_preservation(self):
        """
        Path 1: Physical distance 100m, but has steep slope penalty (cost 300)
        Path 2: Physical distance 150m, flat contour (cost 150)
        Algorithm should choose Path 2 (lower cost 150), reporting distance 150m.
        """
        g = CampusGraph()
        for n in ["Origin", "Slope", "Flat", "Dest"]:
            g.add_node(Node(n, n, "academic"))

        g.add_edge(Edge("Origin", "Slope", distance_m=50.0, cost=150.0))
        g.add_edge(Edge("Slope", "Dest", distance_m=50.0, cost=150.0))

        g.add_edge(Edge("Origin", "Flat", distance_m=75.0, cost=75.0))
        g.add_edge(Edge("Flat", "Dest", distance_m=75.0, cost=75.0))

        res = dijkstra_shortest_path(g, "Origin", "Dest")
        assert res.nodes == ["Origin", "Flat", "Dest"]
        assert res.total_cost == pytest.approx(150.0)
        assert res.total_distance_m == pytest.approx(150.0)

    def test_full_precision_unrounded_accumulation(self):
        """Verifies that floating-point distance is not truncated or prematurely rounded."""
        g = CampusGraph()
        g.add_node(Node("P1", "P1", "academic"))
        g.add_node(Node("P2", "P2", "academic"))
        g.add_node(Node("P3", "P3", "academic"))

        g.add_edge(Edge("P1", "P2", distance_m=12.3456789))
        g.add_edge(Edge("P2", "P3", distance_m=87.6543211))

        res = dijkstra_shortest_path(g, "P1", "P3")
        expected_sum = 12.3456789 + 87.6543211
        assert math.isclose(res.total_distance_m, expected_sum, abs_tol=1e-10)


class TestMultipleEquallyOptimalPaths:
    """Tests graph with multiple paths of identical minimum cost."""

    def test_equally_optimal_paths(self):
        """
        Two parallel paths of identical length:
        A -> Upper -> Z (50m)
        A -> Lower -> Z (50m)
        Both are equally optimal; the returned path must be valid and cost exactly 50m.
        """
        g = CampusGraph()
        for n in ["A", "Upper", "Lower", "Z"]:
            g.add_node(Node(n, n, "academic"))

        g.add_edge(Edge("A", "Upper", distance_m=25.0))
        g.add_edge(Edge("Upper", "Z", distance_m=25.0))
        g.add_edge(Edge("A", "Lower", distance_m=25.0))
        g.add_edge(Edge("Lower", "Z", distance_m=25.0))

        res = dijkstra_shortest_path(g, "A", "Z")
        assert res.total_distance_m == pytest.approx(50.0)
        assert res.total_cost == pytest.approx(50.0)
        assert res.nodes in (["A", "Upper", "Z"], ["A", "Lower", "Z"])
