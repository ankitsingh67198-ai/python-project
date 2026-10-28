# Technical Project Plan & Architecture Design
## Smart Campus Navigation System for IIIT Kottayam

**Document Version:** 1.1.0  
**Status:** Draft / Proposed for Review (Pending Milestone 1 Approval)  
**Target Institution:** Indian Institute of Information Technology Kottayam (IIIT Kottayam), Valavoor, Kerala  
**Author:** Senior Python Software Architect & Graph-Algorithm Engineer  
**Date:** October 2026  

---

## 1. System Architecture & High-Level Design

### 1.1 Architectural Philosophy & Core Principles
The Smart Campus Navigation System is engineered as a modular, decoupled, and academically rigorous software application. The design adheres to key software engineering principles:
1. **Single Source of Truth (DRY Principle):** The routing engine, graph modeling, database queries, and data validation rules reside in a shared core Python package (`campus_routing/`). Both the interactive Streamlit web application and the Jupyter exploratory notebook consume this package without duplicating algorithmic or query logic.
2. **Separation of Concerns:** Presentation concerns (Streamlit, Folium HTML rendering) are isolated from business logic (Dijkstra pathfinding, graph construction) and persistence (SQLite schema, connection management).
3. **Data Provenance & Scientific Honesty:** Verified institutional landmarks are strictly separated from unverified micro-coordinates and pathways. Production databases do not fabricate unverified paths. Synthetic demonstration data is isolated in separate fixtures.
4. **Physical Distance vs. Routing Cost Separation:** Ground physical distance (`distance_m`) is always preserved at full IEEE-754 floating-point precision. Cost functions (elevation penalties, stair avoidance) compute an algorithmic impedance score without mutating the true physical distance.
5. **Dual-Solver Verification:** Algorithmic correctness is proven through dual execution against NetworkX (`networkx.dijkstra_path`), guaranteeing formal optimality.
6. **Defensive Programming:** Extensive runtime validation prevents invalid spatial states, graph disconnection crashes, and data corruption.

### 1.2 Multi-Tier Architectural Diagram

```
+---------------------------------------------------------------------------------------+
|                                  PRESENTATION LAYER                                   |
|                                                                                       |
|    +----------------------------------+          +-------------------------------+    |
|    |      Streamlit Web Interface     |          |       Jupyter Notebook        |    |
|    |     (`app/streamlit_app.py`)     |          | (`notebooks/walkthrough.ipynb`|    |
|    +-----------------+----------------+          +---------------+---------------+    |
+----------------------|-------------------------------------------|--------------------+
                       |                                           |
                       +-------------------+   +-------------------+
                                           |   |
+------------------------------------------v---v----------------------------------------+
|                                   SERVICE LAYER                                       |
|                                                                                       |
|   +------------------------------------+       +----------------------------------+   |
|   |          Routing Service           |       |         Map Generator            |   |
|   |  (`campus_routing.services.router`)|       | (`campus_routing.viz.map_builder`|   |
|   +-----------------+------------------+       +-----------------+----------------+   |
+---------------------|--------------------------------------------|--------------------+
                      |                                            |
                      +--------------------+   +-------------------+
                                           |   |
+------------------------------------------v---v----------------------------------------+
|                                DOMAIN & ALGORITHM LAYER                               |
|                                                                                       |
|   +--------------------------+  +--------------------------+  +-------------------+   |
|   |      Custom Dijkstra     |  |    NetworkX Benchmark    |  |    Graph Model    |   |
|   |   (`algorithms.dijkstra`)|  |   (`algorithms.networkx`)|  |  (`models.graph`) |   |
|   +--------------------------+  +--------------------------+  +-------------------+   |
+------------------------------------------|--------------------------------------------+
                                           |
+------------------------------------------v--------------------------------------------+
|                             DATA ACCESS & PERSISTENCE LAYER                           |
|                                                                                       |
|   +-----------------------------+                  +------------------------------+   |
|   |     Database Repository     |                  |        Data Validator        |   |
|   |    (`campus_routing.db`)    |                  |  (`campus_routing.validation`|   |
|   +--------------+--------------+                  +--------------+---------------+   |
|                  |                                                |                   |
|                  v                                                v                   |
|   +-------------------------------------------------------------------------------+   |
|   |                       SQLite Database (`data/campus.db`)                      |   |
|   +-------------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------------+
```

