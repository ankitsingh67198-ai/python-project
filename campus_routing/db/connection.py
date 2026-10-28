"""
SQLite connection manager and transaction context for Smart Campus Navigation.

Ensures foreign key enforcement, WAL mode, pathlib compatibility, and transaction safety.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator, Optional, Union

from campus_routing.config import DEFAULT_DB_PATH
from campus_routing.exceptions import DatabaseError


def get_db_connection(
    db_path: Optional[Union[str, Path]] = None,
    timeout: float = 10.0,
) -> sqlite3.Connection:
    """
    Creates and configures a SQLite connection with foreign keys and row factory enabled.

    Args:
        db_path: Filesystem path to SQLite file or ':memory:'. Defaults to DEFAULT_DB_PATH.
        timeout: SQLite lock timeout in seconds.

    Returns:
        Configured sqlite3.Connection instance.

    Raises:
        DatabaseError: If connection cannot be opened or configured.
    """
    resolved_path: Union[str, Path]
    if db_path is None:
        resolved_path = DEFAULT_DB_PATH
    elif isinstance(db_path, str) and db_path == ":memory:":
        resolved_path = ":memory:"
    else:
        resolved_path = Path(db_path)

    # Ensure parent directory exists for file-based database
    if isinstance(resolved_path, Path):
        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as err:
            raise DatabaseError(f"Failed to create database directory {resolved_path.parent}: {err}") from err

    try:
        conn = sqlite3.connect(
            str(resolved_path),
            timeout=timeout,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row

        # Mandatory relational integrity
        conn.execute("PRAGMA foreign_keys = ON;")

        # Enable Write-Ahead Logging for file-based DBs to support concurrent readers
        if resolved_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")

        return conn
    except sqlite3.Error as err:
        raise DatabaseError(f"Failed to connect to SQLite database at {resolved_path}: {err}") from err


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for atomic SQLite transactions.

    Commits on successful completion; rolls back automatically on exception.

    Args:
        conn: Open sqlite3.Connection.

    Yields:
        The connection within an active transaction.
    """
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db(
    db_path: Optional[Union[str, Path]] = None,
    schema_path: Optional[Union[str, Path]] = None,
) -> sqlite3.Connection:
    """
    Initializes the database schema by executing schema.sql.

    Args:
        db_path: Target database path.
        schema_path: Path to schema.sql. Defaults to campus_routing/db/schema.sql.

    Returns:
        The connection to the initialized database.
    """
    if schema_path is None:
        schema_file = Path(__file__).resolve().parent / "schema.sql"
    else:
        schema_file = Path(schema_path)

    if not schema_file.is_file():
        raise DatabaseError(f"Schema definition file not found at {schema_file}")

    schema_sql = schema_file.read_text(encoding="utf-8")
    conn = get_db_connection(db_path=db_path)

    try:
        with transaction(conn):
            conn.executescript(schema_sql)
        return conn
    except sqlite3.Error as err:
        conn.close()
        raise DatabaseError(f"Failed to initialize database schema: {err}") from err
