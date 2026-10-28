"""
Domain models for Smart Campus Navigation.

Exports:
    Node: Campus landmark or pathway junction entity.
    Edge: Pathway segment entity with distance and routing cost separation.
    CampusGraph: In-memory adjacency representation supporting routing and filtering.
"""

from campus_routing.models.edge import Edge
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node

__all__ = [
    "Node",
    "Edge",
    "CampusGraph",
]
