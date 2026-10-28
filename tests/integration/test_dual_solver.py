"""
Integration tests for dual-solver validation harness on the demonstration graph.

Executes comprehensive cross-validation comparing Custom Dijkstra vs. NetworkX.
Verifies all reachable pairs, blocked path alternative routing, and accessibility constraints.
"""

from typing import List
import pytest

from campus_routing.algorithms.dijkstra import dijkstra_shortest_path
from campus_routing.algorithms.networkx_solver import networkx_shortest_path
from campus_routing.algorithms.validator import validate_route_against_networkx
from campus_routing.config import DEMO_GRAPH_PATH
from campus_routing.exceptions import NodeNotFoundError, PathNotFoundError
from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node


@pytest.fixture
def demo_graph() -> CampusGraph:
    """Loads the isolated synthetic demonstration graph."""
    assert DEMO_GRAPH_PATH.is_file(), f"Demonstration graph file missing at {DEMO_GRAPH_PATH}"
    return CampusGraph.from_json_file(DEMO_GRAPH_PATH)


class TestDualSolverOnDemonstrationGraph:
    """Verifies Custom Dijkstra against NetworkX across the complete demonstration dataset."""

    def test_all_reachable_node_pairs_match_networkx(self, demo_graph: CampusGraph):
        """
        Cross-validates all 30 origin-destination pairs (u != v) in the 6-node demonstration network.
        Every query must yield identical optimal routing costs and valid hop sequences.
        """
        nodes: List[Node] = demo_graph.get_nodes()
        node_ids = [n.id for n in nodes]
        assert len(node_ids) == 6

        comparisons_executed = 0

        for u in node_ids:
            for v in node_ids:
                if u == v:
                    continue
                custom_res, ref_res = validate_route_against_networkx(
                    graph=demo_graph,
                    source=u,
                    target=v,
                    accessible_only=False,
                    abs_tol=1e-4,
                )
                assert custom_res.nodes[0] == u
                assert custom_res.nodes[-1] == v
                assert ref_res.nodes[0] == u
                assert ref_res.nodes[-1] == v
                assert custom_res.total_cost == pytest.approx(ref_res.total_cost, abs=1e-4)
                assert custom_res.total_distance_m == pytest.approx(ref_res.total_distance_m, abs=1e-4)
                comparisons_executed += 1

        assert comparisons_executed == 30

    def test_dynamic_blockage_re_routing_parity(self, demo_graph: CampusGraph):
        """
        Blocks the direct arterial path between DEMO_GATE and DEMO_ACAD.
        Both solvers must discover the exact same alternative detour.
        """
        # Baseline before blockage: direct edge 165.4m
        res_before = dijkstra_shortest_path(demo_graph, "DEMO_GATE", "DEMO_ACAD")
        assert res_before.nodes == ["DEMO_GATE", "DEMO_ACAD"]
        assert res_before.total_distance_m == pytest.approx(165.4)

        # Block the direct pathway
        demo_graph.set_edge_blocked(
            "DEMO_GATE",
            "DEMO_ACAD",
            is_blocked=True,
            block_reason="Security Maintenance",
        )

        # In demonstration graph, DEMO_GATE connects only to DEMO_ACAD!
        # Thus blocking this edge isolates DEMO_GATE completely.
        # Both solvers must raise PathNotFoundError consistently.
        with pytest.raises(PathNotFoundError):
            validate_route_against_networkx(demo_graph, "DEMO_GATE", "DEMO_ACAD")

        # Unblock DEMO_GATE - DEMO_ACAD
        demo_graph.set_edge_blocked("DEMO_GATE", "DEMO_ACAD", is_blocked=False)

        # Now block DEMO_ACAD - DEMO_MESS (dist 110.8m)
        # Alternate route from DEMO_ACAD to DEMO_HOSTEL should detour:
        # Before: ACAD -> MESS -> HOSTEL (110.8 + 72.3 = 183.1m)
        # Blocked: No direct ACAD-MESS. Path must be: ACAD -> LIBRARY -> SPORTS -> MESS -> HOSTEL
        demo_graph.set_edge_blocked(
            "DEMO_ACAD",
            "DEMO_MESS",
            is_blocked=True,
            block_reason="Paving Work",
        )

        custom_res, ref_res = validate_route_against_networkx(
            demo_graph, "DEMO_ACAD", "DEMO_HOSTEL"
        )
        assert custom_res.total_cost == pytest.approx(ref_res.total_cost, abs=1e-4)
        assert custom_res.total_distance_m == pytest.approx(ref_res.total_distance_m, abs=1e-4)

    def test_accessibility_filtering_consistency(self, demo_graph: CampusGraph):
        """
        Edges to DEMO_SPORTS use 'trail' (inaccessible) and 'stairs' (inaccessible).
        Under accessible_only=True, DEMO_SPORTS becomes unreachable.
        Both solvers must consistently raise PathNotFoundError.
        """
        # Without accessibility restriction: DEMO_SPORTS is reachable from DEMO_ACAD
        custom_open, ref_open = validate_route_against_networkx(
            demo_graph, "DEMO_ACAD", "DEMO_SPORTS", accessible_only=False
        )
        assert "DEMO_SPORTS" in custom_open.nodes

        # With accessible_only=True: DEMO_SPORTS has no step-free pathways
        with pytest.raises(PathNotFoundError):
            validate_route_against_networkx(
                demo_graph, "DEMO_ACAD", "DEMO_SPORTS", accessible_only=True
            )