---

## 2. Proposed Project Folder Structure

```
Smart-Campus-Navigation/
├── .gitignore                          # Standard Python, SQLite, OS, and IDE ignore patterns
├── README.md                           # Project introduction, quickstart, and feature overview
├── pyproject.toml                      # Project metadata, build tool configuration, and tool options
├── requirements.txt                    # Pinned production and development dependencies
│
├── campus_routing/                     # Core reusable domain library (shared by UI & Notebook)
│   ├── __init__.py                     # Package export declarations
│   ├── config.py                       # Configuration constants (DB path, map center, zoom limits)
│   ├── exceptions.py                   # Domain-specific exceptions (PathNotFoundError, etc.)
│   │
│   ├── algorithms/                     # Graph search and routing implementations
│   │   ├── __init__.py
│   │   ├── dijkstra.py                 # Custom priority-queue Dijkstra implementation (full precision)
│   │   ├── networkx_solver.py          # NetworkX benchmark solver for cross-validation
│   │   └── validator.py                # Dual-solver equivalence verification harness
│   │
│   ├── db/                             # Persistence and SQLite management
│   │   ├── __init__.py
│   │   ├── connection.py               # SQLite connection manager with WAL and foreign key support
│   │   ├── repository.py               # Node, Edge, and Obstruction CRUD operations
│   │   ├── schema.sql                  # DDL statements with coordinate checks and canonical edge order
│   │   └── seeder.py                   # Idempotent seed script for IIIT Kottayam landmark dataset
│   │
│   ├── models/                         # Domain entities and data structures
│   │   ├── __init__.py
│   │   ├── node.py                     # Node dataclass with spatial, provenance, and landmark attributes
│   │   ├── edge.py                     # Edge dataclass with physical distance, direction, and accessibility
│   │   └── graph.py                    # Adjacency-list Graph container and builder
│   │
│   ├── services/                       # High-level orchestration services
│   │   ├── __init__.py
│   │   ├── navigation_service.py       # Orchestrates graph loading, pathfinding, and directions
│   │   └── obstruction_service.py      # Manages dynamic edge blocking and alternative routing
│   │
│   ├── validation/                     # Spatial and topological data validation
│   │   ├── __init__.py
│   │   ├── spatial_rules.py            # Bounding box envelope, coordinate completeness
│   │   └── graph_integrity.py          # Connectivity audit, cycle check, negative weight check
│   │
│   └── visualization/                  # Map rendering and cartographic helpers
│       ├── __init__.py
│       ├── map_builder.py              # Folium map constructor with campus base layers
│       ├── styles.py                   # Color themes, polyline styling, and marker icons
│       └── directions.py               # Natural language direction synthesizer
│
├── app/                                # Streamlit Web Application
│   ├── __init__.py
│   ├── streamlit_app.py                # Streamlit entrypoint script
│   └── components/                     # Modular Streamlit UI widgets
│       ├── __init__.py
│       ├── sidebar.py                  # Origin, destination, and accessibility controls
│       ├── blockage_panel.py           # Pathway obstruction management widget
│       └── metrics_card.py             # Custom HTML/CSS cards for distance and duration
│
├── notebooks/                          # Academic Demonstration & Laboratory
│   ├── __init__.py
│   └── campus_navigation_walkthrough.ipynb # Comprehensive academic walkthrough notebook
│
├── tests/                              # Automated Pytest Suite
│   ├── __init__.py
│   ├── conftest.py                     # Shared test fixtures (in-memory SQLite, test graphs)
│   ├── unit/                           # Isolated unit tests
│   │   ├── test_repository.py          # Database queries, updates, transactions, constraints
│   │   ├── test_models.py              # Node, Edge, and Graph data structure tests
│   │   └── test_dijkstra.py            # Dijkstra optimality, edge cases, negative weights
│   └── integration/                    # End-to-end integration tests
│       ├── test_dual_solver.py         # Custom Dijkstra vs. NetworkX equivalence on demonstration data
│       └── test_navigation_service.py  # Service-level pathfinding and dynamic blockage re-routing
│
├── data/                               # Persistent Storage & Raw Datasets
│   ├── campus.db                       # SQLite database file (created on initialization)
│   ├── seed_landmarks.json             # Declarative verified landmarks for IIIT Kottayam
│   └── demonstration_graph.json        # Explicitly marked synthetic graph for testing & demo
│
├── docs/                               # Formal Architecture & Requirement Documentation
│   ├── REQUIREMENTS.md                 # System Requirements Specification (SRS)
│   └── PROJECT_PLAN.md                 # This Architecture and Project Plan document
│
└── reports/                            # Publication-Quality PDF Report Generation
    ├── generate_pdf_report.py          # Automated ReportLab PDF generator script
    └── assets/                         # Report styling assets, charts, and logos
```

