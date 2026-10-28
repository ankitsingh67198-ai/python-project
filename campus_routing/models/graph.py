"""
Graph domain model for Smart Campus Navigation.

Maintains an in-memory adjacency structure representing campus pathways and landmarks.
Decoupled completely from presentation layers (Streamlit and Folium).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from campus_routing.exceptions import (
    DuplicateEdgeError,
    EdgeNotFoundError,
    NodeNotFoundError,
    ValidationError,
)
from campus_routing.models.edge import Edge
from campus_routing.models.node import Node


class CampusGraph:
    """
    In-memory weighted graph model for campus navigation.

    Supports:
        - Nodes representing landmarks and pathway intersections.
        - Directed and undirected edges with physical distances and routing costs.
        - Efficient neighbor lookup with dynamic blockage and accessibility filters.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        # Stores unique edges by canonical key
        self._edges: Dict[Tuple[str, str], Edge] = {}
        # Adjacency list: node_id -> List of (neighbor_id, Edge)
        self._adjacency: Dict[str, List[Tuple[str, Edge]]] = {}

    @property
    def node_count(self) -> int:
        """Returns total number of nodes in graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Returns total number of unique physical edges in graph."""
        return len(self._edges)

    # --------------------------------------------------------------------------
    # Node Management
    # --------------------------------------------------------------------------

    def add_node(self, node: Node, overwrite: bool = False) -> None:
        """
        Inserts a Node into the graph.

        Args:
            node: Node instance to add.
            overwrite: If True, replaces existing node with same ID.
        """
        if not isinstance(node, Node):
            raise ValidationError(f"Expected Node instance, got {type(node)}")

        if node.id in self._nodes and not overwrite:
            raise ValidationError(f"Node with ID '{node.id}' already exists in graph.")

        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def has_node(self, node_id: str) -> bool:
        """Checks if a node ID exists in the graph."""
        return node_id in self._nodes

    def get_node(self, node_id: str) -> Node:
        """
        Retrieves a Node by ID.

        Raises:
            NodeNotFoundError: If node_id does not exist.
        """
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' does not exist in graph.")
        return self._nodes[node_id]

    def get_nodes(
        self,
        landmark_only: bool = False,
        category: Optional[str] = None,
    ) -> List[Node]:
        """Returns a filtered list of nodes."""
        results = list(self._nodes.values())
        if landmark_only:
            results = [n for n in results if n.is_landmark]
        if category is not None:
            results = [n for n in results if n.category == category]
        return results

    # --------------------------------------------------------------------------
    # Edge Management
    # --------------------------------------------------------------------------

    def add_edge(self, edge: Edge) -> None:
        """
        Inserts an Edge connecting two existing nodes in the graph.

        Raises:
            NodeNotFoundError: If source or target node does not exist.
            DuplicateEdgeError: If the edge already exists.
        """
        if not isinstance(edge, Edge):
            raise ValidationError(f"Expected Edge instance, got {type(edge)}")

        if edge.source_id not in self._nodes:
            raise NodeNotFoundError(
                f"Cannot add edge: source node '{edge.source_id}' does not exist in graph."
            )
        if edge.target_id not in self._nodes:
            raise NodeNotFoundError(
                f"Cannot add edge: target node '{edge.target_id}' does not exist in graph."
            )

        key = edge.canonical_endpoints()
        if key in self._edges:
            raise DuplicateEdgeError(
                f"Edge between '{edge.source_id}' and '{edge.target_id}' already exists in graph."
            )

        self._edges[key] = edge

        # Populate adjacency lists
        self._adjacency[edge.source_id].append((edge.target_id, edge))
        if not edge.is_directed:
            self._adjacency[edge.target_id].append((edge.source_id, edge))

    def has_edge(self, source_id: str, target_id: str) -> bool:
        """Checks if a pathway exists connecting source_id to target_id."""
        return self.get_edge(source_id, target_id) is not None

    def get_edge(self, source_id: str, target_id: str) -> Optional[Edge]:
        """
        Retrieves the Edge connecting source_id and target_id.
        Handles undirected reverse lookups transparently.
        """
        # 1. Direct directed check
        if (source_id, target_id) in self._edges:
            return self._edges[(source_id, target_id)]

        # 2. Canonical undirected check
        canonical_key = (min(source_id, target_id), max(source_id, target_id))
        if canonical_key in self._edges:
            edge = self._edges[canonical_key]
            if not edge.is_directed:
                return edge

        return None

    def get_edges(self, include_blocked: bool = True) -> List[Edge]:
        """Returns all unique edges in the graph."""
        if include_blocked:
            return list(self._edges.values())
        return [e for e in self._edges.values() if not e.is_blocked]

    def set_edge_blocked(
        self,
        source_id: str,
        target_id: str,
        is_blocked: bool,
        block_reason: Optional[str] = None,
    ) -> None:
        """
        Updates the blockage status of an existing edge without deleting it.

        Raises:
            EdgeNotFoundError: If pathway does not exist.
        """
        existing = self.get_edge(source_id, target_id)
        if existing is None:
            raise EdgeNotFoundError(
                f"Pathway between '{source_id}' and '{target_id}' does not exist in graph."
            )

        key = existing.canonical_endpoints()
        updated_edge = Edge(
            source_id=existing.source_id,
            target_id=existing.target_id,
            distance_m=existing.distance_m,
            is_directed=existing.is_directed,
            surface_type=existing.surface_type,
            is_accessible=existing.is_accessible,
            is_blocked=is_blocked,
            block_reason=block_reason if is_blocked else None,
            source_provenance=existing.source_provenance,
            verification_status=existing.verification_status,
            cost=existing.cost,
        )

        self._edges[key] = updated_edge
        # Re-sync adjacency references for modified edge
        self._refresh_adjacency_edge(key, updated_edge)

    def _refresh_adjacency_edge(self, key: Tuple[str, str], new_edge: Edge) -> None:
        """Updates edge references in the adjacency lists."""
        u, v = key
        for node in (u, v):
            if node in self._adjacency:
                new_list: List[Tuple[str, Edge]] = []
                for neighbor, old_edge in self._adjacency[node]:
                    if old_edge.canonical_endpoints() == key:
                        new_list.append((neighbor, new_edge))
                    else:
                        new_list.append((neighbor, old_edge))
                self._adjacency[node] = new_list

    def get_neighbors(
        self,
        node_id: str,
        include_blocked: bool = False,
        accessible_only: bool = False,
    ) -> List[Tuple[str, Edge]]:
        """
        Returns adjacent (neighbor_id, Edge) tuples from node_id.

        Args:
            node_id: Source node ID.
            include_blocked: If False, omits blocked edges.
            accessible_only: If True, omits edges that are not wheelchair accessible.

        Raises:
            NodeNotFoundError: If node_id does not exist in graph.
        """
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' does not exist in graph.")

        results: List[Tuple[str, Edge]] = []
        for neighbor_id, edge in self._adjacency.get(node_id, []):
            if not include_blocked and edge.is_blocked:
                continue
            if accessible_only and not edge.is_accessible:
                continue
            results.append((neighbor_id, edge))

        return results

    # --------------------------------------------------------------------------
    # Serialization & Factory Methods
    # --------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serializes graph to a dictionary."""
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampusGraph":
        """Builds a CampusGraph from dictionary representation."""
        graph = cls()
        for node_dict in data.get("nodes", []):
            graph.add_node(Node.from_dict(node_dict))
        for edge_dict in data.get("edges", []):
            graph.add_edge(Edge.from_dict(edge_dict))
        return graph

    @classmethod
    def from_json_file(cls, file_path: Union[str, Path]) -> "CampusGraph":
        """Loads a CampusGraph from a JSON file."""
        target_path = Path(file_path)
        if not target_path.is_file():
            raise FileNotFoundError(f"Graph JSON file not found at: {target_path}")

        raw_data = json.loads(target_path.read_text(encoding="utf-8"))
        return cls.from_dict(raw_data)

    # Convenience alias for from_json_file
    from_json = from_json_file

    @classmethod
    def from_repository(cls, repo: Any) -> "CampusGraph":
        """
        Constructs a CampusGraph from a CampusRepository database instance.
        """
        graph = cls()
        db_nodes = repo.list_nodes()
        for n in db_nodes:
            graph.add_node(
                Node(
                    id=n["id"],
                    name=n["name"],
                    category=n["category"],
                    latitude=n["latitude"],
                    longitude=n["longitude"],
                    elevation_m=n["elevation_m"],
                    is_landmark=bool(n["is_landmark"]),
                    description=n["description"],
                    source_provenance=n["source_provenance"],
                    verification_status=n["verification_status"],
                )
            )

        db_edges = repo.list_edges(include_blocked=True)
        for e in db_edges:
            graph.add_edge(
                Edge(
                    source_id=e["source_id"],
                    target_id=e["target_id"],
                    distance_m=float(e["distance_m"]),
                    is_directed=bool(e["is_directed"]),
                    surface_type=e["surface_type"],
                    is_accessible=bool(e["is_accessible"]),
                    is_blocked=bool(e["is_blocked"]),
                    block_reason=e["block_reason"],
                    source_provenance=e["source_provenance"],
                    verification_status=e["verification_status"],
                )
            )

        return graph