class TestDualSolverEdgeCases:
    """Verifies edge case handling across both solvers."""

    def test_source_equals_destination(self, demo_graph: CampusGraph):
        """Origin == Destination returns 0 distance and single node on both solvers."""
        custom_res, ref_res = validate_route_against_networkx(
            demo_graph, "DEMO_ACAD", "DEMO_ACAD"
        )
        assert custom_res.nodes == ["DEMO_ACAD"]
        assert custom_res.total_distance_m == 0.0
        assert custom_res.total_cost == 0.0
        assert ref_res.nodes == ["DEMO_ACAD"]
        assert ref_res.total_distance_m == 0.0
        assert ref_res.total_cost == 0.0

    def test_unknown_nodes_raise_consistently(self, demo_graph: CampusGraph):
        """Unknown nodes trigger NodeNotFoundError in both solvers."""
        with pytest.raises(NodeNotFoundError):
            validate_route_against_networkx(demo_graph, "INVALID_NODE", "DEMO_GATE")

        with pytest.raises(NodeNotFoundError):
            validate_route_against_networkx(demo_graph, "DEMO_GATE", "INVALID_NODE")

    def test_multiple_equally_optimal_paths(self):
        """
        Topology with two symmetric paths of identical cost:
        Path 1: S -> Top -> D (50m)
        Path 2: S -> Bot -> D (50m)
        Both solvers must identify optimal cost 50m and valid routes.
        """
        g = CampusGraph()
        for name in ["S", "Top", "Bot", "D"]:
            g.add_node(Node(name, name, "academic"))

        g.add_edge(Edge("S", "Top", distance_m=25.0))
        g.add_edge(Edge("Top", "D", distance_m=25.0))
        g.add_edge(Edge("S", "Bot", distance_m=25.0))
        g.add_edge(Edge("Bot", "D", distance_m=25.0))

        custom_res, ref_res = validate_route_against_networkx(g, "S", "D")
        assert custom_res.total_cost == pytest.approx(50.0)
        assert ref_res.total_cost == pytest.approx(50.0)
        assert custom_res.nodes in (["S", "Top", "D"], ["S", "Bot", "D"])
        assert ref_res.nodes in (["S", "Top", "D"], ["S", "Bot", "D"])

    def test_disconnected_graph_consistently_raises(self):
        """Independent components cause both solvers to raise PathNotFoundError."""
        g = CampusGraph()
        g.add_node(Node("C1_A", "C1_A", "academic"))
        g.add_node(Node("C1_B", "C1_B", "academic"))
        g.add_edge(Edge("C1_A", "C1_B", distance_m=10.0))

        g.add_node(Node("C2_A", "C2_A", "academic"))
        g.add_node(Node("C2_B", "C2_B", "academic"))
        g.add_edge(Edge("C2_A", "C2_B", distance_m=10.0))

        with pytest.raises(PathNotFoundError):
            validate_route_against_networkx(g, "C1_A", "C2_A")