---

## 3. Custom Dijkstra Implementation & NetworkX Validation Strategy

### 3.1 Mathematical Formulation of Custom Dijkstra
Let $G = (V, E)$ be a weighted graph where $V$ represents campus nodes and $E$ represents walkable pathway segments. Each edge $e = (u, v) \in E$ has an associated physical distance $w(u, v) \in \mathbb{R}^+$ in meters.

#### Algorithmic Principles:
1. **Full-Precision Calculation:** Distances are maintained as IEEE 754 double-precision floats throughout traversal, edge relaxation, and total distance reporting. No intermediate or final truncation/rounding occurs in the algorithmic layer.
2. **Separation of Physical Distance and Routing Cost:**
   - Default routing minimizes pure physical distance $w(u, v)$.
   - Weighted preference routing (e.g., stairs penalty, slope factor) utilizes a cost function $C(u, v) = w(u, v) \times (1 + \text{penalty})$, while the returned result includes both the total physical distance and the cost score.
3. **Handling Directionality:** Directed edges (`is_directed = 1`) are traversed only in the specified $u \to v$ direction. Undirected edges (`is_directed = 0`) allow traversal in both directions.

```python
# Algorithmic Skeleton for campus_routing/algorithms/dijkstra.py
import heapq
from typing import Dict, List, Optional, Set, Tuple

def dijkstra_shortest_path(
    adj_list: Dict[str, List[Tuple[str, float]]],
    source: str,
    target: str,
    blocked_edges: Optional[Set[Tuple[str, str]]] = None
) -> Tuple[List[str], float]:
    """
    Computes shortest path using Dijkstra's algorithm with a min-heap.
    
    Time Complexity: O((|E| + |V|) log |V|)
    Space Complexity: O(|V|)
    
    Returns:
        Tuple[List[str], float]: (Ordered path nodes, unrounded physical distance in meters)
    """
    if blocked_edges is None:
        blocked_edges = set()
        
    if source not in adj_list or target not in adj_list:
        raise KeyError(f"Source '{source}' or Target '{target}' not present in graph.")

    distances: Dict[str, float] = {node: float("inf") for node in adj_list}
    predecessors: Dict[str, Optional[str]] = {node: None for node in adj_list}
    distances[source] = 0.0
    
    # Priority Queue elements: (accumulated_distance, current_node)
    pq: List[Tuple[float, str]] = [(0.0, source)]
    visited: Set[str] = set()

    while pq:
        curr_dist, u = heapq.heappop(pq)
        
        if curr_dist > distances[u]:
            continue
            
        if u == target:
            break
            
        visited.add(u)
        
        for v, weight in adj_list.get(u, []):
            if weight < 0:
                raise ValueError(f"Negative edge weight encountered: ({u}, {v}) = {weight}")
            # Check for dynamic blockage in both directions
            if (u, v) in blocked_edges or (v, u) in blocked_edges:
                continue
                
            new_dist = curr_dist + weight
            if new_dist < distances[v]:
                distances[v] = new_dist
                predecessors[v] = u
                heapq.heappush(pq, (new_dist, v))
                
    if distances[target] == float("inf"):
        raise PathNotFoundError(f"No navigable path exists between '{source}' and '{target}'.")
        
    # Reconstruct route
    path = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = predecessors[curr]
    path.reverse()
    
    # Return unrounded full-precision distance
    return path, distances[target]
```

