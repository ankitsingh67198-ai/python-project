"""
Dynamic pathway blockage control panel for Smart Campus Navigation.

Allows users to simulate temporary pedestrian pathway obstructions (construction,
maintenance, events) strictly within the in-memory synthetic demonstration environment.
Preserves changes in Streamlit session state without modifying the database or JSON files.
"""

from typing import Dict, List, Optional, Tuple

import streamlit as st

from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph

SESSION_BLOCKED_EDGES_KEY: str = "demo_blocked_edges"


def get_blocked_edges() -> Dict[Tuple[str, str], str]:
    """
    Retrieves the in-memory blockage registry from Streamlit session state.

    Returns:
        Dictionary mapping canonical (source_id, target_id) tuples to blockage reason strings.
    """
    if SESSION_BLOCKED_EDGES_KEY not in st.session_state:
        st.session_state[SESSION_BLOCKED_EDGES_KEY] = {}
    return st.session_state[SESSION_BLOCKED_EDGES_KEY]


def apply_session_blockages_to_graph(graph: CampusGraph) -> None:
    """
    Applies all currently recorded session-state blockages to an in-memory CampusGraph instance.

    Args:
        graph: The target CampusGraph instance to update.
    """
    blocked_dict = get_blocked_edges()
    for (u, v), reason in blocked_dict.items():
        if graph.has_edge(u, v):
            graph.set_edge_blocked(
                source_id=u,
                target_id=v,
                is_blocked=True,
                block_reason=reason,
            )


def render_blockage_panel(graph: CampusGraph) -> None:
    """
    Renders the dynamic pathway obstruction management interface.

    Allows blocking or unblocking synthetic pathways, providing optional reasons,
    and resetting all simulated closures.

    Args:
        graph: The CampusGraph representing the demonstration topology.
    """
    blocked_edges = get_blocked_edges()

    with st.expander("🚧 Pathway Status & Dynamic Blockage Controls (Demonstration Only)", expanded=False):
        st.markdown(
            """
            <div style="font-size: 13px; color: #455A64; margin-bottom: 12px;">
                Simulate real-time walkway closures (e.g. maintenance, event detours, construction)
                to observe dynamic Dijkstra rerouting. Changes affect <b>only</b> this demonstration session.
            </div>
            """,
            unsafe_allow_html=True,
        )

        all_edges = graph.get_edges(include_blocked=True)
        if not all_edges:
            st.info("No pathways found in the demonstration graph.")
            return

        # Build options mapping for selection: canonical key -> readable label
        edge_options: Dict[str, Tuple[str, str]] = {}
        for edge in all_edges:
            u_node = graph.get_node(edge.source_id)
            v_node = graph.get_node(edge.target_id)
            canonical = edge.canonical_endpoints()
            status_tag = "⛔ BLOCKED" if canonical in blocked_edges else "✅ OPEN"
            label = (
                f"[{status_tag}] {u_node.name} ({u_node.id}) ↔ {v_node.name} ({v_node.id}) "
                f"({edge.distance_m:.1f} m, {edge.surface_type})"
            )
            edge_options[label] = canonical

        col1, col2 = st.columns([3, 2])

        with col1:
            selected_label = st.selectbox(
                label="Select Pathway Segment",
                options=list(edge_options.keys()),
                key="blockage_edge_select",
                help="Select a synthetic pathway segment to toggle its traversal availability.",
            )
            selected_canonical = edge_options[selected_label]
            is_currently_blocked = selected_canonical in blocked_edges

        with col2:
            if not is_currently_blocked:
                reason = st.text_input(
                    label="Blockage Reason",
                    value="Pathway resurfacing / maintenance work",
                    key="blockage_reason_input",
                    help="Reason displayed on map tooltips when pathway is obstructed.",
                )
                if st.button("⛔ Block Selected Pathway", key="apply_block_button", use_container_width=True):
                    blocked_edges[selected_canonical] = reason.strip() or "Pathway temporarily closed"
                    st.session_state[SESSION_BLOCKED_EDGES_KEY] = blocked_edges
                    st.rerun()
            else:
                current_reason = blocked_edges[selected_canonical]
                st.markdown(
                    f"""
                    <div style="font-size: 12px; color: #C62828; margin-top: 24px; padding: 6px; background: #FFEBEE; border-radius: 4px;">
                        <b>Current Status:</b> Blocked<br>
                        <b>Reason:</b> {current_reason}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("✅ Reopen Pathway", key="reopen_path_button", use_container_width=True):
                    blocked_edges.pop(selected_canonical, None)
                    st.session_state[SESSION_BLOCKED_EDGES_KEY] = blocked_edges
                    st.rerun()

        # Summary of currently blocked edges and reset control
        if blocked_edges:
            st.markdown("---")
            st.markdown("###### Currently Blocked Segments")
            summary_cols = st.columns([4, 1])
            with summary_cols[0]:
                for (u, v), r in blocked_edges.items():
                    u_name = graph.get_node(u).name if graph.has_node(u) else u
                    v_name = graph.get_node(v).name if graph.has_node(v) else v
                    st.markdown(f"• **{u_name} ({u}) ↔ {v_name} ({v})**: *{r}*")
            with summary_cols[1]:
                if st.button("🔄 Clear All Blockages", key="clear_all_blockages_btn", use_container_width=True):
                    blocked_edges.clear()
                    st.session_state[SESSION_BLOCKED_EDGES_KEY] = blocked_edges
                    st.rerun()
