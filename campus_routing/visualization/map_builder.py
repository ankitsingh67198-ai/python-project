"""
Folium-based interactive map builder for Smart Campus Navigation.

Provides modular, type-annotated functions for generating campus cartographic
visualizations in two strictly isolated modes:
1. Campus Context Mode: Shows institutional reference datum with survey notices.
2. Synthetic Demonstration Mode: Shows demonstration topology with active route overlays.

Completely decoupled from routing algorithms and Streamlit presentation logic.
"""

from pathlib import Path
from typing import Dict, Final, List, Optional, Tuple, Union

import folium

from campus_routing.algorithms.dijkstra import RouteResult
from campus_routing.config import (
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
    ValidationError,
)
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node
from campus_routing.visualization.styles import (
    CATEGORY_COLORS,
    CATEGORY_ICONS,
    COLOR_DEST_MARKER,
    COLOR_START_MARKER,
    HTML_CAMPUS_CONTEXT_BANNER,
    HTML_SYNTHETIC_DEMO_BANNER,
    STYLE_ACTIVE_ROUTE,
    STYLE_BLOCKED_PATHWAY,
    STYLE_DEFAULT_PATHWAY,
    STYLE_DIRECTED_PATHWAY,
    build_legend_html,
)


# Mapping from domain category to standard Folium icon colors
FOLIUM_ICON_COLORS: Final[Dict[str, str]] = {
    "academic": "blue",
    "administrative": "purple",
    "residential": "orange",
    "dining": "green",
    "sports": "darkred",
    "amenity": "cadetblue",
    "gate": "black",
    "junction": "gray",
    "other": "lightgray",
}


