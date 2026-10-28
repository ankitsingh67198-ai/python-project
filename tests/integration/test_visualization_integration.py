"""
Integration tests for map visualization with routing engine and database.

Verifies:
1. End-to-end pipeline: Dijkstra shortest path calculation -> RouteResult -> Folium map overlay.
2. End-to-end pipeline: Shortest path -> RouteDirections generation.
3. Strict data isolation: Map rendering must NEVER insert synthetic records into the production SQLite database.
4. Campus context map never claims or draws unverified pedestrian pathways.
5. Separation of physical ground distance and routing cost across the visualization pipeline.
"""

from pathlib import Path
import sqlite3
import pytest

from campus_routing.algorithms.dijkstra import dijkstra_shortest_path
from campus_routing.config import DEMO_GRAPH_PATH
from campus_routing.db.connection import get_db_connection
from campus_routing.db.repository import CampusRepository
from campus_routing.db.seeder import seed_database
from campus_routing.models.graph import CampusGraph
from campus_routing.visualization.directions import generate_route_directions
from campus_routing.visualization.map_builder import (
    create_campus_context_map,
    create_demonstration_map,
    export_map_to_html,
)


class TestVisualizationIntegration:
    """Integration test suite connecting algorithms, cartography, and database."""

    def test_end_to_end_routing_and_map_rendering(self, tmp_path: Path) -> None:
        """Calculates Dijkstra route on demo graph, visualizes it, and exports valid HTML."""
        graph = CampusGraph.from_json_file(DEMO_GRAPH_PATH)

        # Route from Gate to Hostel
        route = dijkstra_shortest_path(graph, "DEMO_GATE", "DEMO_HOSTEL")
        assert route.nodes[0] == "DEMO_GATE"
        assert route.nodes[-1] == "DEMO_HOSTEL"
        assert route.total_distance_m > 0.0

        # Generate interactive map
        demo_map = create_demonstration_map(graph, route_result=route)
        out_html = tmp_path / "integrated_route_map.html"
        html_str = export_map_to_html(demo_map, file_path=out_html)

        # Validate rendered components
        assert "CALCULATED ROUTE" in html_str
        assert "DEMO_GATE" in html_str
        assert "DEMO_HOSTEL" in html_str
        assert f"{route.total_distance_m:.1f} m" in html_str
        assert "🏁 ROUTE ORIGIN (START)" in html_str
        assert "🎯 ROUTE DESTINATION" in html_str
        assert out_html.exists()

        # Generate directional instructions
        directions = generate_route_directions(graph, route)
        assert directions.step_count == route.hop_count
        assert directions.total_distance_m == route.total_distance_m
        first_step = directions.steps[0]
        assert first_step.from_node_name == "Demo Campus Main Gate"

    def test_visualization_never_inserts_synthetic_records_into_database(
        self,
        temp_db_path: Path,
    ) -> None:
        """
        Executing map visualization functions must NEVER modify or inject
        synthetic demonstration nodes/edges into the production SQLite database.
        """
        # 1. Initialize production database with verified landmark seeds
        seed_database(db_path=temp_db_path, seed_demo=False)

        repo = CampusRepository(db_path=temp_db_path)
        initial_nodes = repo.list_nodes()
        initial_edges = repo.list_edges()
        initial_routing_flag = repo.get_metadata("has_verified_routing_network")

        assert len(initial_nodes) == 18
        assert len(initial_edges) == 0
        assert initial_routing_flag == "false"

        # 2. Render Campus Context Map using this repo
        context_map = create_campus_context_map(repo=repo)
        _ = export_map_to_html(context_map)

        # 3. Render Synthetic Demonstration Map
        demo_graph = CampusGraph.from_json_file(DEMO_GRAPH_PATH)
        route = dijkstra_shortest_path(demo_graph, "DEMO_GATE", "DEMO_ACAD")
        demo_map = create_demonstration_map(demo_graph, route_result=route)
        _ = export_map_to_html(demo_map)

        # 4. Verify database state remains completely untouched
        after_nodes = repo.list_nodes()
        after_edges = repo.list_edges()
        after_routing_flag = repo.get_metadata("has_verified_routing_network")

        assert len(after_nodes) == 18
        assert len(after_edges) == 0
        assert after_routing_flag == "false"

        # Ensure no DEMO_ nodes were inserted into the SQLite database
        demo_nodes_in_db = [n for n in after_nodes if n["id"].startswith("DEMO_")]
        assert len(demo_nodes_in_db) == 0

        repo.close()

    def test_campus_context_map_makes_no_false_pathway_claims(self, temp_db_path: Path) -> None:
        """
        Campus context map HTML must not claim verified walking paths exist,
        and must not render polyline pathways when coordinates are unsurveyed.
        """
        seed_database(db_path=temp_db_path, seed_demo=False)
        repo = CampusRepository(db_path=temp_db_path)

        context_map = create_campus_context_map(repo=repo)
        html_str = export_map_to_html(context_map)

        # Must explicitly warn that pathways are unsurveyed
        assert "unsurveyed" in html_str.lower()
        assert "18 landmarks recorded" in html_str

        # Must not have any PolyLine pathway entities plotted
        assert "WALKING PATHWAY" not in html_str
        assert "PATHWAY SEGMENT" not in html_str
        assert "CALCULATED ROUTE" not in html_str

        repo.close()
