"""
Unit tests for domain models: Node, Edge, and CampusGraph.

Verifies validation, constraints, canonical ordering, serialization, and adjacency management.
"""

import json
import math
from pathlib import Path
import pytest

from campus_routing.exceptions import (
    CoordinateOutOfBoundsError,
    DuplicateEdgeError,
    EdgeNotFoundError,
    IncompleteCoordinateError,
    InvalidEdgeError,
    InvalidNodeCategoryError,
    NodeNotFoundError,
    ValidationError,
)
from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node


class TestNodeModel:
    """Unit tests for Node entity."""

    def test_valid_node_with_coordinates(self):
        """Node with valid coordinates initializes correctly."""
        node = Node(
            id="ACAD_01",
            name="Academic Block 1",
            category="academic",
            latitude=9.754833,
            longitude=76.650099,
            elevation_m=125.0,
            is_landmark=True,
            description="Main academic complex",
            source_provenance="OFFICIAL_INSTITUTIONAL",
            verification_status="OFFICIAL_REFERENCE",
        )
        assert node.id == "ACAD_01"
        assert node.name == "Academic Block 1"
        assert node.category == "academic"
        assert node.has_coordinates is True
        assert node.latitude == pytest.approx(9.754833)

    def test_valid_node_with_unknown_coordinates(self):
        """Node with unknown coordinates (both None) is valid."""
        node = Node(
            id="UNSURVEYED_01",
            name="Unsurveyed Gate",
            category="gate",
            latitude=None,
            longitude=None,
        )
        assert node.id == "UNSURVEYED_01"
        assert node.has_coordinates is False
        assert node.latitude is None
        assert node.longitude is None

    def test_incomplete_coordinates_rejected(self):
        """Supplying latitude without longitude or vice-versa must raise IncompleteCoordinateError."""
        with pytest.raises(IncompleteCoordinateError):
            Node(id="INC_LAT", name="Inc Lat", category="academic", latitude=9.755, longitude=None)

        with pytest.raises(IncompleteCoordinateError):
            Node(id="INC_LON", name="Inc Lon", category="academic", latitude=None, longitude=76.650)

    def test_coordinates_out_of_bounds_rejected(self):
        """Coordinates outside sanity envelope must raise CoordinateOutOfBoundsError."""
        with pytest.raises(CoordinateOutOfBoundsError):
            Node(id="OOB_1", name="OOB", category="academic", latitude=10.5, longitude=76.650)

        with pytest.raises(CoordinateOutOfBoundsError):
            Node(id="OOB_2", name="OOB", category="academic", latitude=9.755, longitude=78.0)

    def test_empty_id_or_name_rejected(self):
        """Empty ID or name raises ValidationError."""
        with pytest.raises(ValidationError):
            Node(id="", name="Valid Name", category="academic")
        with pytest.raises(ValidationError):
            Node(id="VALID_ID", name="", category="academic")

    def test_invalid_category_rejected(self):
        """Unsupported category raises InvalidNodeCategoryError."""
        with pytest.raises(InvalidNodeCategoryError):
            Node(id="N1", name="Node 1", category="helicopter_pad")

    def test_serialization_roundtrip(self):
        """Node serialization to/from dictionary preserves all fields."""
        original = Node(
            id="NODE_TEST",
            name="Test Node",
            category="dining",
            latitude=9.7552,
            longitude=76.6505,
            elevation_m=130.0,
            is_landmark=True,
            description="Test dining hall",
            source_provenance="SYNTHETIC_DEMO",
            verification_status="SYNTHETIC_DEMO",
        )
        data = original.to_dict()
        reconstructed = Node.from_dict(data)
        assert original == reconstructed


