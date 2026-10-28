"""
Cartographic visualization package for Smart Campus Navigation.

Exposes Folium map building functions, route overlays, visual styling tokens,
and approximate directional guidance generators.
"""

from campus_routing.visualization.directions import (
    DIRECTIONS_DISCLAIMER,
    DirectionStep,
    RouteDirections,
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

__all__ = [
    "create_campus_context_map",
    "create_demonstration_map",
    "export_map_to_html",
    "generate_route_directions",
    "calculate_bearing",
    "DirectionStep",
    "RouteDirections",
    "DIRECTIONS_DISCLAIMER",
    "CATEGORY_COLORS",
    "CATEGORY_ICONS",
    "COLOR_START_MARKER",
    "COLOR_DEST_MARKER",
    "HTML_CAMPUS_CONTEXT_BANNER",
    "HTML_SYNTHETIC_DEMO_BANNER",
    "STYLE_ACTIVE_ROUTE",
    "STYLE_BLOCKED_PATHWAY",
    "STYLE_DEFAULT_PATHWAY",
    "STYLE_DIRECTED_PATHWAY",
    "build_legend_html",
]
