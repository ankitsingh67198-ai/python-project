"""
Visual styling and cartographic design tokens for Smart Campus Navigation.

Defines curated color palettes, marker icons, polyline parameters,
informative HTML disclaimers, and legend components.
"""

from typing import Any, Dict, Final

# -----------------------------------------------------------------------------
# Color Palette (Curated accessible colors)
# -----------------------------------------------------------------------------

CATEGORY_COLORS: Final[Dict[str, str]] = {
    "academic": "#1976D2",       # Blue
    "administrative": "#7B1FA2", # Purple
    "residential": "#E65100",    # Orange / Amber
    "dining": "#2E7D32",         # Green
    "sports": "#C2185B",         # Deep Rose / Red
    "amenity": "#00897B",        # Teal
    "gate": "#B71C1C",           # Dark Crimson
    "junction": "#546E7A",       # Slate Blue-Gray
    "other": "#616161",          # Neutral Gray
}

CATEGORY_ICONS: Final[Dict[str, str]] = {
    "academic": "graduation-cap",
    "administrative": "university",
    "residential": "home",
    "dining": "cutlery",
    "sports": "futbol-o",
    "amenity": "info-circle",
    "gate": "shield",
    "junction": "circle",
    "other": "map-marker",
}

# -----------------------------------------------------------------------------
# Pathway & Route Polyline Styling
# -----------------------------------------------------------------------------

STYLE_DEFAULT_PATHWAY: Final[Dict[str, Any]] = {
    "color": "#607D8B",          # Slate gray
    "weight": 4,
    "opacity": 0.7,
}

STYLE_DIRECTED_PATHWAY: Final[Dict[str, Any]] = {
    "color": "#455A64",          # Darker slate
    "weight": 4,
    "opacity": 0.75,
    "dash_array": "4, 6",
}

STYLE_BLOCKED_PATHWAY: Final[Dict[str, Any]] = {
    "color": "#D32F2F",          # Vivid Red
    "weight": 5,
    "opacity": 0.9,
    "dash_array": "8, 8",
}

STYLE_ACTIVE_ROUTE: Final[Dict[str, Any]] = {
    "color": "#0D47A1",          # Vibrant deep royal blue
    "weight": 6,
    "opacity": 0.9,
}

# Route Endpoint Marker Colors
COLOR_START_MARKER: Final[str] = "#2E7D32"   # Forest Green
COLOR_DEST_MARKER: Final[str] = "#C62828"    # Crimson Red

# -----------------------------------------------------------------------------
# Informative Banner HTML Components
# -----------------------------------------------------------------------------

HTML_CAMPUS_CONTEXT_BANNER: Final[str] = """
<div id="campus-context-banner" style="
    position: fixed;
    top: 15px;
    left: 60px;
    right: 20px;
    z-index: 1000;
    background: #FFF8E1;
    color: #5D4037;
    border: 2px solid #FFA000;
    border-radius: 6px;
    padding: 12px 16px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
    line-height: 1.45;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
">
    <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px; color: #E65100;">
        ℹ️ IIIT Kottayam — Campus Context Mode (Planning Baseline)
    </div>
    <div>
        <strong>Verified Centroid Datum:</strong> 9°45′17″ N, 76°39′00″ E (Valavoor, Pala).
        <br>
        <strong>Notice:</strong> Verified internal pedestrian footways and micro-level building entrance coordinates
        are currently <em>unsurveyed</em>. To ensure scientific integrity, no pathways or building pins are fabricated on this map.
    </div>
</div>
"""

HTML_SYNTHETIC_DEMO_BANNER: Final[str] = """
<div id="synthetic-demo-banner" style="
    position: fixed;
    top: 15px;
    left: 60px;
    right: 20px;
    z-index: 1000;
    background: #FFEBEE;
    color: #B71C1C;
    border: 2px solid #D32F2F;
    border-radius: 6px;
    padding: 12px 16px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
    line-height: 1.45;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
">
    <div style="font-weight: 800; font-size: 14px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">
        ⚠️ SYNTHETIC DEMONSTRATION — NOT REAL CAMPUS NAVIGATION
    </div>
    <div>
        This map displays an isolated synthetic graph (<code>demonstration_graph.json</code>) designed exclusively
        for algorithm testing and cartographic verification. These pathways and nodes do <strong>not</strong> represent
        actual IIIT Kottayam walking routes.
    </div>
</div>
"""


def build_legend_html(is_demo: bool = False) -> str:
    """
    Constructs a clean HTML floating legend widget for the map.

    Args:
        is_demo: If True, includes route and blocked pathway indicators.

    Returns:
        HTML string containing styled floating legend.
    """
    items_html = ""
    for cat, color in CATEGORY_COLORS.items():
        if cat in ("junction", "other") and not is_demo:
            continue
        label = cat.replace("_", " ").title()
        items_html += f"""
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: {color}; margin-right: 8px;"></span>
            <span style="font-size: 11px; color: #37474F;">{label}</span>
        </div>
        """

    pathway_legend = ""
    if is_demo:
        pathway_legend = """
        <div style="border-top: 1px solid #CFD8DC; margin-top: 6px; padding-top: 6px;">
            <div style="font-weight: 600; font-size: 11px; color: #263238; margin-bottom: 4px;">Pathways</div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 4px; background: #0D47A1; margin-right: 8px;"></span>
                <span style="font-size: 11px; color: #37474F;">Calculated Route</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 3px; background: #607D8B; margin-right: 8px;"></span>
                <span style="font-size: 11px; color: #37474F;">Walkable Pathway</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <span style="display: inline-block; width: 16px; height: 4px; border-top: 3px dashed #D32F2F; margin-right: 8px;"></span>
                <span style="font-size: 11px; color: #37474F;">Blocked Pathway</span>
            </div>
            <div style="display: flex; align-items: center; margin-top: 4px;">
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #2E7D32; margin-right: 8px;"></span>
                <span style="font-size: 11px; color: #37474F;">Start Marker</span>
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #C62828; margin-left: 8px; margin-right: 8px;"></span>
                <span style="font-size: 11px; color: #37474F;">Destination</span>
            </div>
        </div>
        """

    return f"""
    <div id="map-floating-legend" style="
        position: fixed;
        bottom: 25px;
        right: 25px;
        z-index: 1000;
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid #B0BEC5;
        border-radius: 6px;
        padding: 10px 14px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        box-shadow: 0 2px 8px rgba(0,0,0,0.18);
        min-width: 150px;
    ">
        <div style="font-weight: 700; font-size: 12px; color: #263238; margin-bottom: 6px; border-bottom: 1px solid #ECEFF1; padding-bottom: 4px;">
            { 'Demo Legend' if is_demo else 'Landmark Categories' }
        </div>
        {items_html}
        {pathway_legend}
    </div>
    """