class TestEdgeModel:
    """Unit tests for Edge entity."""

    def test_valid_undirected_edge(self):
        """Undirected edge initializes with valid distance."""
        edge = Edge(
            source_id="A",
            target_id="B",
            distance_m=125.4,
            is_directed=False,
            surface_type="paved",
            is_accessible=True,
        )
        assert edge.source_id == "A"
        assert edge.target_id == "B"
        assert edge.distance_m == 125.4
        assert edge.effective_cost == 125.4
        assert edge.canonical_endpoints() == ("A", "B")

    def test_canonical_endpoints_for_undirected_edge(self):
        """Canonical endpoints order alphabetically for undirected edges."""
        edge = Edge(source_id="Z", target_id="A", distance_m=10.0, is_directed=False)
        assert edge.canonical_endpoints() == ("A", "Z")

    def test_canonical_endpoints_for_directed_edge(self):
        """Canonical endpoints preserve direction for directed edges."""
        edge = Edge(source_id="Z", target_id="A", distance_m=10.0, is_directed=True)
        assert edge.canonical_endpoints() == ("Z", "A")

    def test_custom_routing_cost(self):
        """When cost is provided, effective_cost reflects cost rather than distance_m."""
        edge = Edge(
            source_id="A",
            target_id="B",
            distance_m=100.0,
            cost=250.0,  # e.g. steep incline penalty
        )
        assert edge.distance_m == 100.0
        assert edge.cost == 250.0
        assert edge.effective_cost == 250.0

    def test_self_loop_rejected(self):
        """Self-loops raise InvalidEdgeError."""
        with pytest.raises(InvalidEdgeError):
            Edge(source_id="A", target_id="A", distance_m=50.0)

    def test_non_positive_distance_rejected(self):
        """Zero or negative physical distance raises InvalidEdgeError."""
        with pytest.raises(InvalidEdgeError):
            Edge(source_id="A", target_id="B", distance_m=0.0)
        with pytest.raises(InvalidEdgeError):
            Edge(source_id="A", target_id="B", distance_m=-10.0)

    def test_non_finite_distance_rejected(self):
        """NaN or Inf physical distance raises InvalidEdgeError."""
        with pytest.raises(InvalidEdgeError):
            Edge(source_id="A", target_id="B", distance_m=float("nan"))
        with pytest.raises(InvalidEdgeError):
            Edge(source_id="A", target_id="B", distance_m=float("inf"))

    def test_negative_or_non_finite_cost_rejected(self):
        """Negative or non-finite routing cost raises InvalidEdgeError."""
        with pytest.raises(InvalidEdgeError):
            Edge(source_id="A", target_id="B", distance_m=50.0, cost=-5.0)
        with pytest.raises(InvalidEdgeError):
            Edge(source_id="A", target_id="B", distance_m=50.0, cost=float("nan"))

    def test_serialization_roundtrip(self):
        """Edge serialization to/from dictionary preserves all fields."""
        original = Edge(
            source_id="N1",
            target_id="N2",
            distance_m=88.5,
            is_directed=True,
            surface_type="stairs",
            is_accessible=False,
            is_blocked=True,
            block_reason="Repairs",
            cost=150.0,
        )
        data = original.to_dict()
        reconstructed = Edge.from_dict(data)
        assert original.source_id == reconstructed.source_id
        assert original.target_id == reconstructed.target_id
        assert original.distance_m == reconstructed.distance_m
        assert original.effective_cost == reconstructed.effective_cost
        assert original.is_blocked == reconstructed.is_blocked