def create_campus_context_map(
    repo: Optional[CampusRepository] = None,
    width: str = "100%",
    height: str = "600px",
    zoom_start: int = 16,
    tiles: str = "OpenStreetMap",
) -> folium.Map:
    """
    Renders the official Campus Context baseline map.

    Centered on the verified institutional reference coordinate (Valavoor, Pala).
    Prominently displays an institutional reference marker and an advisory banner
    explaining that internal pedestrian pathways and building entrance coordinates
    remain unsurveyed.

    NEVER plots fictitious coordinates, fake building footprints, or fabricated pathways.

    Args:
        repo: Optional CampusRepository to inspect available landmarks count.
        width: CSS width for the map container.
        height: CSS height for the map container.
        zoom_start: Initial zoom level.
        tiles: Folium tile provider.

    Returns:
        Configured folium.Map instance.
    """
    campus_map = folium.Map(
        location=[REFERENCE_LATITUDE, REFERENCE_LONGITUDE],
        zoom_start=zoom_start,
        width=width,
        height=height,
        tiles=tiles,
        control_scale=True,
    )

    # Informational notice about unsurveyed landmarks
    landmark_count_info = ""
    if repo is not None:
        try:
            landmarks = repo.list_nodes()
            unsurveyed_count = sum(1 for n in landmarks if n.get("latitude") is None)
            landmark_count_info = (
                f"<div style='margin-top: 6px; padding: 4px 8px; background: #ECEFF1; border-radius: 4px;'>"
                f"<b>Database Status:</b> {len(landmarks)} landmarks recorded "
                f"({unsurveyed_count} awaiting GPS field survey).</div>"
            )
        except Exception:
            landmark_count_info = ""

    # Campus Centroid Reference Marker (explicitly NOT a building entrance)
    ref_popup_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; min-width: 220px; line-height: 1.4;">
        <div style="font-weight: 700; color: #0D47A1; font-size: 13px; margin-bottom: 4px;">
            {REFERENCE_CAMPUS_NAME}
        </div>
        <div style="color: #455A64; margin-bottom: 4px;">
            <b>Reference Datum:</b> Institutional Centroid
        </div>
        <div><b>Coordinates:</b> {REFERENCE_LATITUDE:.6f}° N, {REFERENCE_LONGITUDE:.6f}° E</div>
        <div><b>Location:</b> {REFERENCE_LOCATION}</div>
        <div style="margin-top: 6px; color: #D84315; font-size: 11px;">
            ⚠️ <i>Reference point for cartographic centering only. Not an entrance or survey monument.</i>
        </div>
        {landmark_count_info}
    </div>
    """

    folium.Marker(
        location=[REFERENCE_LATITUDE, REFERENCE_LONGITUDE],
        popup=folium.Popup(ref_popup_html, max_width=300),
        tooltip="IIIT Kottayam — Institutional Reference Datum",
        icon=folium.Icon(color="blue", icon="university", prefix="fa"),
    ).add_to(campus_map)

    # Attach informational top banner and floating legend
    campus_map.get_root().html.add_child(folium.Element(HTML_CAMPUS_CONTEXT_BANNER))
    campus_map.get_root().html.add_child(folium.Element(build_legend_html(is_demo=False)))

    return campus_map


def create_demonstration_map(
    graph: Optional[CampusGraph] = None,
    route_result: Optional[RouteResult] = None,
    width: str = "100%",
    height: str = "600px",
    zoom_start: int = 17,
    tiles: str = "OpenStreetMap",
) -> folium.Map:
    """
    Renders the Synthetic Demonstration map.

    Visualizes the isolated synthetic graph (nodes and pathways) for testing
    routing algorithms and cartographic display. Prominently labeled with
    unmistakable synthetic demonstration warnings.

    Optionally highlights an active RouteResult with start/destination markers
    and distinct blocked pathway styling.

    Args:
        graph: Optional CampusGraph instance. Defaults to loading demonstration_graph.json.
        route_result: Optional RouteResult to overlay.
        width: CSS width for map container.
        height: CSS height for map container.
        zoom_start: Initial zoom level.
        tiles: Folium tile provider.

    Returns:
        Configured folium.Map instance.

    Raises:
        ValidationError: If route_result is malformed.
        NodeNotFoundError: If route_result references non-existent nodes.
        IncompleteCoordinateError: If route_result contains nodes lacking coordinates.
    """
    if graph is None:
        graph = CampusGraph.from_json(DEMO_GRAPH_PATH)

    # Collect valid coordinate points for viewport bounds calculation
    plotted_coords: List[Tuple[float, float]] = []

    # Calculate initial center point
    nodes = graph.get_nodes()
    valid_coords = [(n.latitude, n.longitude) for n in nodes if n.has_coordinates]
    if valid_coords:
        center_lat = sum(c[0] for c in valid_coords) / len(valid_coords)  # type: ignore[misc]
        center_lon = sum(c[1] for c in valid_coords) / len(valid_coords)  # type: ignore[misc]
    else:
        center_lat, center_lon = REFERENCE_LATITUDE, REFERENCE_LONGITUDE

    demo_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        width=width,
        height=height,
        tiles=tiles,
        control_scale=True,
    )

    # 1. Render all pathway edges
    for edge in graph.get_edges(include_blocked=True):
        u = graph.get_node(edge.source_id)
        v = graph.get_node(edge.target_id)
        if not (u.has_coordinates and v.has_coordinates):
            continue

        assert u.latitude is not None and u.longitude is not None
        assert v.latitude is not None and v.longitude is not None
        endpoints = [[u.latitude, u.longitude], [v.latitude, v.longitude]]

        if edge.is_blocked:
            block_popup = (
                f"<div style='font-family: sans-serif; font-size: 12px; color: #C62828;'>"
                f"<b>⛔ BLOCKED PATHWAY (SYNTHETIC)</b><br>"
                f"<b>Between:</b> {u.name} — {v.name}<br>"
                f"<b>Reason:</b> {edge.block_reason or 'Pathway temporarily obstructed'}<br>"
                f"<b>Distance:</b> {edge.distance_m:.1f} m"
                f"</div>"
            )
            folium.PolyLine(
                locations=endpoints,
                color=STYLE_BLOCKED_PATHWAY["color"],
                weight=STYLE_BLOCKED_PATHWAY["weight"],
                opacity=STYLE_BLOCKED_PATHWAY["opacity"],
                dash_array=STYLE_BLOCKED_PATHWAY["dash_array"],
                tooltip=f"⛔ Blocked Pathway: {u.id} — {v.id}",
                popup=folium.Popup(block_popup, max_width=250),
            ).add_to(demo_map)
        elif edge.is_directed:
            dir_popup = (
                f"<div style='font-family: sans-serif; font-size: 12px;'>"
                f"<b>➡️ DIRECTED PATHWAY (SYNTHETIC)</b><br>"
                f"<b>Direction:</b> {u.name} → {v.name}<br>"
                f"<b>Distance:</b> {edge.distance_m:.1f} m<br>"
                f"<b>Surface:</b> {edge.surface_type}<br>"
                f"<b>Accessible:</b> {'Yes' if edge.is_accessible else 'No'}"
                f"</div>"
            )
            folium.PolyLine(
                locations=endpoints,
                color=STYLE_DIRECTED_PATHWAY["color"],
                weight=STYLE_DIRECTED_PATHWAY["weight"],
                opacity=STYLE_DIRECTED_PATHWAY["opacity"],
                dash_array=STYLE_DIRECTED_PATHWAY["dash_array"],
                tooltip=f"➡️ One-way: {u.name} → {v.name}",
                popup=folium.Popup(dir_popup, max_width=250),
            ).add_to(demo_map)
        else:
            path_popup = (
                f"<div style='font-family: sans-serif; font-size: 12px;'>"
                f"<b>PATHWAY SEGMENT (SYNTHETIC)</b><br>"
                f"<b>Between:</b> {u.name} — {v.name}<br>"
                f"<b>Distance:</b> {edge.distance_m:.1f} m<br>"
                f"<b>Surface:</b> {edge.surface_type}<br>"
                f"<b>Accessible:</b> {'Yes' if edge.is_accessible else 'No'}"
                f"</div>"
            )
            folium.PolyLine(
                locations=endpoints,
                color=STYLE_DEFAULT_PATHWAY["color"],
                weight=STYLE_DEFAULT_PATHWAY["weight"],
                opacity=STYLE_DEFAULT_PATHWAY["opacity"],
                tooltip=f"Pathway: {u.name} — {v.name} ({edge.distance_m:.1f} m)",
                popup=folium.Popup(path_popup, max_width=250),
            ).add_to(demo_map)

    # 2. Render all nodes / landmarks
    for node in nodes:
        if not node.has_coordinates:
            continue

        assert node.latitude is not None and node.longitude is not None
        loc = (node.latitude, node.longitude)
        plotted_coords.append(loc)

        cat = node.category
        color = FOLIUM_ICON_COLORS.get(cat, "gray")
        icon_name = CATEGORY_ICONS.get(cat, "map-marker")
        hex_color = CATEGORY_COLORS.get(cat, "#616161")

        popup_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; min-width: 200px; line-height: 1.4;">
            <div style="font-weight: 700; color: {hex_color}; font-size: 13px; margin-bottom: 4px;">
                {node.name}
            </div>
            <div><b>ID:</b> <code>{node.id}</code></div>
            <div><b>Category:</b> {cat.title()}</div>
            <div><b>Elevation:</b> {node.elevation_m or 'N/A'} m</div>
            <div><b>Provenance:</b> <span style="font-size: 11px; background: #FFEBEE; padding: 1px 4px; border-radius: 3px; color: #B71C1C;">{node.source_provenance}</span></div>
            <div style="margin-top: 4px; font-style: italic; color: #555;">{node.description or ''}</div>
        </div>
        """

        folium.Marker(
            location=[loc[0], loc[1]],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"[{cat.upper()}] {node.name}",
            icon=folium.Icon(color=color, icon=icon_name, prefix="fa"),
        ).add_to(demo_map)

    # 3. Render RouteResult overlay (if supplied)
    if route_result is not None:
        if not route_result.nodes:
            raise ValidationError("Cannot render route: RouteResult contains an empty node sequence.")

        route_coords: List[List[float]] = []
        for nid in route_result.nodes:
            if not graph.has_node(nid):
                raise NodeNotFoundError(
                    f"Route overlay failure: node '{nid}' does not exist in graph."
                )
            r_node = graph.get_node(nid)
            if not r_node.has_coordinates:
                raise IncompleteCoordinateError(
                    f"Route overlay failure: node '{nid}' ({r_node.name}) lacks spatial coordinates. "
                    "Cannot draw route overlay through missing locations."
                )
            assert r_node.latitude is not None and r_node.longitude is not None
            route_coords.append([r_node.latitude, r_node.longitude])

        # Draw active route polyline
        route_popup_html = (
            f"<div style='font-family: sans-serif; font-size: 12px;'>"
            f"<div style='font-weight: 700; color: #0D47A1; font-size: 13px;'>CALCULATED ROUTE</div>"
            f"<b>Waypoints:</b> {' → '.join(route_result.nodes)}<br>"
            f"<b>Total Distance:</b> {route_result.total_distance_m:.1f} m<br>"
            f"<b>Routing Cost:</b> {route_result.total_cost:.1f}<br>"
            f"<b>Hops:</b> {route_result.hop_count}"
            f"</div>"
        )

        folium.PolyLine(
            locations=route_coords,
            color=STYLE_ACTIVE_ROUTE["color"],
            weight=STYLE_ACTIVE_ROUTE["weight"],
            opacity=STYLE_ACTIVE_ROUTE["opacity"],
            tooltip=f"Active Route: {route_result.total_distance_m:.1f} m ({route_result.hop_count} hops)",
            popup=folium.Popup(route_popup_html, max_width=280),
        ).add_to(demo_map)

        # Start Marker (Green Play Icon)
        start_node = graph.get_node(route_result.nodes[0])
        assert start_node.latitude is not None and start_node.longitude is not None
        folium.Marker(
            location=[start_node.latitude, start_node.longitude],
            popup=folium.Popup(
                f"<div style='font-family: sans-serif; font-size: 12px; color: {COLOR_START_MARKER};'>"
                f"<b>🏁 ROUTE ORIGIN (START)</b><br>{start_node.name} (<code>{start_node.id}</code>)</div>",
                max_width=220,
            ),
            tooltip=f"🏁 START: {start_node.name}",
            icon=folium.Icon(color="green", icon="play", prefix="fa"),
        ).add_to(demo_map)

        # Destination Marker (Red Flag Icon)
        dest_node = graph.get_node(route_result.nodes[-1])
        assert dest_node.latitude is not None and dest_node.longitude is not None
        folium.Marker(
            location=[dest_node.latitude, dest_node.longitude],
            popup=folium.Popup(
                f"<div style='font-family: sans-serif; font-size: 12px; color: {COLOR_DEST_MARKER};'>"
                f"<b>🎯 ROUTE DESTINATION</b><br>{dest_node.name} (<code>{dest_node.id}</code>)</div>",
                max_width=220,
            ),
            tooltip=f"🎯 DESTINATION: {dest_node.name}",
            icon=folium.Icon(color="red", icon="flag", prefix="fa"),
        ).add_to(demo_map)

    # 4. Fit viewport bounds
    if plotted_coords:
        min_lat = min(c[0] for c in plotted_coords)
        max_lat = max(c[0] for c in plotted_coords)
        min_lon = min(c[1] for c in plotted_coords)
        max_lon = max(c[1] for c in plotted_coords)
        demo_map.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]], padding=(25, 25))

    # 5. Add synthetic demo warning banner and legend
    demo_map.get_root().html.add_child(folium.Element(HTML_SYNTHETIC_DEMO_BANNER))
    demo_map.get_root().html.add_child(folium.Element(build_legend_html(is_demo=True)))

    return demo_map


def export_map_to_html(
    folium_map: folium.Map,
    file_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Renders a Folium map to a standalone HTML string and optionally writes it to disk.

    Args:
        folium_map: Folium map instance to render.
        file_path: Optional destination filesystem path.

    Returns:
        Rendered HTML document as a string.
    """
    html_content = folium_map.get_root().render()

    if file_path is not None:
        target = Path(file_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html_content, encoding="utf-8")

    return html_content
