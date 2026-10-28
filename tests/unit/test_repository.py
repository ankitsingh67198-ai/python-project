"""
Unit tests for SQLite database repository, schema constraints, transactions, and seeder.

Verifies:
1. Successful database initialization.
2. Required tables and indexes existence.
3. Foreign-key enforcement.
4. Invalid data and schema constraints.
5. Unknown and partial coordinates.
6. Valid and invalid pathway records.
7. Transaction rollback on failure.
8. Idempotent seeding.
9. Preservation of existing user changes.
10. Correct distinction between verified and demonstration data.
"""

from pathlib import Path
import sqlite3
import pytest

from campus_routing.db.connection import transaction
from campus_routing.db.repository import CampusRepository
from campus_routing.db.seeder import seed_database
from campus_routing.exceptions import (
    CoordinateOutOfBoundsError,
    DuplicateEdgeError,
    EdgeNotFoundError,
    IncompleteCoordinateError,
    InvalidEdgeError,
    InvalidNodeCategoryError,
    NodeNotFoundError,
)


class TestDatabaseSchemaAndInitialization:
    """Tests 1 & 2: Database initialization, tables, and indexes."""

    def test_database_initialization_creates_tables(self, repo_in_memory: CampusRepository):
        """Verifies that nodes, edges, and campus_metadata tables are created."""
        conn = repo_in_memory.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        assert "nodes" in tables
        assert "edges" in tables
        assert "campus_metadata" in tables

    def test_required_indexes_exist(self, repo_in_memory: CampusRepository):
        """Verifies that all performance indexes are present in the schema."""
        conn = repo_in_memory.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';"
        )
        indexes = {row["name"] for row in cursor.fetchall()}
        expected_indexes = {
            "idx_edges_source",
            "idx_edges_target",
            "idx_nodes_category",
            "idx_nodes_landmark",
        }
        for expected in expected_indexes:
            assert expected in indexes, f"Expected index '{expected}' not found in database."


class TestForeignKeyAndCascadeEnforcement:
    """Test 3: Foreign-key enforcement and cascading deletes."""

    def test_foreign_key_rejects_missing_node(self, repo_in_memory: CampusRepository):
        """Adding an edge referencing nonexistent node IDs must raise NodeNotFoundError."""
        with pytest.raises(NodeNotFoundError):
            repo_in_memory.add_edge(
                source_id="NONEXISTENT_A",
                target_id="NONEXISTENT_B",
                distance_m=100.0,
            )

    def test_cascading_delete_removes_connected_edges(self, repo_in_memory: CampusRepository):
        """Deleting a node must automatically delete connected edges via CASCADE."""
        repo_in_memory.upsert_node(node_id="NODE_A", name="Node A", category="academic")
        repo_in_memory.upsert_node(node_id="NODE_B", name="Node B", category="residential")
        repo_in_memory.add_edge(source_id="NODE_A", target_id="NODE_B", distance_m=50.0)

        assert repo_in_memory.get_edge("NODE_A", "NODE_B") is not None

        # Delete NODE_A
        conn = repo_in_memory.get_connection()
        with transaction(conn):
            conn.execute("DELETE FROM nodes WHERE id = 'NODE_A';")

        assert repo_in_memory.get_node("NODE_A") is None
        assert repo_in_memory.get_edge("NODE_A", "NODE_B") is None


