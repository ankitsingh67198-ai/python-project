"""
Repository layer for campus nodes, pathways, and metadata.

Encapsulates all SQLite database operations, enforcing spatial domain rules,
foreign key consistency, and data provenance.
"""

from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Union

from campus_routing.config import (
    DEFAULT_DB_PATH,
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    VALID_NODE_CATEGORIES,
    VALID_PROVENANCE_VALUES,
    VALID_SURFACE_TYPES,
    VALID_VERIFICATION_STATUSES,
)
from campus_routing.db.connection import get_db_connection, transaction
from campus_routing.exceptions import (
    CoordinateOutOfBoundsError,
    DatabaseError,
    DuplicateEdgeError,
    EdgeNotFoundError,
    IncompleteCoordinateError,
    InvalidEdgeError,
    InvalidNodeCategoryError,
    NodeNotFoundError,
    ValidationError,
)


class CampusRepository:
    """
    Data access repository for SQLite-backed campus navigation records.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """
        Initializes repository using an existing connection or target path.

        Args:
            db_path: Path to SQLite file or ':memory:'.
            conn: Optional existing sqlite3.Connection.
        """
        self._db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        self._conn = conn

    def get_connection(self) -> sqlite3.Connection:
        """Returns the active or newly opened SQLite connection."""
        if self._conn is None:
            self._conn = get_db_connection(self._db_path)
        return self._conn

    def close(self) -> None:
        """Closes the active database connection if managed by this repository."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "CampusRepository":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def init_schema(self, schema_path: Optional[Union[str, Path]] = None) -> None:
        """
        Applies DDL statements from schema.sql to initialize all tables and indexes.
        """
        if schema_path is None:
            schema_file = Path(__file__).resolve().parent / "schema.sql"
        else:
            schema_file = Path(schema_path)

        if not schema_file.is_file():
            raise DatabaseError(f"Schema file not found at {schema_file}")

        ddl = schema_file.read_text(encoding="utf-8")
        conn = self.get_connection()
        try:
            with transaction(conn):
                conn.executescript(ddl)
        except sqlite3.Error as err:
            raise DatabaseError(f"Schema initialization failed: {err}") from err

    # --------------------------------------------------------------------------
    # Node Management
    # --------------------------------------------------------------------------

    def validate_node_data(
        self,
        category: str,
        latitude: Optional[float],
        longitude: Optional[float],
        source_provenance: str,
        verification_status: str,
    ) -> None:
        """Validates node attributes against domain rules before persistence."""
        if category not in VALID_NODE_CATEGORIES:
            raise InvalidNodeCategoryError(
                f"Invalid category '{category}'. Must be one of: {sorted(VALID_NODE_CATEGORIES)}"
            )

        # Coordinate completeness check
        if (latitude is None and longitude is not None) or (latitude is not None and longitude is None):
            raise IncompleteCoordinateError(
                f"Incomplete coordinates: latitude={latitude}, longitude={longitude}. Both must be provided or both null."
            )

        # Bounding envelope check (when coordinates are supplied)
        if latitude is not None and longitude is not None:
            if not (MIN_LATITUDE <= latitude <= MAX_LATITUDE):
                raise CoordinateOutOfBoundsError(
                    f"Latitude {latitude} outside coarse sanity envelope [{MIN_LATITUDE}, {MAX_LATITUDE}]"
                )
            if not (MIN_LONGITUDE <= longitude <= MAX_LONGITUDE):
                raise CoordinateOutOfBoundsError(
                    f"Longitude {longitude} outside coarse sanity envelope [{MIN_LONGITUDE}, {MAX_LONGITUDE}]"
                )

        if source_provenance not in VALID_PROVENANCE_VALUES:
            raise ValidationError(
                f"Invalid source_provenance '{source_provenance}'. Must be one of: {sorted(VALID_PROVENANCE_VALUES)}"
            )

        if verification_status not in VALID_VERIFICATION_STATUSES:
            raise ValidationError(
                f"Invalid verification_status '{verification_status}'. Must be one of: {sorted(VALID_VERIFICATION_STATUSES)}"
            )

    def upsert_node(
        self,
        node_id: str,
        name: str,
        category: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        elevation_m: Optional[float] = None,
        is_landmark: int = 1,
        description: Optional[str] = None,
        source_provenance: str = "OFFICIAL_INSTITUTIONAL",
        verification_status: str = "UNVERIFIED",
        overwrite_existing: bool = True,
    ) -> Dict[str, Any]:
        """
        Inserts or updates a campus node with spatial and provenance validation.
        """
        self.validate_node_data(
            category=category,
            latitude=latitude,
            longitude=longitude,
            source_provenance=source_provenance,
            verification_status=verification_status,
        )

        conn = self.get_connection()
        try:
            with transaction(conn):
                if overwrite_existing:
                    sql = """
                    INSERT INTO nodes (
                        id, name, category, latitude, longitude, elevation_m,
                        is_landmark, description, source_provenance, verification_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        category = excluded.category,
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        elevation_m = excluded.elevation_m,
                        is_landmark = excluded.is_landmark,
                        description = excluded.description,
                        source_provenance = excluded.source_provenance,
                        verification_status = excluded.verification_status;
                    """
                else:
                    sql = """
                    INSERT OR IGNORE INTO nodes (
                        id, name, category, latitude, longitude, elevation_m,
                        is_landmark, description, source_provenance, verification_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """

                conn.execute(
                    sql,
                    (
                        node_id,
                        name,
                        category,
                        latitude,
                        longitude,
                        elevation_m,
                        int(is_landmark),
                        description,
                        source_provenance,
                        verification_status,
                    ),
                )
            node = self.get_node(node_id)
            if node is None:
                raise DatabaseError(f"Failed to retrieve node '{node_id}' after upsert.")
            return node
        except sqlite3.IntegrityError as err:
            raise ValidationError(f"Database integrity violation for node '{node_id}': {err}") from err
        except sqlite3.Error as err:
            raise DatabaseError(f"Database error during upsert of node '{node_id}': {err}") from err

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single node by its ID."""
        conn = self.get_connection()
        cursor = conn.execute("SELECT * FROM nodes WHERE id = ?;", (node_id,))
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    def list_nodes(
        self,
        landmark_only: bool = False,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists nodes filtered by landmark flag or category."""
        conn = self.get_connection()
        query = "SELECT * FROM nodes WHERE 1=1"
        params: List[Any] = []

        if landmark_only:
            query += " AND is_landmark = 1"
        if category is not None:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY category, name;"
        cursor = conn.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    # --------------------------------------------------------------------------
    # Edge Management
    # --------------------------------------------------------------------------

    def validate_edge_data(
        self,
        source_id: str,
        target_id: str,
        distance_m: float,
        is_directed: int,
        surface_type: str,
        source_provenance: str,
        verification_status: str,
    ) -> None:
        """Validates edge attributes before database insertion."""
        if source_id == target_id:
            raise InvalidEdgeError(f"Self-loop edge rejected: source and target are both '{source_id}'")

        if distance_m <= 0.0:
            raise InvalidEdgeError(f"Pathway distance must be strictly positive (> 0.0). Received: {distance_m}")

        if surface_type not in VALID_SURFACE_TYPES:
            raise ValidationError(
                f"Invalid surface_type '{surface_type}'. Must be one of: {sorted(VALID_SURFACE_TYPES)}"
            )

        if source_provenance not in VALID_PROVENANCE_VALUES:
            raise ValidationError(
                f"Invalid source_provenance '{source_provenance}'. Must be one of: {sorted(VALID_PROVENANCE_VALUES)}"
            )

        if verification_status not in VALID_VERIFICATION_STATUSES:
            raise ValidationError(
                f"Invalid verification_status '{verification_status}'. Must be one of: {sorted(VALID_VERIFICATION_STATUSES)}"
            )

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        distance_m: float,
        is_directed: int = 0,
        surface_type: str = "paved",
        is_accessible: int = 1,
        is_blocked: int = 0,
        block_reason: Optional[str] = None,
        source_provenance: str = "SYNTHETIC_DEMO",
        verification_status: str = "UNVERIFIED",
        auto_canonicalize: bool = True,
    ) -> int:
        """
        Inserts a new pathway segment connecting source_id and target_id.

        For undirected pathways (is_directed=0), if auto_canonicalize=True,
        source_id and target_id are ordered canonically (min, max).
        """
        # Auto-canonicalize undirected edges if requested
        if is_directed == 0 and auto_canonicalize and source_id > target_id:
            source_id, target_id = target_id, source_id

        self.validate_edge_data(
            source_id=source_id,
            target_id=target_id,
            distance_m=distance_m,
            is_directed=is_directed,
            surface_type=surface_type,
            source_provenance=source_provenance,
            verification_status=verification_status,
        )

        conn = self.get_connection()
        try:
            with transaction(conn):
                cursor = conn.execute(
                    """
                    INSERT INTO edges (
                        source_id, target_id, distance_m, is_directed, surface_type,
                        is_accessible, is_blocked, block_reason, source_provenance, verification_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        source_id,
                        target_id,
                        distance_m,
                        int(is_directed),
                        surface_type,
                        int(is_accessible),
                        int(is_blocked),
                        block_reason,
                        source_provenance,
                        verification_status,
                    ),
                )
                return int(cursor.lastrowid)
        except sqlite3.IntegrityError as err:
            err_msg = str(err).lower()
            if "foreign key" in err_msg:
                raise NodeNotFoundError(
                    f"Foreign key constraint failed for pathway '{source_id}' -> '{target_id}': one or both nodes do not exist."
                ) from err
            if "unique" in err_msg:
                raise DuplicateEdgeError(
                    f"Pathway between '{source_id}' and '{target_id}' already exists."
                ) from err
            if "chk_canonical_undirected" in err_msg or "canonical" in err_msg:
                raise InvalidEdgeError(
                    f"Canonical ordering violation: for undirected edges, source_id must be < target_id ('{source_id}' > '{target_id}')"
                ) from err
            if "chk_no_self_loop" in err_msg:
                raise InvalidEdgeError("Self-loops are not permitted in pathways.") from err
            raise ValidationError(f"Integrity error inserting edge ({source_id}, {target_id}): {err}") from err
        except sqlite3.Error as err:
            raise DatabaseError(f"Database error inserting edge ({source_id}, {target_id}): {err}") from err

    def get_edge(self, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a pathway connecting source_id and target_id.
        If the pathway is undirected, searches in both forward and reverse directions.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            """
            SELECT * FROM edges
            WHERE (source_id = ? AND target_id = ?)
               OR (is_directed = 0 AND source_id = ? AND target_id = ?);
            """,
            (source_id, target_id, target_id, source_id),
        )
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    def list_edges(self, include_blocked: bool = True) -> List[Dict[str, Any]]:
        """Lists all pathway segments in the database."""
        conn = self.get_connection()
        if include_blocked:
            cursor = conn.execute("SELECT * FROM edges ORDER BY source_id, target_id;")
        else:
            cursor = conn.execute("SELECT * FROM edges WHERE is_blocked = 0 ORDER BY source_id, target_id;")
        return [dict(row) for row in cursor.fetchall()]

    def set_edge_blocked(
        self,
        source_id: str,
        target_id: str,
        is_blocked: bool,
        block_reason: Optional[str] = None,
    ) -> None:
        """
        Marks an existing edge as blocked or unblocked. Preserves edge records.
        """
        edge = self.get_edge(source_id, target_id)
        if edge is None:
            raise EdgeNotFoundError(f"Pathway between '{source_id}' and '{target_id}' does not exist.")

        canonical_source = edge["source_id"]
        canonical_target = edge["target_id"]

        conn = self.get_connection()
        try:
            with transaction(conn):
                conn.execute(
                    """
                    UPDATE edges
                    SET is_blocked = ?, block_reason = ?
                    WHERE source_id = ? AND target_id = ?;
                    """,
                    (int(is_blocked), block_reason if is_blocked else None, canonical_source, canonical_target),
                )
        except sqlite3.Error as err:
            raise DatabaseError(f"Failed to update blockage status for edge ({source_id}, {target_id}): {err}") from err

    # --------------------------------------------------------------------------
    # Campus Metadata Management
    # --------------------------------------------------------------------------

    def get_metadata(self, key: str) -> Optional[str]:
        """Retrieves a metadata value by key."""
        conn = self.get_connection()
        cursor = conn.execute("SELECT value FROM campus_metadata WHERE key = ?;", (key,))
        row = cursor.fetchone()
        return str(row["value"]) if row is not None else None

    def set_metadata(self, key: str, value: str) -> None:
        """Sets or updates a campus metadata key-value entry."""
        conn = self.get_connection()
        try:
            with transaction(conn):
                conn.execute(
                    """
                    INSERT INTO campus_metadata (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (key, str(value)),
                )
        except sqlite3.Error as err:
            raise DatabaseError(f"Failed to set metadata '{key}': {err}") from err

    def get_all_metadata(self) -> Dict[str, str]:
        """Returns all metadata key-value pairs as a dictionary."""
        conn = self.get_connection()
        cursor = conn.execute("SELECT key, value FROM campus_metadata ORDER BY key;")
        return {row["key"]: row["value"] for row in cursor.fetchall()}

    def has_verified_routing_network(self) -> bool:
        """Checks if verified real-world routing network data is marked available."""
        val = self.get_metadata("has_verified_routing_network")
        if val is None:
            return False
        return val.strip().lower() in {"true", "1", "yes"}