### 3.2 NetworkX Dual-Solver Validation Strategy
1. **Total Distance Parity:**
   $$|\text{dist}_{\text{custom}}(s, t) - \text{dist}_{\text{networkx}}(s, t)| < 10^{-4}\text{ meters}$$
2. **Handling Alternate Shortest Paths (Tie-Breaking):**
   If multiple distinct paths yield the exact same minimum distance, the validation harness verifies:
   - Total distance equals NetworkX's `dijkstra_path_length`.
   - The sum of edge weights along the custom path matches the optimal distance.
   - Every hop exists and is unblocked.

---

## 4. SQLite Data Model & Dataset Validation Rules

### 4.1 Relational DDL Specification (`schema.sql`)

```sql
-- Schema DDL: schema.sql
PRAGMA foreign_keys = ON;

-- Table: nodes (Campus landmarks, entrances, and trail junctions)
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('academic', 'administrative', 'residential', 'dining', 'sports', 'amenity', 'gate', 'junction', 'other')),
    latitude REAL CHECK(
        (latitude IS NULL AND longitude IS NULL) OR 
        (latitude IS NOT NULL AND longitude IS NOT NULL AND latitude BETWEEN 9.750000 AND 9.760000 AND longitude BETWEEN 76.645000 AND 76.656000)
    ),
    longitude REAL CHECK(
        (latitude IS NULL AND longitude IS NULL) OR 
        (latitude IS NOT NULL AND longitude IS NOT NULL AND latitude BETWEEN 9.750000 AND 9.760000 AND longitude BETWEEN 76.645000 AND 76.656000)
    ),
    elevation_m REAL,
    is_landmark INTEGER NOT NULL DEFAULT 1 CHECK(is_landmark IN (0, 1)),
    description TEXT,
    source_provenance TEXT NOT NULL DEFAULT 'OFFICIAL_INSTITUTIONAL' CHECK(source_provenance IN ('OFFICIAL_INSTITUTIONAL', 'EXTERNAL_PUBLIC_GEODATA', 'SYNTHETIC_DEMO', 'FIELD_SURVEY_VERIFIED')),
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK(verification_status IN ('UNVERIFIED', 'OFFICIAL_REFERENCE', 'FIELD_SURVEYED', 'SYNTHETIC_DEMO')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: edges (Walkable pathway segments)
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    distance_m REAL NOT NULL CHECK(distance_m > 0.0),
    is_directed INTEGER NOT NULL DEFAULT 0 CHECK(is_directed IN (0, 1)),
    surface_type TEXT DEFAULT 'paved' CHECK(surface_type IN ('paved', 'concrete', 'asphalt', 'stairs', 'trail', 'unpaved', 'unknown')),
    is_accessible INTEGER NOT NULL DEFAULT 1 CHECK(is_accessible IN (0, 1)),
    is_blocked INTEGER NOT NULL DEFAULT 0 CHECK(is_blocked IN (0, 1)),
    block_reason TEXT,
    source_provenance TEXT NOT NULL DEFAULT 'SYNTHETIC_DEMO' CHECK(source_provenance IN ('OFFICIAL_INSTITUTIONAL', 'EXTERNAL_PUBLIC_GEODATA', 'SYNTHETIC_DEMO', 'FIELD_SURVEY_VERIFIED')),
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK(verification_status IN ('UNVERIFIED', 'OFFICIAL_REFERENCE', 'FIELD_SURVEYED', 'SYNTHETIC_DEMO')),
    CHECK(source_id <> target_id),
    CHECK(is_directed = 1 OR source_id < target_id),
    UNIQUE(source_id, target_id)
);

-- Table: campus_metadata (Key-value system registry)
CREATE TABLE IF NOT EXISTS campus_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for rapid neighbor lookup during graph construction
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_nodes_category ON nodes(category);
CREATE INDEX IF NOT EXISTS idx_nodes_landmark ON nodes(is_landmark);
```