class TestNodeConstraintsAndCoordinates:
    """Tests 4 & 5: Schema constraints, invalid categories, and coordinate rules."""

    def test_invalid_node_category_rejected(self, repo_in_memory: CampusRepository):
        """Specifying an unsupported category raises InvalidNodeCategoryError."""
        with pytest.raises(InvalidNodeCategoryError):
            repo_in_memory.upsert_node(
                node_id="INVALID_CAT",
                name="Invalid Block",
                category="spaceport",
            )

    def test_unknown_coordinates_allowed(self, repo_in_memory: CampusRepository):
        """Nodes with latitude=None and longitude=None must be accepted (unverified status)."""
        node = repo_in_memory.upsert_node(
            node_id="UNSURVEYED_NODE",
            name="Unsurveyed Landmark",
            category="academic",
            latitude=None,
            longitude=None,
        )
        assert node["latitude"] is None
        assert node["longitude"] is None

    def test_valid_coordinates_within_envelope_allowed(self, repo_in_memory: CampusRepository):
        """Nodes with valid coordinates within the Valavoor envelope must be accepted."""
        node = repo_in_memory.upsert_node(
            node_id="SURVEYED_NODE",
            name="Surveyed Landmark",
            category="academic",
            latitude=9.754833,
            longitude=76.650099,
            elevation_m=130.5,
        )
        assert node["latitude"] == pytest.approx(9.754833)
        assert node["longitude"] == pytest.approx(76.650099)
        assert node["elevation_m"] == pytest.approx(130.5)

    def test_incomplete_coordinates_rejected_latitude_only(self, repo_in_memory: CampusRepository):
        """Providing latitude without longitude must be rejected."""
        with pytest.raises(IncompleteCoordinateError):
            repo_in_memory.upsert_node(
                node_id="INCOMPLETE_LAT",
                name="Incomplete Lat",
                category="academic",
                latitude=9.754833,
                longitude=None,
            )

    def test_incomplete_coordinates_rejected_longitude_only(self, repo_in_memory: CampusRepository):
        """Providing longitude without latitude must be rejected."""
        with pytest.raises(IncompleteCoordinateError):
            repo_in_memory.upsert_node(
                node_id="INCOMPLETE_LON",
                name="Incomplete Lon",
                category="academic",
                latitude=None,
                longitude=76.650099,
            )

    def test_coordinates_outside_envelope_rejected(self, repo_in_memory: CampusRepository):
        """Coordinates outside the coarse sanity bounding envelope must be rejected."""
        # Latitude out of bounds
        with pytest.raises(CoordinateOutOfBoundsError):
            repo_in_memory.upsert_node(
                node_id="OOB_LAT",
                name="Out of bounds Lat",
                category="academic",
                latitude=15.000000,
                longitude=76.650099,
            )

        # Longitude out of bounds
        with pytest.raises(CoordinateOutOfBoundsError):
            repo_in_memory.upsert_node(
                node_id="OOB_LON",
                name="Out of bounds Lon",
                category="academic",
                latitude=9.754833,
                longitude=85.000000,
            )


