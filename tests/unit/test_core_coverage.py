"""
Targeted tests for untested edge cases, error conditions, and query filters
across the core campus_routing package to ensure rigorous branch coverage >= 90%.
"""

from pathlib import Path
import sqlite3
from unittest.mock import MagicMock
import pytest

from campus_routing.algorithms.dijkstra import RouteResult
from campus_routing.algorithms.validator import (
    ValidationDiscrepancyError,
    validate_route_against_networkx,
)
from campus_routing.config import DEMO_GRAPH_PATH
from campus_routing.db.connection import init_db
from campus_routing.db.repository import CampusRepository
from campus_routing.exceptions import (
    DatabaseError,
    EdgeNotFoundError,
    NodeNotFoundError,
    ValidationError,
)
from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node
from campus_routing.visualization.map_builder import (
    create_campus_context_map,
    create_demonstration_map,
)


class TestGraphModelBranches:
    """Verifies graph validation, filtering, and error handling branches."""

    def test_add_node_type_validation(self) -> None:
        """add_node raises ValidationError when passed non-Node object."""
        graph = CampusGraph()
        with pytest.raises(ValidationError, match="Expected Node instance"):
            graph.add_node("not-a-node")  # type: ignore[arg-type]

    def test_get_nodes_filtering(self) -> None:
        """get_nodes filters correctly by landmark_only and category."""
        graph = CampusGraph()
        n1 = Node(id="A", name="A", category="academic", is_landmark=1)
        n2 = Node(id="B", name="B", category="residential", is_landmark=0)
        graph.add_node(n1)
        graph.add_node(n2)

        assert len(graph.get_nodes(landmark_only=True)) == 1
        assert graph.get_nodes(landmark_only=True)[0].id == "A"
        assert len(graph.get_nodes(category="residential")) == 1
        assert graph.get_nodes(category="residential")[0].id == "B"
        assert len(graph.get_nodes(category="dining")) == 0

    def test_add_edge_type_validation(self) -> None:
        """add_edge raises ValidationError when passed non-Edge object."""
        graph = CampusGraph()
        with pytest.raises(ValidationError, match="Expected Edge instance"):
            graph.add_edge("not-an-edge")  # type: ignore[arg-type]

    def test_set_edge_blocked_on_missing_edge_raises(self) -> None:
        """set_edge_blocked raises EdgeNotFoundError if edge does not exist."""
        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)
        with pytest.raises(EdgeNotFoundError, match="does not exist in graph"):
            graph.set_edge_blocked("DEMO_GATE", "NONEXISTENT", is_blocked=True)

    def test_get_neighbors_on_missing_node_raises(self) -> None:
        """get_neighbors raises NodeNotFoundError if node does not exist."""
        graph = CampusGraph()
        with pytest.raises(NodeNotFoundError, match="does not exist in graph"):
            graph.get_neighbors("UNKNOWN_NODE")


