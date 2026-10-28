"""
Idempotent database seeding module for Smart Campus Navigation.

Seeds verified IIIT Kottayam landmark metadata and system configuration.
Guarantees zero fabrication: coordinates and pathways remain unverified until surveyed.
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Union

from campus_routing.config import (
    DEFAULT_DB_PATH,
    DEMO_GRAPH_PATH,
    REFERENCE_CAMPUS_NAME,
    REFERENCE_LATITUDE,
    REFERENCE_LOCATION,
    REFERENCE_LONGITUDE,
    SEED_LANDMARKS_PATH,
)
from campus_routing.db.repository import CampusRepository
from campus_routing.exceptions import DatabaseError


def seed_database(
    db_path: Optional[Union[str, Path]] = None,
    landmarks_path: Optional[Union[str, Path]] = None,
    demo_path: Optional[Union[str, Path]] = None,
    seed_demo: bool = False,
    overwrite_existing: bool = False,
) -> Dict[str, int]:
    """
    Idempotently initializes and seeds the SQLite database.

    Args:
        db_path: Target SQLite database path. Defaults to DEFAULT_DB_PATH.
        landmarks_path: Path to seed_landmarks.json.
        demo_path: Path to demonstration_graph.json (used only if seed_demo=True).
        seed_demo: If True, also seeds synthetic demonstration nodes/edges.
        overwrite_existing: If True, overwrites existing records; if False, preserves user changes.

    Returns:
        Summary dict containing counts of inserted/updated records.
    """
    target_landmarks = Path(landmarks_path) if landmarks_path else SEED_LANDMARKS_PATH
    with CampusRepository(db_path=db_path) as repo:
        # 1. Initialize schema
        repo.init_schema()

        # 2. Seed campus metadata registry
        repo.set_metadata("campus_name", REFERENCE_CAMPUS_NAME)
        repo.set_metadata("campus_location", REFERENCE_LOCATION)
        repo.set_metadata("reference_latitude", str(REFERENCE_LATITUDE))
        repo.set_metadata("reference_longitude", str(REFERENCE_LONGITUDE))
        repo.set_metadata("schema_version", "1.0.0")

        # Routing network availability flag
        # Verified walking network is currently unavailable (data gap pending on-site survey)
        if not repo.get_metadata("has_verified_routing_network"):
            repo.set_metadata("has_verified_routing_network", "false")

        # 3. Seed verified campus landmark catalog
        if not target_landmarks.is_file():
            raise DatabaseError(f"Landmark seed file not found at: {target_landmarks}")

        landmarks_data: List[Dict[str, Any]] = json.loads(target_landmarks.read_text(encoding="utf-8"))
        nodes_seeded = 0

        for item in landmarks_data:
            repo.upsert_node(
                node_id=item["id"],
                name=item["name"],
                category=item["category"],
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                elevation_m=item.get("elevation_m"),
                is_landmark=item.get("is_landmark", 1),
                description=item.get("description"),
                source_provenance=item.get("source_provenance", "OFFICIAL_INSTITUTIONAL"),
                verification_status=item.get("verification_status", "OFFICIAL_REFERENCE"),
                overwrite_existing=overwrite_existing,
            )
            nodes_seeded += 1

        edges_seeded = 0

        # 4. Optionally seed demonstration topology (kept explicitly isolated)
        if seed_demo:
            target_demo = Path(demo_path) if demo_path else DEMO_GRAPH_PATH
            if not target_demo.is_file():
                raise DatabaseError(f"Demonstration graph file not found at: {target_demo}")

            demo_data = json.loads(target_demo.read_text(encoding="utf-8"))
            for d_node in demo_data.get("nodes", []):
                repo.upsert_node(
                    node_id=d_node["id"],
                    name=d_node["name"],
                    category=d_node["category"],
                    latitude=d_node.get("latitude"),
                    longitude=d_node.get("longitude"),
                    elevation_m=d_node.get("elevation_m"),
                    is_landmark=d_node.get("is_landmark", 1),
                    description=d_node.get("description"),
                    source_provenance=d_node.get("source_provenance", "SYNTHETIC_DEMO"),
                    verification_status=d_node.get("verification_status", "SYNTHETIC_DEMO"),
                    overwrite_existing=overwrite_existing,
                )
                nodes_seeded += 1

            for d_edge in demo_data.get("edges", []):
                existing = repo.get_edge(d_edge["source_id"], d_edge["target_id"])
                if existing is None or overwrite_existing:
                    repo.add_edge(
                        source_id=d_edge["source_id"],
                        target_id=d_edge["target_id"],
                        distance_m=float(d_edge["distance_m"]),
                        is_directed=int(d_edge.get("is_directed", 0)),
                        surface_type=d_edge.get("surface_type", "paved"),
                        is_accessible=int(d_edge.get("is_accessible", 1)),
                        is_blocked=int(d_edge.get("is_blocked", 0)),
                        block_reason=d_edge.get("block_reason"),
                        source_provenance=d_edge.get("source_provenance", "SYNTHETIC_DEMO"),
                        verification_status=d_edge.get("verification_status", "SYNTHETIC_DEMO"),
                        auto_canonicalize=True,
                    )
                    edges_seeded += 1

        return {
            "nodes_seeded": nodes_seeded,
            "edges_seeded": edges_seeded,
        }



if __name__ == "__main__":
    include_demo = "--demo" in sys.argv
    print(f"Initializing campus database at {DEFAULT_DB_PATH}...")
    result = seed_database(seed_demo=include_demo)
    print(f"Successfully seeded database:")
    print(f" - Verified landmarks seeded: {result['nodes_seeded']}")
    print(f" - Pathways seeded: {result['edges_seeded']}")
    print(f" - Demonstration network included: {include_demo}")