class TestPathwayRecordsAndDirectionality:
    """Test 6: Valid and invalid pathway records, canonical ordering, and directionality."""

    @pytest.fixture(autouse=True)
    def setup_test_nodes(self, repo_in_memory: CampusRepository):
        """Inserts test nodes for edge operations."""
        repo_in_memory.upsert_node(node_id="N_AAA", name="Node AAA", category="academic")
        repo_in_memory.upsert_node(node_id="N_BBB", name="Node BBB", category="residential")
        repo_in_memory.upsert_node(node_id="N_CCC", name="Node CCC", category="dining")

    def test_valid_undirected_pathway_bidirectional_query(self, repo_in_memory: CampusRepository):
        """Undirected pathways can be queried in both forward and reverse directions."""
        repo_in_memory.add_edge(
            source_id="N_AAA",
            target_id="N_BBB",
            distance_m=120.5,
            is_directed=0,
        )

        edge_fwd = repo_in_memory.get_edge("N_AAA", "N_BBB")
        edge_rev = repo_in_memory.get_edge("N_BBB", "N_AAA")

        assert edge_fwd is not None
        assert edge_rev is not None
        assert edge_fwd["distance_m"] == pytest.approx(120.5)
        assert edge_rev["distance_m"] == pytest.approx(120.5)

    def test_auto_canonicalize_reorders_undirected_edge(self, repo_in_memory: CampusRepository):
        """Inserting an undirected edge with source > target is auto-canonicalized to source < target."""
        edge_id = repo_in_memory.add_edge(
            source_id="N_BBB",
            target_id="N_AAA",
            distance_m=85.0,
            is_directed=0,
            auto_canonicalize=True,
        )
        assert edge_id > 0
        edge = repo_in_memory.get_edge("N_AAA", "N_BBB")
        assert edge is not None
        assert edge["source_id"] == "N_AAA"
        assert edge["target_id"] == "N_BBB"

    def test_non_canonical_undirected_edge_rejected_when_not_auto_canonicalized(
        self, repo_in_memory: CampusRepository
    ):
        """Passing source > target with auto_canonicalize=False triggers constraint violation."""
        with pytest.raises(InvalidEdgeError):
            repo_in_memory.add_edge(
                source_id="N_BBB",
                target_id="N_AAA",
                distance_m=85.0,
                is_directed=0,
                auto_canonicalize=False,
            )

    def test_directed_pathway_respects_orientation(self, repo_in_memory: CampusRepository):
        """Directed pathways allow any valid source and target, but reverse query returns None."""
        repo_in_memory.add_edge(
            source_id="N_BBB",
            target_id="N_AAA",
            distance_m=45.0,
            is_directed=1,
        )

        fwd = repo_in_memory.get_edge("N_BBB", "N_AAA")
        rev = repo_in_memory.get_edge("N_AAA", "N_BBB")

        assert fwd is not None
        assert fwd["distance_m"] == pytest.approx(45.0)
        assert rev is None

    def test_self_loop_rejected(self, repo_in_memory: CampusRepository):
        """Edges connecting a node to itself must be rejected."""
        with pytest.raises(InvalidEdgeError):
            repo_in_memory.add_edge(
                source_id="N_AAA",
                target_id="N_AAA",
                distance_m=10.0,
            )

    def test_non_positive_distance_rejected(self, repo_in_memory: CampusRepository):
        """Zero or negative distances must be rejected."""
        with pytest.raises(InvalidEdgeError):
            repo_in_memory.add_edge(
                source_id="N_AAA",
                target_id="N_BBB",
                distance_m=0.0,
            )
        with pytest.raises(InvalidEdgeError):
            repo_in_memory.add_edge(
                source_id="N_AAA",
                target_id="N_BBB",
                distance_m=-15.0,
            )

    def test_duplicate_edge_rejected(self, repo_in_memory: CampusRepository):
        """Attempting to insert a duplicate edge pair must raise DuplicateEdgeError."""
        repo_in_memory.add_edge(source_id="N_AAA", target_id="N_BBB", distance_m=50.0)
        with pytest.raises(DuplicateEdgeError):
            repo_in_memory.add_edge(source_id="N_AAA", target_id="N_BBB", distance_m=75.0)


class TestTransactionsAndRollbacks:
    """Test 7: Transaction rollback behavior on error."""

    def test_transaction_rollback_preserves_previous_state(self, repo_in_memory: CampusRepository):
        """If an exception occurs within transaction(), all intermediate writes must roll back."""
        repo_in_memory.upsert_node(node_id="COMMITTED_1", name="Committed Node", category="academic")
        conn = repo_in_memory.get_connection()

        with pytest.raises(RuntimeError):
            with transaction(conn):
                conn.execute(
                    "INSERT INTO nodes (id, name, category) VALUES ('UNCOMMITTED_2', 'Temp Node', 'academic');"
                )
                # Intentionally trigger an error
                raise RuntimeError("Simulated transaction fault")

        assert repo_in_memory.get_node("COMMITTED_1") is not None
        assert repo_in_memory.get_node("UNCOMMITTED_2") is None


class TestBlockagesAndModifications:
    """Test 8 & 9: Edge obstruction handling and user change preservation."""

    def test_edge_blockage_updates_without_deleting_record(self, repo_in_memory: CampusRepository):
        """Blocking a pathway updates status flags and preserves the record."""
        repo_in_memory.upsert_node(node_id="BLK_A", name="Block A", category="academic")
        repo_in_memory.upsert_node(node_id="BLK_B", name="Block B", category="residential")
        repo_in_memory.add_edge(source_id="BLK_A", target_id="BLK_B", distance_m=100.0)

        repo_in_memory.set_edge_blocked(
            source_id="BLK_A",
            target_id="BLK_B",
            is_blocked=True,
            block_reason="Monsoon Waterlogging",
        )

        edge = repo_in_memory.get_edge("BLK_A", "BLK_B")
        assert edge is not None
        assert edge["is_blocked"] == 1
        assert edge["block_reason"] == "Monsoon Waterlogging"

        # Verify list_edges filtering
        active_edges = repo_in_memory.list_edges(include_blocked=False)
        all_edges = repo_in_memory.list_edges(include_blocked=True)
        assert len(active_edges) == 0
        assert len(all_edges) == 1

        # Unblock pathway
        repo_in_memory.set_edge_blocked(source_id="BLK_A", target_id="BLK_B", is_blocked=False)
        unblocked_edge = repo_in_memory.get_edge("BLK_A", "BLK_B")
        assert unblocked_edge["is_blocked"] == 0
        assert unblocked_edge["block_reason"] is None

    def test_blocking_nonexistent_edge_raises_error(self, repo_in_memory: CampusRepository):
        """Attempting to block a non-existent edge raises EdgeNotFoundError."""
        with pytest.raises(EdgeNotFoundError):
            repo_in_memory.set_edge_blocked("NONE_1", "NONE_2", is_blocked=True)


