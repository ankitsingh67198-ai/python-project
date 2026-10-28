"""
Configuration constants and filesystem paths for Smart Campus Navigation.

All paths are resolved using pathlib.Path to guarantee native Windows and cross-platform compatibility.
"""

from pathlib import Path
from typing import Final, Set

# Root directories
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
DOCS_DIR: Final[Path] = PROJECT_ROOT / "docs"
TESTS_DIR: Final[Path] = PROJECT_ROOT / "tests"

# Persistent database and seed paths
DEFAULT_DB_PATH: Final[Path] = DATA_DIR / "campus.db"
SEED_LANDMARKS_PATH: Final[Path] = DATA_DIR / "seed_landmarks.json"
DEMO_GRAPH_PATH: Final[Path] = DATA_DIR / "demonstration_graph.json"

# Campus Regional Reference Datum (Approximate Campus Centroid, Valavoor)
# Source: Public reference (Wikipedia, OpenStreetMap Way 1077351803)
REFERENCE_LATITUDE: Final[float] = 9.754833
REFERENCE_LONGITUDE: Final[float] = 76.650099
REFERENCE_CAMPUS_NAME: Final[str] = "Indian Institute of Information Technology Kottayam"
REFERENCE_LOCATION: Final[str] = "Valavoor, Pala, Kottayam, Kerala 686635, India"

# Engineering Coarse Sanity Envelope (NOT physical cadastral perimeter)
# Used exclusively for sanity validation against gross coordinates entry errors
MIN_LATITUDE: Final[float] = 9.750000
MAX_LATITUDE: Final[float] = 9.760000
MIN_LONGITUDE: Final[float] = 76.645000
MAX_LONGITUDE: Final[float] = 76.656000

# Permitted domain categories for nodes
VALID_NODE_CATEGORIES: Final[Set[str]] = {
    "academic",
    "administrative",
    "residential",
    "dining",
    "sports",
    "amenity",
    "gate",
    "junction",
    "other",
}

# Permitted pathway surface types
VALID_SURFACE_TYPES: Final[Set[str]] = {
    "paved",
    "concrete",
    "asphalt",
    "stairs",
    "trail",
    "unpaved",
    "unknown",
}

# Data provenance categories
VALID_PROVENANCE_VALUES: Final[Set[str]] = {
    "OFFICIAL_INSTITUTIONAL",
    "EXTERNAL_PUBLIC_GEODATA",
    "SYNTHETIC_DEMO",
    "FIELD_SURVEY_VERIFIED",
}

# Verification statuses
VALID_VERIFICATION_STATUSES: Final[Set[str]] = {
    "UNVERIFIED",
    "OFFICIAL_REFERENCE",
    "FIELD_SURVEYED",
    "SYNTHETIC_DEMO",
}
