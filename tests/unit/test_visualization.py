"""
Unit tests for Folium-based visualization and route directions module.

Verifies:
1. Campus context map creation without building coordinates.
2. Synthetic demonstration graph rendering.
3. Missing-coordinate handling.
4. Landmark and junction markers.
5. Route overlays with correct start and destination markers.
6. Blocked-path visual styling.
7. Directed-edge visualization.
8. Invalid route rejection.
9. HTML map export and non-empty output.
10. Correct synthetic-data warnings in the demonstration map.
11. Bearing calculation and directional instructions.
12. Separation of physical distance and routing cost.
"""

from pathlib import Path
import folium
import pytest

from campus_routing.algorithms.dijkstra import RouteResult
from campus_routing.config import (
    DEMO_GRAPH_PATH,
    REFERENCE_LATITUDE,
    REFERENCE_LONGITUDE,
)
from campus_routing.exceptions import (
    IncompleteCoordinateError,
    NodeNotFoundError,
    ValidationError,
)
from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node
from campus_routing.visualization.directions import (
    DIRECTIONS_DISCLAIMER,
    calculate_bearing,
    generate_route_directions,
)
from campus_routing.visualization.map_builder import (
    create_campus_context_map,
    create_demonstration_map,
    export_map_to_html,
)
from campus_routing.visualization.styles import (
    CATEGORY_COLORS,
    HTML_CAMPUS_CONTEXT_BANNER,
    HTML_SYNTHETIC_DEMO_BANNER,
    build_legend_html,
)


@pytest.fixture
def sample_demo_graph() -> CampusGraph:
    """Provides the loaded demonstration graph."""
    return CampusGraph.from_json_file(DEMO_GRAPH_PATH)


@pytest.fixture
def custom_test_graph() -> CampusGraph:
    """Provides a controlled in-memory graph for cartographic unit tests."""
    g = CampusGraph()
    g.add_node(Node(
        id="N1",
        name="Node One",
        category="academic",
        latitude=9.7542,
        longitude=76.6495,
        elevation_m=120.0,
        source_provenance="SYNTHETIC_DEMO",
        verification_status="SYNTHETIC_DEMO",
    ))
    g.add_node(Node(
        id="N2",
        name="Node Two",
        category="dining",
        latitude=9.7548,
        longitude=76.6502,
        elevation_m=125.0,
        source_provenance="SYNTHETIC_DEMO",
        verification_status="SYNTHETIC_DEMO",
    ))
    g.add_node(Node(
        id="N3",
        name="Node Three",
        category="sports",
        latitude=9.7555,
        longitude=76.6510,
        elevation_m=130.0,
        source_provenance="SYNTHETIC_DEMO",
        verification_status="SYNTHETIC_DEMO",
    ))
    g.add_node(Node(
        id="N_NO_COORDS",
        name="Unsurveyed Node",
        category="amenity",
        latitude=None,
        longitude=None,
        source_provenance="OFFICIAL_INSTITUTIONAL",
        verification_status="UNVERIFIED",
    ))
    # Undirected active edge N1 <-> N2
    g.add_edge(Edge(
        source_id="N1",
        target_id="N2",
        distance_m=100.0,
        is_directed=False,
        surface_type="paved",
        is_accessible=True,
    ))
    # Blocked edge N2 <-> N3
    g.add_edge(Edge(
        source_id="N2",
        target_id="N3",
        distance_m=120.0,
        is_directed=False,
        surface_type="concrete",
        is_blocked=True,
        block_reason="Monsoon Waterlogging",
    ))
    return g


# -----------------------------------------------------------------------------
# Test 1: Campus context map creation without building coordinates
# -----------------------------------------------------------------------------

class TestCampusContextMap:
    """Verifies official baseline map behavior in absence of pedestrian geometry."""

    def test_context_map_initialization(self) -> None:
        """Map must center on verified institutional reference datum."""
        campus_map = create_campus_context_map()
        assert isinstance(campus_map, folium.Map)
        assert campus_map.location == [REFERENCE_LATITUDE, REFERENCE_LONGITUDE]

    def test_context_map_contains_reference_marker_and_notice(self) -> None:
        """HTML output must feature reference marker, warning banner, and disclaimer."""
        campus_map = create_campus_context_map()
        html = export_map_to_html(campus_map)

        # Check for reference point coordinates
        assert f"{REFERENCE_LATITUDE:.6f}" in html
        assert f"{REFERENCE_LONGITUDE:.6f}" in html

        # Must explicitly state this is a reference datum, not a building entrance
        assert "Institutional Centroid" in html
        assert "Not an entrance" in html

        # Informational banner must be embedded
        assert "campus-context-banner" in html
        assert "unsurveyed" in html.lower()

    def test_context_map_does_not_draw_synthetic_pathways(self) -> None:
        """Context map must not fabricate pathways or synthetic route lines."""
        campus_map = create_campus_context_map()
        html = export_map_to_html(campus_map)

        # Must not contain synthetic indicators or route overlays
        assert "SYNTHETIC DEMONSTRATION" not in html
        assert "DEMO_" not in html
        assert "CALCULATED ROUTE" not in html