class TestIdempotentSeedingAndProvenance:
    """Test 9 & 10: Idempotent seeding and data provenance integrity."""

    def test_seeding_is_idempotent(self, repo_temp_file: CampusRepository, sample_landmarks_file: Path):
        """Running seed_database repeatedly produces the exact same node count with no duplicate errors."""
        res_1 = seed_database(
            db_path=repo_temp_file._db_path,
            landmarks_path=sample_landmarks_file,
            overwrite_existing=False,
        )
        assert res_1["nodes_seeded"] == 2

        # Second execution
        res_2 = seed_database(
            db_path=repo_temp_file._db_path,
            landmarks_path=sample_landmarks_file,
            overwrite_existing=False,
        )
        assert res_2["nodes_seeded"] == 2

        nodes = repo_temp_file.list_nodes()
        assert len(nodes) == 2

    def test_seeding_preserves_user_modifications(
        self, repo_temp_file: CampusRepository, sample_landmarks_file: Path
    ):
        """When overwrite_existing=False, user updates to descriptions are preserved."""
        seed_database(
            db_path=repo_temp_file._db_path,
            landmarks_path=sample_landmarks_file,
            overwrite_existing=False,
        )

        # User modifies description
        repo_temp_file.upsert_node(
            node_id="ACAD_TEST_1",
            name="Academic Test Block",
            category="academic",
            description="User custom note: renovation ongoing.",
            overwrite_existing=True,
        )

        # Run seeder again with overwrite_existing=False
        seed_database(
            db_path=repo_temp_file._db_path,
            landmarks_path=sample_landmarks_file,
            overwrite_existing=False,
        )

        node = repo_temp_file.get_node("ACAD_TEST_1")
        assert node["description"] == "User custom note: renovation ongoing."

    def test_verified_data_distinction_and_routing_status(self, repo_temp_file: CampusRepository):
        """Verified campus database must have 0 edges and has_verified_routing_network=false."""
        seed_database(db_path=repo_temp_file._db_path, seed_demo=False)

        # Verify routing network is flagged as unavailable
        assert repo_temp_file.has_verified_routing_network() is False

        # Verify no fabricated edges exist in production database
        edges = repo_temp_file.list_edges()
        assert len(edges) == 0

        # Verify all seeded landmarks carry official provenance
        nodes = repo_temp_file.list_nodes()
        assert len(nodes) >= 15
        for node in nodes:
            assert node["source_provenance"] == "OFFICIAL_INSTITUTIONAL"
            assert node["verification_status"] == "OFFICIAL_REFERENCE"
            # Coordinates must be null since not yet surveyed
            assert node["latitude"] is None
            assert node["longitude"] is None

    def test_demonstration_data_isolation(self, repo_temp_file: CampusRepository):
        """When seed_demo=True, synthetic records are flagged with SYNTHETIC_DEMO provenance."""
        seed_database(db_path=repo_temp_file._db_path, seed_demo=True)

        demo_node = repo_temp_file.get_node("DEMO_GATE")
        assert demo_node is not None
        assert demo_node["source_provenance"] == "SYNTHETIC_DEMO"
        assert demo_node["verification_status"] == "SYNTHETIC_DEMO"

        demo_edge = repo_temp_file.get_edge("DEMO_ACAD", "DEMO_GATE")
        assert demo_edge is not None
        assert demo_edge["source_provenance"] == "SYNTHETIC_DEMO"
        assert demo_edge["verification_status"] == "SYNTHETIC_DEMO"