class TestCampusGraphModel:
    """Unit tests for CampusGraph container."""

    @pytest.fixture
    def sample_graph(self) -> CampusGraph:
        """Constructs a basic test graph with 3 nodes and 2 edges."""
        graph = CampusGraph()
        graph.add_node(Node("A", "Node A", "gate"))
        graph.add_node(Node("B", "Node B", "academic"))
        graph.add_node(Node("C", "Node C", "residential"))
        graph.add_edge(Edge("A", "B", distance_m=100.0, is_directed=False))
        graph.add_edge(Edge("B", "C", distance_m=50.0, is_directed=True, is_accessible=False))
        return graph

    def test_node_insertion_and_retrieval(self, sample_graph: CampusGraph):
        """Nodes can be retrieved by ID."""
        assert sample_graph.node_count == 3
        assert sample_graph.has_node("A")
        assert sample_graph.get_node("A").name == "Node A"

        with pytest.raises(NodeNotFoundError):
            sample_graph.get_node("NONEXISTENT")

    def test_duplicate_node_rejected(self, sample_graph: CampusGraph):
        """Inserting duplicate node ID without overwrite=True raises ValidationError."""
        with pytest.raises(ValidationError):
            sample_graph.add_node(Node("A", "Duplicate A", "gate"), overwrite=False)

    def test_edge_connecting_unknown_node_rejected(self, sample_graph: CampusGraph):
        """Adding edge with unknown endpoint raises NodeNotFoundError."""
        with pytest.raises(NodeNotFoundError):
            sample_graph.add_edge(Edge("A", "UNKNOWN_TARGET", distance_m=50.0))

    def test_duplicate_edge_rejected(self, sample_graph: CampusGraph):
        """Adding duplicate edge raises DuplicateEdgeError."""
        with pytest.raises(DuplicateEdgeError):
            sample_graph.add_edge(Edge("A", "B", distance_m=75.0, is_directed=False))

    def test_undirected_traversable_both_ways(self, sample_graph: CampusGraph):
        """Undirected edge A-B is found when queried A->B or B->A."""
        assert sample_graph.has_edge("A", "B")
        assert sample_graph.has_edge("B", "A")

        neighbors_a = [n for n, e in sample_graph.get_neighbors("A")]
        neighbors_b = [n for n, e in sample_graph.get_neighbors("B")]
        assert "B" in neighbors_a
        assert "A" in neighbors_b

    def test_directed_edge_traversal(self, sample_graph: CampusGraph):
        """Directed edge B->C is traversable only from B to C."""
        assert sample_graph.has_edge("B", "C")
        assert not sample_graph.has_edge("C", "B")

        neighbors_b = [n for n, e in sample_graph.get_neighbors("B")]
        neighbors_c = [n for n, e in sample_graph.get_neighbors("C")]
        assert "C" in neighbors_b
        assert "B" not in neighbors_c

    def test_blockage_filtering(self, sample_graph: CampusGraph):
        """Blocked edges are omitted when include_blocked=False."""
        sample_graph.set_edge_blocked("A", "B", is_blocked=True, block_reason="Tree fall")

        # Without blocked edges: A has no traversable neighbors
        neighbors_unblocked = sample_graph.get_neighbors("A", include_blocked=False)
        assert len(neighbors_unblocked) == 0

        # With blocked edges: A sees B
        neighbors_all = sample_graph.get_neighbors("A", include_blocked=True)
        assert len(neighbors_all) == 1
        assert neighbors_all[0][0] == "B"
        assert neighbors_all[0][1].is_blocked is True
        assert neighbors_all[0][1].block_reason == "Tree fall"

    def test_accessibility_filtering(self, sample_graph: CampusGraph):
        """Non-accessible edges are omitted when accessible_only=True."""
        # Edge B->C has is_accessible=False
        neighbors_standard = sample_graph.get_neighbors("B", accessible_only=False)
        assert any(n == "C" for n, e in neighbors_standard)

        neighbors_accessible = sample_graph.get_neighbors("B", accessible_only=True)
        assert not any(n == "C" for n, e in neighbors_accessible)

    def test_from_dict_and_to_dict_roundtrip(self, sample_graph: CampusGraph):
        """Graph serialization to/from dictionary preserves structure."""
        data = sample_graph.to_dict()
        reconstructed = CampusGraph.from_dict(data)
        assert reconstructed.node_count == sample_graph.node_count
        assert reconstructed.edge_count == sample_graph.edge_count
        assert reconstructed.has_edge("A", "B")
        assert reconstructed.has_edge("B", "C")

    def test_from_json_file(self, tmp_path: Path):
        """Graph can be loaded from JSON file."""
        file_path = tmp_path / "test_graph.json"
        content = {
            "nodes": [
                {"id": "X1", "name": "Node X1", "category": "gate"},
                {"id": "X2", "name": "Node X2", "category": "academic"},
            ],
            "edges": [
                {"source_id": "X1", "target_id": "X2", "distance_m": 120.0, "is_directed": False}
            ]
        }
        file_path.write_text(json.dumps(content), encoding="utf-8")
        graph = CampusGraph.from_json_file(file_path)
        assert graph.node_count == 2
        assert graph.edge_count == 1
        assert graph.has_edge("X1", "X2")

    def test_from_repository_loads_database_records(self, repo_temp_file):
        """CampusGraph.from_repository correctly loads SQLite nodes and edges."""
        repo_temp_file.upsert_node("R1", "Repo Node 1", "gate")
        repo_temp_file.upsert_node("R2", "Repo Node 2", "academic")
        repo_temp_file.add_edge("R1", "R2", distance_m=55.0, is_directed=0)

        graph = CampusGraph.from_repository(repo_temp_file)
        assert graph.node_count == 2
        assert graph.edge_count == 1
        assert graph.has_node("R1")
        assert graph.has_node("R2")
        assert graph.has_edge("R1", "R2")
        assert graph.get_edge("R1", "R2").distance_m == pytest.approx(55.0)

