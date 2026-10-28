"""
Smart Campus Navigation — Main Streamlit Application.

Orchestrates the interactive web interface, managing application state, mode switching
(Campus Context vs Synthetic Demonstration), routing engine invocation, dynamic blockage
controls, and Folium map rendering.
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so that both 'app' and 'campus_routing'
# packages are importable on all platforms (including Streamlit Community Cloud).
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from typing import Optional

import streamlit as st
from streamlit_folium import st_folium

from app.components.blockage_panel import apply_session_blockages_to_graph, render_blockage_panel
from app.components.metrics_card import render_metrics_card
from app.components.sidebar import (
    MODE_CAMPUS_CONTEXT,
    MODE_SYNTHETIC_DEMO,
    SidebarState,
    render_sidebar,
)
from campus_routing.algorithms.dijkstra import RouteResult, dijkstra_shortest_path
from campus_routing.config import (
    DEFAULT_DB_PATH,
    DEMO_GRAPH_PATH,
    REFERENCE_CAMPUS_NAME,
    REFERENCE_LATITUDE,
    REFERENCE_LOCATION,
    REFERENCE_LONGITUDE,
)
from campus_routing.db.repository import CampusRepository
from campus_routing.exceptions import (
    IncompleteCoordinateError,
    NodeNotFoundError,
    PathNotFoundError,
    ValidationError,
)
from campus_routing.models.graph import CampusGraph
from campus_routing.visualization.map_builder import (
    create_campus_context_map,
    create_demonstration_map,
)


def init_app_config() -> None:
    """Configures Streamlit page metadata and injects responsive design CSS tokens."""
    st.set_page_config(
        page_title="Smart Campus Navigation — IIIT Kottayam",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Injected modern CSS tokens for contrast, layout spacing, and banner badges
    st.markdown(
        """
        <style>
            /* Main container typography and padding */
            .main-header {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin-bottom: 8px;
            }
            .campus-subtitle {
                color: #546E7A;
                font-size: 14px;
                font-weight: 500;
                margin-top: -6px;
                margin-bottom: 16px;
            }
            /* Persistent Mode B Synthetic Warning Banner */
            .synthetic-alert-banner {
                background: linear-gradient(90deg, #FFEBEE 0%, #FFCDD2 100%);
                border-left: 6px solid #C62828;
                padding: 12px 18px;
                border-radius: 4px;
                color: #B71C1C;
                font-size: 13px;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            }
            /* Campus Context Institutional Banner */
            .context-info-banner {
                background: linear-gradient(90deg, #E3F2FD 0%, #BBDEFB 100%);
                border-left: 6px solid #1565C0;
                padding: 12px 18px;
                border-radius: 4px;
                color: #0D47A1;
                font-size: 13px;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            }
            /* Empty state card */
            .empty-state-card {
                background-color: #FAFAFA;
                border: 1px solid #ECEFF1;
                border-radius: 8px;
                padding: 20px;
                margin-top: 14px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_demonstration_graph() -> CampusGraph:
    """
    Loads an isolated in-memory CampusGraph from demonstration_graph.json.

    Never inserts records into the production campus database. Applies any
    dynamic blockages currently saved in Streamlit session state.
    """
    graph = CampusGraph.from_json(DEMO_GRAPH_PATH)
    apply_session_blockages_to_graph(graph)
    return graph


def render_campus_context_view(repo: CampusRepository) -> None:
    """
    Renders Mode A: Campus Context.

    Displays verified institutional datum, existing campus metadata, and a clear
    empty state explaining that pedestrian routing is disabled until field survey completion.
    """
    st.markdown(
        """
        <div class="context-info-banner">
            <b>📍 INSTITUTIONAL CAMPUS REFERENCE VIEW — FIELD SURVEY PENDING</b><br>
            Showing verified institutional reference datum for IIIT Kottayam. Real campus pedestrian
            routing is currently <b>disabled</b> because verified footway geometries and building-level
            GPS coordinates have not yet been surveyed.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_map, col_details = st.columns([7, 5])

    with col_map:
        st.markdown("##### Campus Location Overview")
        # Reuse existing map builder
        context_map = create_campus_context_map(repo=repo, width="100%", height="540px")
        st_folium(context_map, width="100%", height=540, returned_objects=[])

    with col_details:
        st.markdown("##### Institutional Verification Status")

        landmarks = repo.list_nodes()
        unsurveyed_count = sum(1 for n in landmarks if n.get("latitude") is None)
        has_network = repo.has_verified_routing_network()

        st.markdown(
            f"""
            <div class="empty-state-card">
                <div style="font-weight: 700; color: #263238; font-size: 15px; margin-bottom: 8px;">
                    {REFERENCE_CAMPUS_NAME}
                </div>
                <div style="font-size: 12px; color: #546E7A; margin-bottom: 12px;">
                    <b>Institutional Reference Datum:</b> {REFERENCE_LATITUDE:.6f}° N, {REFERENCE_LONGITUDE:.6f}° E<br>
                    <b>Location:</b> {REFERENCE_LOCATION}
                </div>
                <hr style="margin: 10px 0; border: 0; border-top: 1px solid #E0E0E0;">
                <div style="font-size: 13px; line-height: 1.6;">
                    <b>Database Landmark Count:</b> {len(landmarks)} official landmarks<br>
                    <b>Awaiting GPS Coordinates:</b> <span style="color: #D84315; font-weight: 600;">{unsurveyed_count}</span><br>
                    <b>Verified Walking Pathways:</b> <span style="color: #D84315; font-weight: 600;">0 (Unsurveyed)</span><br>
                    <b>Pedestrian Routing Engine:</b> <span style="color: {'#2E7D32' if has_network else '#C62828'}; font-weight: 600;">{'Ready' if has_network else 'Inactive (Missing Survey Data)'}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="background-color: #FFF9C4; border-left: 4px solid #FBC02D; padding: 12px; border-radius: 4px; font-size: 12px; margin-top: 14px; color: #5D4037;">
                <b>📋 Required Field Survey Data to Enable Real-World Navigation:</b>
                <ol style="margin-top: 6px; padding-left: 18px; margin-bottom: 0;">
                    <li>High-precision RTK-GPS survey of internal walkways, sidewalks, and ramps.</li>
                    <li>Micro-level coordinate capture for all building entrances and accessibility ramps.</li>
                    <li>Walkway attribute recording: surface type (asphalt, concrete, stairs, unpaved) and width.</li>
                    <li>Obstacle, barrier, and elevation profile mapping for wheelchair compliance.</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_synthetic_demo_view(demo_graph: CampusGraph, sidebar_state: SidebarState) -> None:
    """
    Renders Mode B: Synthetic Demonstration.

    Calculates routes, applies dynamic blockages, and renders the interactive demo map.
    """
    st.markdown(
        """
        <div class="synthetic-alert-banner">
            <b>⚠️ SYNTHETIC DEMONSTRATION — NOT REAL CAMPUS NAVIGATION</b><br>
            Displaying an isolated synthetic test dataset (6 nodes, 6 edges) for testing Dijkstra
            shortest-path calculation, pathway closures, and accessibility filtering.
            Distances and routes are <b>simulated demonstration values</b>, not verified campus facts.
        </div>
        """,
        unsafe_allow_html=True,
    )

    origin_id = sidebar_state.origin_id
    destination_id = sidebar_state.destination_id
    route_result: Optional[RouteResult] = None
    routing_error: Optional[str] = None

    # Calculate route if origin and destination are present
    if origin_id is not None and destination_id is not None:
        if origin_id == destination_id:
            route_result = RouteResult(
                nodes=[origin_id],
                total_distance_m=0.0,
                total_cost=0.0,
            )
        else:
            try:
                route_result = dijkstra_shortest_path(
                    graph=demo_graph,
                    source=origin_id,
                    target=destination_id,
                    accessible_only=sidebar_state.accessible_only,
                )
            except PathNotFoundError:
                routing_error = "unreachable"
            except (NodeNotFoundError, ValidationError, IncompleteCoordinateError) as exc:
                routing_error = str(exc)

    # 1. Routing Status / Metrics Card
    if route_result is not None:
        origin_node = demo_graph.get_node(origin_id)
        dest_node = demo_graph.get_node(destination_id)
        render_metrics_card(
            graph=demo_graph,
            route=route_result,
            origin_name=origin_node.name,
            destination_name=dest_node.name,
        )
    elif routing_error == "unreachable":
        origin_node = demo_graph.get_node(origin_id)
        dest_node = demo_graph.get_node(destination_id)
        st.warning(
            f"⚠️ **Destination Unreachable:** No valid pathway connects **{origin_node.name}** "
            f"to **{dest_node.name}** under current settings.\n\n"
            f"• If **accessibility filtering** is enabled, required routes may contain stairs or trails.\n"
            f"• If **dynamic blockages** are active, the path may be obstructed. Check the pathway panel below."
        )
    elif routing_error is not None:
        st.error(f"Routing Error: {routing_error}")
    else:
        st.info("Select origin and destination in the sidebar, then click **Calculate Shortest Route**.")

    # 2. Main Folium Interactive Demonstration Map
    try:
        demo_map = create_demonstration_map(
            graph=demo_graph,
            route_result=route_result,
            width="100%",
            height="560px",
        )
        st_folium(demo_map, width="100%", height=560, returned_objects=[])
    except Exception as exc:
        st.error(f"Error rendering demonstration map: {exc}")

    # 3. Dynamic Pathway Blockage Management Panel
    st.markdown("---")
    render_blockage_panel(demo_graph)


def main() -> None:
    """Main application entrypoint."""
    init_app_config()

    # Application Header
    st.markdown(
        """
        <div class="main-header">
            <h2 style="margin: 0; color: #0D47A1; display: inline-flex; align-items: center; gap: 8px;">
                🧭 Smart Campus Navigation System
            </h2>
            <div class="campus-subtitle">
                Indian Institute of Information Technology Kottayam — Academic Navigation Project
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Isolated database and demonstration graph loading
    repo = CampusRepository(DEFAULT_DB_PATH)
    demo_graph = load_demonstration_graph()

    # Render sidebar
    sidebar_state = render_sidebar(repo=repo, demo_graph=demo_graph)

    # Route view by selected mode
    if sidebar_state.mode == MODE_CAMPUS_CONTEXT:
        render_campus_context_view(repo)
    else:
        render_synthetic_demo_view(demo_graph, sidebar_state)


if __name__ == "__main__":
    main()