class TestRepositoryBranches:
    """Verifies repository query filters, metadata helpers, and error branches."""

    def test_init_db_success_and_missing_schema_error(self, tmp_path: Path) -> None:
        """init_db creates tables and raises DatabaseError on missing schema file."""
        db_file = tmp_path / "init_test.db"
        conn = init_db(db_path=db_file)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

        with pytest.raises(DatabaseError, match="Schema definition file not found"):
            init_db(db_path=":memory:", schema_path=tmp_path / "missing_schema.sql")

    def test_init_schema_missing_file_raises(self, repo_in_memory: CampusRepository, tmp_path: Path) -> None:
        """init_schema raises DatabaseError if passed a non-existent file path."""
        with pytest.raises(DatabaseError, match="Schema file not found"):
            repo_in_memory.init_schema(schema_path=tmp_path / "no_file.sql")

    def test_repository_list_nodes_and_edges_filtering(self, repo_in_memory: CampusRepository) -> None:
        """Tests repository list_nodes and list_edges with various filters."""
        # Nodes
        repo_in_memory.upsert_node(node_id="N1", name="N1", category="academic", is_landmark=1)
        repo_in_memory.upsert_node(node_id="N2", name="N2", category="residential", is_landmark=0)

        academic_nodes = repo_in_memory.list_nodes(category="academic")
        assert len(academic_nodes) == 1
        assert academic_nodes[0]["id"] == "N1"

        landmarks = repo_in_memory.list_nodes(landmark_only=True)
        assert len(landmarks) == 1
        assert landmarks[0]["id"] == "N1"

        # Edges
        repo_in_memory.add_edge(source_id="N1", target_id="N2", distance_m=50.0, is_directed=1, is_accessible=0)
        all_edges = repo_in_memory.list_edges(include_blocked=True)
        assert len(all_edges) == 1

        repo_in_memory.set_edge_blocked("N1", "N2", is_blocked=True, block_reason="Maintenance")
        unblocked_edges = repo_in_memory.list_edges(include_blocked=False)
        assert len(unblocked_edges) == 0

    def test_metadata_helpers(self, repo_in_memory: CampusRepository) -> None:
        """Tests get_all_metadata and has_verified_routing_network."""
        assert not repo_in_memory.has_verified_routing_network()
        all_meta = repo_in_memory.get_all_metadata()
        assert isinstance(all_meta, dict)

        repo_in_memory.set_metadata("has_verified_routing_network", "true")
        assert repo_in_memory.has_verified_routing_network()

    def test_validate_node_data_invalid_provenance_and_verification(self, repo_in_memory: CampusRepository) -> None:
        """validate_node_data rejects invalid provenance and verification status."""
        with pytest.raises(ValidationError, match="Invalid source_provenance"):
            repo_in_memory.validate_node_data(
                category="academic",
                latitude=None,
                longitude=None,
                source_provenance="INVALID_PROV",
                verification_status="UNVERIFIED",
            )

        with pytest.raises(ValidationError, match="Invalid verification_status"):
            repo_in_memory.validate_node_data(
                category="academic",
                latitude=None,
                longitude=None,
                source_provenance="OFFICIAL_INSTITUTIONAL",
                verification_status="INVALID_STATUS",
            )


class TestValidatorDiscrepancyBranches:
    """Verifies that validator catches all theoretical discrepancy conditions between solvers."""

    def test_validator_detects_cost_discrepancy(self) -> None:
        """Validator raises ValidationDiscrepancyError when solver costs differ."""
        from unittest.mock import patch
        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)

        # Mock custom solver returning an erroneous route cost
        discrepant_route = RouteResult(
            nodes=["DEMO_GATE", "DEMO_ACAD", "DEMO_HOSTEL"],
            total_distance_m=348.5,
            total_cost=9999.0,  # Erroneous cost
        )
        with patch("campus_routing.algorithms.validator.dijkstra_shortest_path", return_value=discrepant_route):
            with pytest.raises(ValidationDiscrepancyError, match="discrepancy between solvers"):
                validate_route_against_networkx(graph, "DEMO_GATE", "DEMO_HOSTEL")

    def test_validator_detects_solver_error_mismatch(self) -> None:
        """Validator raises ValidationDiscrepancyError when solvers raise different exception types."""
        from unittest.mock import patch
        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)

        with patch("campus_routing.algorithms.validator.dijkstra_shortest_path", side_effect=RuntimeError("Custom bug")):
            with pytest.raises(ValidationDiscrepancyError, match="Solver error mismatch"):
                validate_route_against_networkx(graph, "DEMO_GATE", "DEMO_HOSTEL")


class TestVisualizationBranches:
    """Verifies edge cases in map building and directions."""

    def test_context_map_with_failing_repo(self) -> None:
        """create_campus_context_map safely falls back when repo.list_nodes fails."""
        mock_repo = MagicMock(spec=CampusRepository)
        mock_repo.list_nodes.side_effect = RuntimeError("DB locked")

        # Map should still be constructed without raising exception
        campus_map = create_campus_context_map(repo=mock_repo)
        assert campus_map is not None

    def test_demo_map_loads_default_json_when_no_graph(self) -> None:
        """create_demonstration_map loads demonstration_graph.json when graph is None."""
        demo_map = create_demonstration_map(graph=None)
        assert demo_map is not None

    def test_demo_map_empty_route_result_raises(self) -> None:
        """create_demonstration_map raises ValidationError if RouteResult has no nodes."""
        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)
        # Bypassing __post_init__ via object.__new__ to test defensive validation
        empty_route = object.__new__(RouteResult)
        object.__setattr__(empty_route, "nodes", [])
        object.__setattr__(empty_route, "total_distance_m", 0.0)
        object.__setattr__(empty_route, "total_cost", 0.0)

        with pytest.raises(ValidationError, match="empty node sequence"):
            create_demonstration_map(graph=graph, route_result=empty_route)
