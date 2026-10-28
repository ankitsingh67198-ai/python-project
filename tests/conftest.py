"""
Shared Pytest fixtures for Smart Campus Navigation test suite.
"""

import json
from pathlib import Path
import sqlite3
import pytest
from typing import Generator

from campus_routing.db.connection import get_db_connection
from campus_routing.db.repository import CampusRepository


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Provides an isolated temporary SQLite database file path."""
    return tmp_path / "test_campus.db"


@pytest.fixture
def memory_conn() -> Generator[sqlite3.Connection, None, None]:
    """Provides an in-memory SQLite connection configured with foreign keys."""
    conn = get_db_connection(db_path=":memory:")
    yield conn
    conn.close()


@pytest.fixture
def repo_in_memory(memory_conn: sqlite3.Connection) -> CampusRepository:
    """Provides a CampusRepository connected to an initialized in-memory database."""
    repo = CampusRepository(conn=memory_conn)
    repo.init_schema()
    return repo


@pytest.fixture
def repo_temp_file(temp_db_path: Path) -> Generator[CampusRepository, None, None]:
    """Provides a CampusRepository connected to an initialized temporary file database."""
    repo = CampusRepository(db_path=temp_db_path)
    repo.init_schema()
    yield repo
    repo.close()


@pytest.fixture
def sample_landmarks_file(tmp_path: Path) -> Path:
    """Creates a temporary sample landmarks JSON file for seeder testing."""
    file_path = tmp_path / "sample_landmarks.json"
    data = [
        {
            "id": "ACAD_TEST_1",
            "name": "Academic Test Block",
            "category": "academic",
            "latitude": None,
            "longitude": None,
            "elevation_m": None,
            "is_landmark": 1,
            "description": "Test academic block with unknown coordinates.",
            "source_provenance": "OFFICIAL_INSTITUTIONAL",
            "verification_status": "OFFICIAL_REFERENCE"
        },
        {
            "id": "HOSTEL_TEST_1",
            "name": "Hostel Test Block",
            "category": "residential",
            "latitude": None,
            "longitude": None,
            "elevation_m": None,
            "is_landmark": 1,
            "description": "Test hostel block with unknown coordinates.",
            "source_provenance": "OFFICIAL_INSTITUTIONAL",
            "verification_status": "OFFICIAL_REFERENCE"
        }
    ]
    file_path.write_text(json.dumps(data), encoding="utf-8")
    return file_path
