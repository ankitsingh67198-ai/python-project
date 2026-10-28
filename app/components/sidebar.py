"""
Sidebar component for the Smart Campus Navigation Streamlit application.

Manages mode selection (Campus Context vs Synthetic Demonstration), origin and
destination node selection, accessibility filtering preferences, and route-calculation
triggers without coupling to database queries or routing algorithms.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import streamlit as st

from campus_routing.db.repository import CampusRepository
from campus_routing.models.graph import CampusGraph

MODE_CAMPUS_CONTEXT: str = "Campus Context"
MODE_SYNTHETIC_DEMO: str = "Synthetic Demonstration"


@dataclass(frozen=True)
class SidebarState:
    """
    Structured container holding user configuration selections from the sidebar.

    Attributes:
        mode: Active application mode ('Campus Context' or 'Synthetic Demonstration').
        origin_id: Selected start node ID in demonstration mode, or None in context mode.
        destination_id: Selected target node ID in demonstration mode, or None in context mode.
        accessible_only: Whether routing should restrict to step-free accessible pathways.
        calculate_requested: Whether the user triggered a route calculation action.
    """

    mode: str
    origin_id: Optional[str]
    destination_id: Optional[str]
    accessible_only: bool
    calculate_requested: bool


def render_sidebar(
    repo: Optional[CampusRepository] = None,
    demo_graph: Optional[CampusGraph] = None,
) -> SidebarState:
    """
    Renders the navigation sidebar and collects user selections.

    Args:
        repo: CampusRepository instance used for reading campus metadata.
        demo_graph: CampusGraph instance representing the isolated synthetic topology.

    Returns:
        SidebarState instance containing the user's active choices.
    """
    st.sidebar.markdown(
        """
        <div style="text-align: center; padding: 10px 0 16px 0;">
            <div style="font-size: 26px; line-height: 1.2;">🧭</div>
            <div style="font-weight: 700; font-size: 16px; color: #0D47A1; margin-top: 4px;">
                IIIT Kottayam
            </div>
            <div style="font-size: 12px; color: #546E7A;">
                Smart Campus Navigation
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")

    # 1. Mode Selection
    mode = st.sidebar.radio(
        label="Application Mode",
        options=[MODE_CAMPUS_CONTEXT, MODE_SYNTHETIC_DEMO],
        index=0,
        help=(
            "Campus Context shows verified institutional metadata and reference datum. "
            "Synthetic Demonstration allows interactive shortest-path calculation on test topology."
        ),
        key="app_mode_selection",
    )

    # 2. Mode-Specific Controls
    if mode == MODE_CAMPUS_CONTEXT:
        st.sidebar.info(
            "📍 **Campus Context Mode**\n\n"
            "Shows the verified institutional reference datum.\n\n"
            "⚠️ Real campus routing is **disabled** because pedestrian footways and "
            "building entrance coordinates remain unsurveyed."
        )

        landmark_count = 18
        if repo is not None:
            try:
                landmarks = repo.list_nodes()
                landmark_count = len(landmarks)
            except Exception:
                pass

        st.sidebar.markdown(
            f"""
            <div style="background-color: #ECEFF1; border-radius: 6px; padding: 10px; font-size: 12px; margin-top: 10px;">
                <b>Campus Database Status:</b><br>
                • Recorded Landmarks: <b>{landmark_count}</b><br>
                • Verified Footways: <b>0</b><br>
                • Routing Availability: <b style="color: #D84315;">Unsurveyed</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        return SidebarState(
            mode=MODE_CAMPUS_CONTEXT,
            origin_id=None,
            destination_id=None,
            accessible_only=False,
            calculate_requested=False,
        )

    # Synthetic Demonstration Mode Controls
    st.sidebar.markdown(
        """
        <div style="background-color: #FFEBEE; border-left: 4px solid #C62828; padding: 8px 10px; font-size: 11px; color: #B71C1C; margin-bottom: 12px; border-radius: 2px;">
            <b>SYNTHETIC DEMO MODE</b><br>
            Using isolated 6-node demonstration topology. Distances are synthetic test values.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if demo_graph is None:
        st.sidebar.error("Demonstration graph data is unavailable.")
        return SidebarState(
            mode=MODE_SYNTHETIC_DEMO,
            origin_id=None,
            destination_id=None,
            accessible_only=False,
            calculate_requested=False,
        )

    demo_nodes = demo_graph.get_nodes()
    # Format node labels: "Demo Campus Main Gate (DEMO_GATE)"
    node_labels: Dict[str, str] = {
        f"{n.name} ({n.id})": n.id for n in sorted(demo_nodes, key=lambda x: x.name)
    }
    label_list = list(node_labels.keys())

    # Default to Main Gate -> Student Hostel if present
    default_origin_idx = 0
    default_dest_idx = min(1, len(label_list) - 1)
    for i, label in enumerate(label_list):
        if "DEMO_GATE" in label:
            default_origin_idx = i
        elif "DEMO_HOSTEL" in label:
            default_dest_idx = i

    origin_label = st.sidebar.selectbox(
        label="Origin Location",
        options=label_list,
        index=default_origin_idx,
        key="demo_origin_select",
        help="Starting landmark for demonstration pathfinding.",
    )
    origin_id = node_labels[origin_label]

    destination_label = st.sidebar.selectbox(
        label="Destination Location",
        options=label_list,
        index=default_dest_idx,
        key="demo_destination_select",
        help="Target landmark for demonstration pathfinding.",
    )
    destination_id = node_labels[destination_label]

    if origin_id == destination_id:
        st.sidebar.warning("ℹ️ Origin and destination are identical. Distance is 0.0 m.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("##### Routing Preferences")

    accessible_only = st.sidebar.checkbox(
        label="♿ Require step-free pathway",
        value=False,
        key="demo_accessible_only",
        help=(
            "Excludes pathways marked as having stairs or steep trails. "
            "Note: Genuine campus accessibility survey is pending."
        ),
    )

    calculate_btn = st.sidebar.button(
        label="Calculate Shortest Route",
        type="primary",
        use_container_width=True,
        key="calculate_route_button",
    )

    return SidebarState(
        mode=MODE_SYNTHETIC_DEMO,
        origin_id=origin_id,
        destination_id=destination_id,
        accessible_only=accessible_only,
        calculate_requested=calculate_btn,
    )
