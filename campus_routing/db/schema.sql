-- Schema DDL for Smart Campus Navigation System
-- Target: SQLite 3.x with strict foreign key and domain constraint enforcement

PRAGMA foreign_keys = ON;

-- Table: nodes
-- Represents campus landmark destinations, building access portals, and pathway intersections.
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(
        category IN ('academic', 'administrative', 'residential', 'dining', 'sports', 'amenity', 'gate', 'junction', 'other')
    ),
    latitude REAL,
    longitude REAL,
    elevation_m REAL,
    is_landmark INTEGER NOT NULL DEFAULT 1 CHECK(is_landmark IN (0, 1)),
    description TEXT,
    source_provenance TEXT NOT NULL DEFAULT 'OFFICIAL_INSTITUTIONAL' CHECK(
        source_provenance IN ('OFFICIAL_INSTITUTIONAL', 'EXTERNAL_PUBLIC_GEODATA', 'SYNTHETIC_DEMO', 'FIELD_SURVEY_VERIFIED')
    ),
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK(
        verification_status IN ('UNVERIFIED', 'OFFICIAL_REFERENCE', 'FIELD_SURVEYED', 'SYNTHETIC_DEMO')
    ),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Integrity Rule: Coordinates must be either BOTH null (unknown) or BOTH non-null and within the sanity envelope.
    CONSTRAINT chk_node_coordinates CHECK(
        (latitude IS NULL AND longitude IS NULL) OR 
        (latitude IS NOT NULL AND longitude IS NOT NULL AND latitude BETWEEN 9.750000 AND 9.760000 AND longitude BETWEEN 76.645000 AND 76.656000)
    )
);

-- Table: edges
-- Represents physical pedestrian pathways connecting nodes.
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    distance_m REAL NOT NULL CHECK(distance_m > 0.0),
    is_directed INTEGER NOT NULL DEFAULT 0 CHECK(is_directed IN (0, 1)),
    surface_type TEXT DEFAULT 'paved' CHECK(
        surface_type IN ('paved', 'concrete', 'asphalt', 'stairs', 'trail', 'unpaved', 'unknown')
    ),
    is_accessible INTEGER NOT NULL DEFAULT 1 CHECK(is_accessible IN (0, 1)),
    is_blocked INTEGER NOT NULL DEFAULT 0 CHECK(is_blocked IN (0, 1)),
    block_reason TEXT,
    source_provenance TEXT NOT NULL DEFAULT 'SYNTHETIC_DEMO' CHECK(
        source_provenance IN ('OFFICIAL_INSTITUTIONAL', 'EXTERNAL_PUBLIC_GEODATA', 'SYNTHETIC_DEMO', 'FIELD_SURVEY_VERIFIED')
    ),
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK(
        verification_status IN ('UNVERIFIED', 'OFFICIAL_REFERENCE', 'FIELD_SURVEYED', 'SYNTHETIC_DEMO')
    ),
    -- Prevent self-loops
    CONSTRAINT chk_no_self_loop CHECK(source_id <> target_id),
    -- For undirected edges (is_directed=0), enforce canonical order source_id < target_id to eliminate reverse duplicates.
    CONSTRAINT chk_canonical_undirected CHECK(is_directed = 1 OR source_id < target_id),
    -- Enforce pair uniqueness
    CONSTRAINT uq_edge_pair UNIQUE(source_id, target_id)
);

-- Table: campus_metadata
-- Key-value registry for system-wide configuration, survey timestamps, and network status flags.
CREATE TABLE IF NOT EXISTS campus_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_nodes_category ON nodes(category);
CREATE INDEX IF NOT EXISTS idx_nodes_landmark ON nodes(is_landmark);