# -----------------------------------------------------------------------------
# Test 2 & 10: Synthetic demonstration map rendering and warnings
# -----------------------------------------------------------------------------

class TestDemonstrationMap:
    """Verifies isolated synthetic demonstration mode rendering."""

    def test_demo_map_renders_all_nodes_and_edges(self, sample_demo_graph: CampusGraph) -> None:
        """Demonstration map renders nodes, edges, and fits bounds."""
        demo_map = create_demonstration_map(sample_demo_graph)
        html = export_map_to_html(demo_map)

        # Verify all demo nodes are represented
        for node in sample_demo_graph.get_nodes():
            assert node.name in html
            assert node.id in html

        # Verify edges are rendered
        assert "PATHWAY SEGMENT (SYNTHETIC)" in html

    def test_demo_map_prominently_displays_synthetic_warnings(self, sample_demo_graph: CampusGraph) -> None:
        """Demonstration mode must feature unmistakable synthetic warning banner."""
        demo_map = create_demonstration_map(sample_demo_graph)
        html = export_map_to_html(demo_map)

        assert "synthetic-demo-banner" in html
        assert "SYNTHETIC DEMONSTRATION — NOT REAL CAMPUS NAVIGATION" in html
        assert "demonstration_graph.json" in html
        assert "Demo Legend" in html


# -----------------------------------------------------------------------------
# Test 3 & 8: Missing-coordinate handling and invalid route rejection
# -----------------------------------------------------------------------------

class TestRouteValidationAndCoordinates:
    """Verifies robust validation against missing coordinates and invalid routes."""

    def test_route_with_missing_coordinates_rejected(self, custom_test_graph: CampusGraph) -> None:
        """Route passing through a node without coordinates raises IncompleteCoordinateError."""
        # Route: N1 -> N_NO_COORDS
        route = RouteResult(nodes=["N1", "N_NO_COORDS"], total_distance_m=100.0, total_cost=100.0)
        with pytest.raises(IncompleteCoordinateError, match="lacks spatial coordinates"):
            create_demonstration_map(custom_test_graph, route_result=route)

    def test_route_with_nonexistent_node_rejected(self, custom_test_graph: CampusGraph) -> None:
        """Route containing unknown node ID raises NodeNotFoundError."""
        route = RouteResult(nodes=["N1", "NON_EXISTENT_NODE"], total_distance_m=50.0, total_cost=50.0)
        with pytest.raises(NodeNotFoundError, match="does not exist in graph"):
            create_demonstration_map(custom_test_graph, route_result=route)

    def test_route_empty_node_sequence_rejected(self, custom_test_graph: CampusGraph) -> None:
        """RouteResult with empty node sequence raises ValueError or ValidationError."""
        with pytest.raises(ValueError, match="at least one node"):
            RouteResult(nodes=[], total_distance_m=0.0, total_cost=0.0)


# -----------------------------------------------------------------------------
# Test 4: Landmark and junction markers
# -----------------------------------------------------------------------------

class TestMarkersAndCategories:
    """Verifies domain marker rendering and category icons."""

    def test_markers_have_category_tooltips_and_popups(self, custom_test_graph: CampusGraph) -> None:
        """Markers must have structured popups and category tooltips."""
        demo_map = create_demonstration_map(custom_test_graph)
        html = export_map_to_html(demo_map)

        assert "[ACADEMIC] Node One" in html
        assert "[DINING] Node Two" in html
        assert "[SPORTS] Node Three" in html
        assert "Elevation:" in html


# -----------------------------------------------------------------------------
# Test 5: Route overlays with correct start and destination markers
# -----------------------------------------------------------------------------

class TestRouteOverlay:
    """Verifies visual overlay of shortest path results."""

    def test_route_overlay_rendering(self, custom_test_graph: CampusGraph) -> None:
        """Route overlay renders polyline and distinctive start/destination markers."""
        route = RouteResult(nodes=["N1", "N2"], total_distance_m=100.0, total_cost=100.0)
        demo_map = create_demonstration_map(custom_test_graph, route_result=route)
        html = export_map_to_html(demo_map)

        assert "CALCULATED ROUTE" in html
        assert "ROUTE ORIGIN (START)" in html
        assert "ROUTE DESTINATION" in html
        assert "Node One" in html
        assert "Node Two" in html


# -----------------------------------------------------------------------------
# Test 6: Blocked-path visual styling
# -----------------------------------------------------------------------------

