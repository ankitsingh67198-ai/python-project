"""
Unit tests for Streamlit application components and utility functions.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.components.blockage_panel import (
    SESSION_BLOCKED_EDGES_KEY,
    apply_session_blockages_to_graph,
    get_blocked_edges,
)
from app.components.metrics_card import (
    ASSUMED_WALKING_SPEED_MPS,
    calculate_theoretical_walking_time,
    render_metrics_card,
)
from app.components.sidebar import (
    MODE_CAMPUS_CONTEXT,
    MODE_SYNTHETIC_DEMO,
    SidebarState,
)
from campus_routing.algorithms.dijkstra import RouteResult
from campus_routing.config import DEMO_GRAPH_PATH
from campus_routing.db.repository import CampusRepository
from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node


class TestMetricsCardComponent:
    """Unit tests for metrics calculation and formatting."""

    def test_theoretical_walking_time_zero_or_negative(self) -> None:
        """Walking time for 0 m is 0 min."""
        assert calculate_theoretical_walking_time(0.0) == "0 min"
        assert calculate_theoretical_walking_time(-10.0) == "0 min"

    def test_theoretical_walking_time_short_distance(self) -> None:
        """Walking time under 60 seconds returns seconds format."""
        # 42 metres at 1.4 m/s is 30 seconds
        result = calculate_theoretical_walking_time(42.0)
        assert result == "30 sec"

    def test_theoretical_walking_time_longer_distance(self) -> None:
        """Walking time >= 60 seconds returns minutes format."""
        # 168 metres at 1.4 m/s is 120 seconds = 2.0 min
        result = calculate_theoretical_walking_time(168.0)
        assert result == "2.0 min"

    @patch("app.components.metrics_card.st")
    def test_render_metrics_card_trivial_zero_hop(self, mock_st: MagicMock) -> None:
        """Trivial single-node route displays info alert without full metrics cards."""
        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)
        route = RouteResult(nodes=["DEMO_GATE"], total_distance_m=0.0, total_cost=0.0)

        render_metrics_card(graph, route, "Demo Gate", "Demo Gate")
        mock_st.info.assert_called_once()
        assert "identical" in mock_st.info.call_args[0][0]

    @patch("app.components.metrics_card.st")
    def test_render_metrics_card_standard_route(self, mock_st: MagicMock) -> None:
        """Multi-node route displays 4 metrics and waypoint sequence."""
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col, mock_col]

        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)
        route = RouteResult(
            nodes=["DEMO_GATE", "DEMO_ACAD", "DEMO_LIBRARY"],
            total_distance_m=227.5,
            total_cost=227.5,
        )

        render_metrics_card(graph, route, "Demo Gate", "Demo Library")
        assert mock_st.columns.call_count >= 1
        assert mock_st.metric.call_count == 4
        mock_st.caption.assert_called_once()
        assert "Theoretical estimate" in mock_st.caption.call_args[0][0]


class TestBlockagePanelComponent:
    """Unit tests for in-memory dynamic pathway blockage operations."""

    @patch("app.components.blockage_panel.st")
    def test_get_blocked_edges_initializes_empty_dict(self, mock_st: MagicMock) -> None:
        """Retrieves and initializes session-state blockage registry."""
        mock_st.session_state = {}
        result = get_blocked_edges()
        assert result == {}
        assert SESSION_BLOCKED_EDGES_KEY in mock_st.session_state

    @patch("app.components.blockage_panel.st")
    def test_apply_session_blockages_to_graph(self, mock_st: MagicMock) -> None:
        """Session-state blockages are applied to in-memory graph without mutating files."""
        mock_st.session_state = {
            SESSION_BLOCKED_EDGES_KEY: {
                ("DEMO_ACAD", "DEMO_GATE"): "Water pipe repair",
            }
        }
        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)
        assert not graph.get_edge("DEMO_ACAD", "DEMO_GATE").is_blocked

        apply_session_blockages_to_graph(graph)

        edge = graph.get_edge("DEMO_ACAD", "DEMO_GATE")
        assert edge.is_blocked
        assert edge.block_reason == "Water pipe repair"

        # Other edges remain unblocked
        other_edge = graph.get_edge("DEMO_ACAD", "DEMO_LIBRARY")
        assert not other_edge.is_blocked


class TestSidebarState:
    """Unit tests for SidebarState dataclass."""

    def test_sidebar_state_immutable(self) -> None:
        """SidebarState is frozen and holds expected attributes."""
        state = SidebarState(
            mode=MODE_CAMPUS_CONTEXT,
            origin_id=None,
            destination_id=None,
            accessible_only=False,
            calculate_requested=False,
        )
        assert state.mode == MODE_CAMPUS_CONTEXT
        assert state.origin_id is None
        assert not state.accessible_only

        with pytest.raises(Exception):
            state.mode = MODE_SYNTHETIC_DEMO  # type: ignore[misc]


class TestSharedMapBuilderAndMissingCoordinates:
    """Verifies that Streamlit views delegate correctly to shared map builders and handle missing coordinates."""

    @patch("app.streamlit_app.st_folium")
    @patch("app.streamlit_app.create_campus_context_map")
    def test_campus_context_delegates_to_map_builder(
        self,
        mock_create_context_map: MagicMock,
        mock_st_folium: MagicMock,
    ) -> None:
        """render_campus_context_view invokes create_campus_context_map with repo."""
        from app.streamlit_app import render_campus_context_view
        mock_repo = MagicMock(spec=CampusRepository)
        mock_repo.list_nodes.return_value = [{"id": "TEST", "name": "Test Landmark", "latitude": None}]
        mock_repo.has_verified_routing_network.return_value = False

        render_campus_context_view(mock_repo)

        mock_create_context_map.assert_called_once_with(repo=mock_repo, width="100%", height="540px")
        mock_st_folium.assert_called_once()

    @patch("app.streamlit_app.st_folium")
    @patch("app.streamlit_app.create_demonstration_map")
    def test_synthetic_demo_delegates_to_map_builder(
        self,
        mock_create_demo_map: MagicMock,
        mock_st_folium: MagicMock,
    ) -> None:
        """render_synthetic_demo_view invokes create_demonstration_map with calculated route."""
        from app.streamlit_app import render_synthetic_demo_view
        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)
        sidebar_state = SidebarState(
            mode=MODE_SYNTHETIC_DEMO,
            origin_id="DEMO_GATE",
            destination_id="DEMO_HOSTEL",
            accessible_only=False,
            calculate_requested=True,
        )

        render_synthetic_demo_view(graph, sidebar_state)

        mock_create_demo_map.assert_called_once()
        call_kwargs = mock_create_demo_map.call_args[1]
        assert call_kwargs["graph"] == graph
        assert call_kwargs["route_result"] is not None
        assert call_kwargs["route_result"].nodes[0] == "DEMO_GATE"
        mock_st_folium.assert_called_once()

    @patch("app.streamlit_app.st_folium")
    @patch("app.streamlit_app.st")
    def test_missing_coordinates_handled_without_crash(
        self,
        mock_st: MagicMock,
        mock_st_folium: MagicMock,
    ) -> None:
        """Synthetic demo view handles nodes with missing coordinates safely."""
        from app.streamlit_app import render_synthetic_demo_view
        # Create a graph with a node lacking coordinates
        graph = CampusGraph()
        n1 = Node(id="N_NO_COORD", name="No Coord Node", category="academic", latitude=None, longitude=None)
        n2 = Node(id="N_WITH_COORD", name="With Coord Node", category="academic", latitude=9.755, longitude=76.650)
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge(Edge(source_id="N_NO_COORD", target_id="N_WITH_COORD", distance_m=100.0))

        sidebar_state = SidebarState(
            mode=MODE_SYNTHETIC_DEMO,
            origin_id="N_NO_COORD",
            destination_id="N_WITH_COORD",
            accessible_only=False,
            calculate_requested=True,
        )

        # Should handle route error gracefully without unhandled crash
        render_synthetic_demo_view(graph, sidebar_state)
        # Verify an error or warning was surfaced to user
        assert mock_st.error.called or mock_st.warning.called
