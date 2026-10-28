"""
Database package for Smart Campus Navigation.

Provides SQLite connection management, repository operations, schema definitions,
and idempotent database seeding.
"""

from campus_routing.db.connection import (
    get_db_connection,
    init_db,
    transaction,
)
from campus_routing.db.repository import CampusRepository

__all__ = [
    "get_db_connection",
    "init_db",
    "transaction",
    "CampusRepository",
]