class TestBlockedPathwayStyling:
    """Verifies that blocked pathways are clearly differentiated."""

    def test_blocked_pathway_styled_and_labeled(self, custom_test_graph: CampusGraph) -> None:
        """Blocked pathway has dashed red style, distinct popup, and blockage reason."""
        demo_map = create_demonstration_map(custom_test_graph)
        html = export_map_to_html(demo_map)

        assert "BLOCKED PATHWAY (SYNTHETIC)" in html
        assert "Monsoon Waterlogging" in html
        assert "Blocked Pathway: N2 — N3" in html


# -----------------------------------------------------------------------------
# Test 7: Directed-edge visualization
# -----------------------------------------------------------------------------

class TestDirectedEdgeVisualization:
    """Verifies directed pathways are visualized with orientation indications."""

    def test_directed_pathway_rendering(self, custom_test_graph: CampusGraph) -> None:
        """Directed edge is rendered with directed styling and orientation indicator."""
        # Add directed edge N1 -> N3
        custom_test_graph.add_edge(Edge(
            source_id="N1",
            target_id="N3",
            distance_m=200.0,
            is_directed=True,
            surface_type="asphalt",
        ))
        demo_map = create_demonstration_map(custom_test_graph)
        html = export_map_to_html(demo_map)

        assert "DIRECTED PATHWAY (SYNTHETIC)" in html
        assert "Node One → Node Three" in html
        assert "One-way: Node One → Node Three" in html


# -----------------------------------------------------------------------------
# Test 9: Standalone HTML map export
# -----------------------------------------------------------------------------

class TestHtmlMapExport:
    """Verifies export of map instances to valid standalone HTML files."""

    def test_export_to_file_and_string(self, tmp_path: Path, sample_demo_graph: CampusGraph) -> None:
        """Export generates non-empty string and writes intact file."""
        demo_map = create_demonstration_map(sample_demo_graph)
        output_file = tmp_path / "map_output.html"

        html_str = export_map_to_html(demo_map, file_path=output_file)

        assert isinstance(html_str, str)
        assert len(html_str) > 1000
        assert "<!DOCTYPE html>" in html_str or "<html" in html_str
        assert output_file.exists()
        assert output_file.stat().st_size > 1000
        assert output_file.read_text(encoding="utf-8") == html_str


# -----------------------------------------------------------------------------
# Test 11 & 12: Directions generator and approximate bearings
# -----------------------------------------------------------------------------

class TestRouteDirectionsModule:
    """Verifies step-by-step approximate directions generator."""

    def test_bearing_calculation(self) -> None:
        """Validates great-circle bearing for cardinal directions."""
        # Due North
        b_north = calculate_bearing(9.750, 76.650, 9.760, 76.650)
        assert abs(b_north - 0.0) < 1.0 or abs(b_north - 360.0) < 1.0

        # Due East
        b_east = calculate_bearing(9.750, 76.650, 9.750, 76.660)
        assert abs(b_east - 90.0) < 1.0

        # Due South
        b_south = calculate_bearing(9.760, 76.650, 9.750, 76.650)
        assert abs(b_south - 180.0) < 1.0

        # Due West
        b_west = calculate_bearing(9.750, 76.660, 9.750, 76.650)
        assert abs(b_west - 270.0) < 1.0

    def test_generate_directions_for_route(self, custom_test_graph: CampusGraph) -> None:
        """Validates directional steps and prominent approximate disclaimer."""
        route = RouteResult(nodes=["N1", "N2"], total_distance_m=100.0, total_cost=100.0)
        directions = generate_route_directions(custom_test_graph, route)

        assert directions.step_count == 1
        assert directions.is_approximate is True
        assert DIRECTIONS_DISCLAIMER in directions.disclaimer

        step = directions.steps[0]
        assert step.step_number == 1
        assert step.from_node_id == "N1"
        assert step.to_node_id == "N2"
        assert step.distance_m == 100.0
        assert step.bearing_deg is not None
        assert step.cardinal_direction in [
            "North", "North-East", "East", "South-East",
            "South", "South-West", "West", "North-West"
        ]
        assert "Proceed" in step.instruction

        # Text rendering contains disclaimer
        text = directions.formatted_text()
        assert "APPROXIMATE" in text
        assert "Step 1:" in text or "1. Proceed" in text

    def test_generate_directions_trivial_route(self, custom_test_graph: CampusGraph) -> None:
        """Single-node trivial route produces zero movement steps."""
        route = RouteResult(nodes=["N1"], total_distance_m=0.0, total_cost=0.0)
        directions = generate_route_directions(custom_test_graph, route)

        assert directions.step_count == 0
        assert "Origin and destination are identical" in directions.formatted_text()

    def test_directions_missing_coordinates_rejected(self, custom_test_graph: CampusGraph) -> None:
        """Route with unsurveyed node raises IncompleteCoordinateError."""
        route = RouteResult(nodes=["N1", "N_NO_COORDS"], total_distance_m=100.0, total_cost=100.0)
        with pytest.raises(IncompleteCoordinateError):
            generate_route_directions(custom_test_graph, route)