### 4.2 Dataset Integrity & Validation Architecture
1. **Coordinate Completeness Constraint:** Rejects any record where latitude is supplied without longitude, or vice-versa.
2. **Sanity Envelope Check:** Validates that when coordinates are present, they reside within $[9.750, 9.760]^\circ\text{ N}$ and $[76.645, 76.656]^\circ\text{ E}$. Note: this envelope is an engineering guardrail, not the physical cadastral property boundary.
3. **Canonical Undirected Edges:** For undirected pathways (`is_directed = 0`), storage enforces `source_id < target_id`. This prevents duplicate reverse records and ensures consistent queries.
4. **Idempotent Seeding:** The seeder checks existing records before insertion and preserves any user-modified states (`is_blocked`, `block_reason`).

---

## 5. Technical Risk Analysis & Mitigation Strategies

| Risk ID | Risk Category | Description & Impact | Probability | Impact Severity | Concrete Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TR-01** | Data Accuracy | Incomplete micro-pathway geometry on OpenStreetMap for IIIT Kottayam leading to inaccurate walking paths. | High | High | Anchor all key landmarks to verified identities with coordinates marked `NULL` until surveyed; isolate synthetic demonstration networks in separate fixtures; document field-survey protocol for student data collection. |
| **TR-02** | Topography / Terrain | Hilly Valavoor terrain causes 2D flat distance to underestimate walking effort across steep slopes or stairs. | High | Medium | Store `elevation_m`, `surface_type`, and `is_accessible` flags in SQLite; design Dijkstra weighting function to compute an impedance score separate from pure physical distance. |
| **TR-03** | Algorithmic / Topology | Dynamic pathway blockages isolate parts of the campus, triggering unhandled exceptions. | Medium | High | Implement early termination on unreachable components ($D[t] = \infty$); catch `PathNotFoundError` in services; present clear, friendly Streamlit banner explaining the blockage. |
| **TR-04** | Dual-Solver Discrepancy | Custom Dijkstra chooses a different path than NetworkX when multiple paths have identical minimum distances. | Medium | Low | Design validation harness to test for total distance parity ($|\Delta| < 10^{-4}$) rather than strict node-index identity; verify that alternative paths are fully valid shortest paths. |
| **TR-05** | Environment / Windows | Windows path separator issues (`\` vs `/`), file locking on SQLite during Streamlit hot-reloading. | Medium | Medium | Use `pathlib.Path` exclusively; employ WAL mode (`PRAGMA journal_mode=WAL;`) in SQLite to support concurrent reads; document explicit PowerShell commands. |
| **TR-06** | Data Conflation | Inadvertently presenting synthetic demonstration paths as actual verified campus routes. | High | High | Enforce provenance tagging (`source_provenance`, `verification_status`); check `has_verified_routing_network` in metadata; display prominent UI disclaimer banner when demonstration data is active. |

---

## 6. Staged Implementation Roadmap & Testable Milestones

### Milestone Details:

#### Milestone 1: Environment Setup, Database Schema & Ingestion Pipeline (Current Focus)
* **Scope:** Configure Python environment, create `campus_routing/db/`, implement `schema.sql`, connection manager, repository CRUD, and seed verified landmark catalog (`seed_landmarks.json`).
* **Verification Gate:** Run `pytest tests/unit/test_repository.py`. Ensure SQLite database initializes with all tables, constraints trigger properly on invalid inputs, and verified landmarks are seeded idempotently without fabricating coordinates or pathways.

#### Milestone 2: Core Graph Model & Dual Dijkstra Routing Engine
* **Scope:** Implement `Node`, `Edge`, and `CampusGraph` models; implement pure Python priority-queue `dijkstra_shortest_path` preserving full floating-point precision; implement `NetworkXRouter` and dual-solver equivalence validator over demonstration fixtures.
* **Verification Gate:** Run `pytest tests/integration/test_dual_solver.py`. 100% of tested origin-destination pairs on the demonstration graph match NetworkX distances within $10^{-4}\text{ m}$.

#### Milestone 3: Interactive Cartography (Folium Map Generator)
* **Scope:** Implement `map_builder.py` and `styles.py`. Render base campus map with color-coded landmark icons, pathway network polylines, blocked segments, and animated active route overlay.
* **Verification Gate:** Generate standalone HTML map test file; verify correct geographic bounds, high-contrast visual styling, and tooltip responsiveness.

#### Milestone 4: Streamlit Web Application & Dynamic Obstruction Controls
* **Scope:** Build `app/streamlit_app.py` with origin/destination dropdowns, accessibility filter, interactive blockage toggles, metric cards (distance, walking time), and embedded Folium map.
* **Verification Gate:** Launch Streamlit application on local port; execute manual and automated browser UI flows verifying route selection, blockage updates, and error handling.

#### Milestone 5: Automated Testing Suite & Edge-Case Hardening
* **Scope:** Complete unit and integration test suite across `tests/`. Test graph cycles, disconnected nodes, blocked bridges, single-node paths ($S = S$), and negative edge rejection.
* **Verification Gate:** Run `pytest --cov=campus_routing --cov-report=term-missing`. Verify overall coverage exceeds 90% and all edge cases pass.

#### Milestone 6: Academic Demonstration Jupyter Notebook
* **Scope:** Build `notebooks/campus_navigation_walkthrough.ipynb` importing `campus_routing`. Include algorithm explanations, step-by-step priority queue visualization, NetworkX visual graphs, and empirical runtime benchmarks.
* **Verification Gate:** Execute `jupyter nbconvert --to notebook --execute notebooks/campus_navigation_walkthrough.ipynb`. All cells execute cleanly without warnings or errors.

#### Milestone 7: Automated Publication-Quality PDF Report Generation
* **Scope:** Implement `reports/generate_pdf_report.py` using ReportLab. Pull live test results, campus metrics, and benchmark plots into a cohesive academic technical report (`reports/IIITK_Campus_Navigation_Report.pdf`).
* **Verification Gate:** Compile PDF report via CLI; verify typography, formatting, structural completeness, and verification accuracy.

---

## 7. Technology Stack, Dependencies & Windows Setup Guide

### 7.1 Python Version & Dependencies Specification
The project requires **Python 3.10+**.

```toml
# requirements.txt
streamlit>=1.35.0          # High-performance reactive web application framework
folium>=0.16.0             # Leaflet.js Python wrapper for spatial cartography
streamlit-folium>=0.20.0   # Bi-directional integration between Streamlit and Folium
networkx>=3.2.1            # Industry-standard graph theory and pathfinding reference
pandas>=2.2.0              # Tabular data manipulation and metric formatting
reportlab>=4.2.0           # Programmatic PDF generation engine for technical reports
matplotlib>=3.8.0          # Plotting engine for benchmark charts and graph topology
jupyterlab>=4.1.0          # Academic exploration and interactive demonstration
pytest>=8.1.0              # Automated testing framework
pytest-cov>=5.0.0          # Code coverage reporting plugin for Pytest
```

### 7.2 Windows PowerShell Environment Setup
```powershell
# 1. Open PowerShell in workspace root
cd w:\Downloads\Smart-Campus-Navigation

# 2. Run unit tests
python -m pytest tests/ -v
```

---

## 8. Unresolved Questions & Research Backlog
1. **Entrance Door Pinpointing:** Exact physical coordinates of each building entrance door pending physical GPS survey.
2. **Topographic Elevation Profiles:** Exact step counts and vertical grade on the path connecting Meenachil/Sahyadri Hostels to Academic Block 1.
3. **Monsoon Routing:** Determination of covered vs open pathways for weather-based path preferences.
