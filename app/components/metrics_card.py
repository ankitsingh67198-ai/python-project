"""
Metrics card and route summary component for Smart Campus Navigation.

Displays physical distance, routing impedance cost, hop count, theoretical estimated
walking time, and structured approximate directional guidance with cartographic disclaimers.
"""

from typing import Optional

import streamlit as st

from campus_routing.algorithms.dijkstra import RouteResult
from campus_routing.models.graph import CampusGraph
from campus_routing.visualization.directions import generate_route_directions

ASSUMED_WALKING_SPEED_MPS: float = 1.4  # Metres per second (~5.04 km/h standard pedestrian pace)


def calculate_theoretical_walking_time(distance_m: float) -> str:
    """
    Computes theoretical walking time based on a fixed 1.4 m/s pedestrian pace.

    Args:
        distance_m: Physical ground distance in metres.

    Returns:
        Formatted human-readable string (e.g. '45 sec', '2.4 min').
    """
    if distance_m <= 0.0:
        return "0 min"
    seconds = distance_m / ASSUMED_WALKING_SPEED_MPS
    if seconds < 60.0:
        return f"{seconds:.0f} sec"
    minutes = seconds / 60.0
    return f"{minutes:.1f} min"


def render_metrics_card(
    graph: CampusGraph,
    route: RouteResult,
    origin_name: Optional[str] = None,
    destination_name: Optional[str] = None,
) -> None:
    """
    Renders structured route summary metrics and approximate step guidance.

    Args:
        graph: CampusGraph instance containing node metadata and coordinates.
        route: Calculated RouteResult from Dijkstra's algorithm.
        origin_name: Optional display name of origin node.
        destination_name: Optional display name of destination node.
    """
    # 1. Trivial Zero-Hop Case
    if route.is_empty or len(route.nodes) == 1:
        st.info(
            f"ℹ️ **Origin and Destination are identical** ({origin_name or route.nodes[0]}).\n\n"
            "Total distance is **0.0 m**. No pathway traversal required."
        )
        return

    # 2. Main Metrics Summary Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Physical Distance",
            value=f"{route.total_distance_m:.1f} m",
            help="Accumulated physical ground distance along pathway segments in metres.",
        )

    with col2:
        st.metric(
            label="Routing Impedance Cost",
            value=f"{route.total_cost:.1f}",
            help="Algorithmic traversal cost minimized by Dijkstra's shortest-path algorithm.",
        )

    with col3:
        st.metric(
            label="Pathway Segments",
            value=f"{route.hop_count} {'hop' if route.hop_count == 1 else 'hops'}",
            help="Number of consecutive walkway segments connecting landmarks.",
        )

    with col4:
        est_time = calculate_theoretical_walking_time(route.total_distance_m)
        st.metric(
            label="Est. Walking Time *",
            value=est_time,
            help="Theoretical walking duration based strictly on assumed 1.4 m/s pace.",
        )

    st.caption(
        f"* **Theoretical estimate**: Walking time is calculated assuming a constant walking speed of "
        f"{ASSUMED_WALKING_SPEED_MPS} m/s (~5.0 km/h). Travel time has **not** been measured or calibrated on campus."
    )

    # 3. Waypoint Sequence Visual Representation
    waypoint_names = []
    for nid in route.nodes:
        if graph.has_node(nid):
            waypoint_names.append(graph.get_node(nid).name)
        else:
            waypoint_names.append(nid)

    sequence_str = "  ➔  ".join(f"`{name}`" for name in waypoint_names)
    st.markdown(
        f"""
        <div style="background-color: #F8F9FA; border: 1px solid #CFD8DC; border-radius: 6px; padding: 10px 14px; margin: 10px 0 16px 0; font-size: 13px;">
            <b style="color: #0D47A1;">Waypoint Sequence:</b><br>
            <div style="margin-top: 6px; line-height: 1.8;">{sequence_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4. Approximate Step-by-Step Directions (Using existing directions module)
    try:
        directions = generate_route_directions(graph, route)
        with st.expander("🧭 Approximate Step Directions & Headings", expanded=False):
            st.markdown(
                f"""
                <div style="font-size: 12px; color: #D84315; background: #FFF3E0; padding: 8px 12px; border-radius: 4px; margin-bottom: 10px; border-left: 3px solid #EF6C00;">
                    <b>Disclaimer:</b> {directions.disclaimer}
                </div>
                """,
                unsafe_allow_html=True,
            )
            for step in directions.steps:
                access_badge = "♿ Accessible" if step.is_accessible else "⚠️ Has stairs / unpaved"
                st.markdown(
                    f"**Step {step.step_number}:** {step.instruction} "
                    f"`{step.distance_m:.1f} m` — *[{access_badge}]*"
                )
    except Exception:
        # If coordinates are missing or unexpected error occurs, do not crash
        pass
