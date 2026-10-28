"""
Builds the formal academic Jupyter Notebook for the Smart Campus Navigation System.
Generates notebooks/campus_navigation_walkthrough.ipynb covering all 11 required sections.
"""

from pathlib import Path
import nbformat as nbf

def create_notebook() -> None:
    project_root = Path(__file__).resolve().parent.parent
    nb = nbf.v4.new_notebook()
    cells = []

    # =========================================================================
    # SECTION 1: INTRODUCTION AND PROBLEM STATEMENT
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""# Smart Campus Navigation System for IIIT Kottayam
## Academic Walkthrough, Graph Theory Foundations & Algorithmic Analysis

**Institution:** Indian Institute of Information Technology Kottayam (IIIT Kottayam)  
**Campus Location:** Valavoor, Pala, Kottayam, Kerala 686635, India  
**Curriculum Level:** Second-Year B.Tech Computer Science and Engineering  
**Project Repository:** `Smart-Campus-Navigation`  
**Milestone:** 5 — Academic Demonstration and Technical Report  

---

### 1. Introduction and Problem Statement

Navigating a modern academic institution situated on undulating terrain presents unique spatial challenges. The permanent campus of IIIT Kottayam spans approximately 53 acres of hilly topography in Valavoor, Pala. The campus comprises distinct functional zones including academic complexes, multi-storey student residences, dining facilities, sports complexes, and utility infrastructure.

Pedestrians moving across campus encounter diverse walkway geometries:
1. **Paved and concrete roads** suitable for vehicular and pedestrian traffic.
2. **Dedicated asphalt walkways** connecting primary academic facilities.
3. **Flight of stairs and steep stairways** cutting through natural terrain contours.
4. **Unpaved trails and dirt pathways** traversing undeveloped sectors.

#### Problem Formulation
A student, faculty member, or visitor requires algorithmic assistance to determine the shortest and most efficient walking route between any two campus facilities. However, a naive shortest-path computation based solely on Euclidean straight-line distance is inadequate because:
* Pathways have directional constraints (one-way pedestrian corridors, turnstile gates).
* Surface types impose different movement impedances (e.g. climbing 50 metres of steep stairs entails significantly higher physical exertion than walking 50 metres on level asphalt).
* Obstructions frequently occur due to ongoing campus expansion, maintenance, or weather events.
* Mobility-impaired individuals require step-free, wheelchair-accessible routes that strictly bypass stairs.

#### Project Objectives
1. **Formal Graph Representation:** Model campus topology as an in-memory weighted directed/undirected graph with explicit spatial attributes.
2. **Algorithmic Pathfinding:** Implement a custom, heap-based Dijkstra shortest-path algorithm maintaining full IEEE-754 double precision without premature rounding.
3. **Rigorous Dual-Solver Validation:** Empirically cross-validate all custom path calculations against an independent reference solver (NetworkX).
4. **Dynamic Rerouting & Accessibility:** Support in-memory pathway blockages and step-free accessibility constraints.
5. **Interactive Visualization:** Embed interactive Leaflet/Folium cartographic views within a modern Streamlit web application.

#### Critical Data Provenance Rule
The production database (`data/campus.db`) contains official names and metadata for 18 verified campus landmarks, but **zero verified pedestrian footways or building entrance GPS coordinates**. Internal pathways await an on-site field survey using RTK-GPS logging. To preserve scientific integrity, all algorithmic demonstrations in this notebook utilize an explicitly isolated **synthetic demonstration dataset** (`data/demonstration_graph.json`, 6 nodes, 6 edges). Synthetic test data is never conflated with verified campus geodata."""
    ))

    # =========================================================================
    # SECTION 2: ENVIRONMENT AND ARCHITECTURE
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""---
### 2. Environment and Architecture

The software architecture is decoupled into distinct, single-responsibility layers:
* **Relational Storage Layer (`campus_routing.db`):** SQLite database enforcing foreign keys, check constraints, WAL journaling, and metadata provenance.
* **Graph Domain Model (`campus_routing.models`):** Immutable `Node` and `Edge` objects and an in-memory `CampusGraph` managing adjacency lists.
* **Algorithmic Routing Layer (`campus_routing.algorithms`):** Custom priority-queue Dijkstra implementation, NetworkX reference solver, and dual-solver empirical cross-validation harness.
* **Cartographic Visualization Layer (`campus_routing.visualization`):** Folium map builders providing isolated Campus Context and Synthetic Demonstration map modes.
* **Presentation Layer (`app/`):** Interactive Streamlit web application running locally.
* **Academic Evaluation Layer (`notebooks/` and `reports/`):** Reproducible computational notebook and formal PDF technical report.

```
+-------------------------------------------------------------------------+
|                         STREAMLIT APPLICATION (app/)                    |
|       Sidebar Controls  |  Metrics Cards  |  Dynamic Blockage Panel     |
+------------------------------------+------------------------------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
|                   CAMPUS ROUTING CORE LIBRARY                           |
|  +--------------------+  +----------------------+  +-----------------+  |
|  | Algorithms         |  | Visualization        |  | Models          |  |
|  |  * Custom Dijkstra |  |  * Folium Maps       |  |  * CampusGraph  |  |
|  |  * NetworkX Solver |  |  * Styles & Legends  |  |  * Node & Edge  |  |
|  |  * Validator       |  |  * Directions Module |  |                 |  |
|  +--------------------+  +----------------------+  +-----------------+  |
+------------------------------------+------------------------------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
|                 PERSISTENT STORAGE & SEED DATA (data/)                  |
|     campus.db (SQLite)  |  demonstration_graph.json  |  seed_data       |
+-------------------------------------------------------------------------+
```"""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Setup environment and import project libraries
import sys
from pathlib import Path
import time
import math
import json
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

# Ensure project root is accessible
project_root = Path.cwd().resolve()
if project_root.name == "notebooks":
    project_root = project_root.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from campus_routing.config import (
    DEFAULT_DB_PATH,
    DEMO_GRAPH_PATH,
    REFERENCE_CAMPUS_NAME,
    REFERENCE_LATITUDE,
    REFERENCE_LONGITUDE,
    REFERENCE_LOCATION,
)
from campus_routing.db.repository import CampusRepository
from campus_routing.models.graph import CampusGraph
from campus_routing.models.node import Node
from campus_routing.models.edge import Edge
from campus_routing.algorithms.dijkstra import dijkstra_shortest_path, RouteResult
from campus_routing.algorithms.networkx_solver import networkx_shortest_path
from campus_routing.algorithms.validator import validate_route_against_networkx
from campus_routing.visualization.directions import generate_route_directions
from campus_routing.visualization.map_builder import (
    create_campus_context_map,
    create_demonstration_map,
    export_map_to_html,
)

print("All project modules successfully imported.")
print(f"Active project root: {project_root}")
print(f"Python interpreter: {sys.version.split()[0]} ({sys.platform})")"""
    ))

    # =========================================================================
    # SECTION 3: DATASET INSPECTION & PROVENANCE AUDIT
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""---
### 3. Dataset Inspection and Data Provenance Audit

Scientific integrity requires complete clarity regarding which data points represent measured ground truth and which represent synthetic models.

We perform a two-part inspection:
1. **Synthetic Demonstration Graph (`demonstration_graph.json`):** 6 nodes and 6 edges configured with realistic planar coordinates and physical pathway lengths for testing algorithms.
2. **Production Database (`campus.db`):** 18 official landmarks seeded from institutional records, confirming that coordinates and walking edges are currently unpopulated pending GPS survey."""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# 1. Load and inspect the synthetic demonstration dataset
demo_graph = CampusGraph.from_json(DEMO_GRAPH_PATH)

nodes_data = []
for n in demo_graph.get_nodes():
    nodes_data.append({
        "Node ID": n.id,
        "Name": n.name,
        "Category": n.category,
        "Latitude (°N)": f"{n.latitude:.6f}" if n.latitude else "N/A",
        "Longitude (°E)": f"{n.longitude:.6f}" if n.longitude else "N/A",
        "Elevation (m)": n.elevation_m,
        "Provenance": n.source_provenance,
    })

df_nodes = pd.DataFrame(nodes_data)
print("=== SYNTHETIC DEMONSTRATION NODES (6 NODES) ===")
display(df_nodes)

edges_data = []
for e in demo_graph.get_edges(include_blocked=True):
    edges_data.append({
        "Source": e.source_id,
        "Target": e.target_id,
        "Distance (m)": f"{e.distance_m:.1f}",
        "Routing Cost": f"{e.effective_cost:.1f}",
        "Surface": e.surface_type,
        "Directed": bool(e.is_directed),
        "Accessible": bool(e.is_accessible),
        "Blocked": bool(e.is_blocked),
    })

df_edges = pd.DataFrame(edges_data)
print("\\n=== SYNTHETIC DEMONSTRATION EDGES (6 EDGES) ===")
display(df_edges)"""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# 2. Inspect the production SQLite database
repo = CampusRepository(DEFAULT_DB_PATH)
db_nodes = repo.list_nodes()
db_edges = repo.list_edges()
db_meta = repo.get_all_metadata()
has_network = repo.has_verified_routing_network()

print("=== PRODUCTION DATABASE (campus.db) AUDIT ===")
print(f"Campus Identity: {db_meta.get('campus_name')}")
print(f"Reference Datum: {db_meta.get('reference_latitude')}° N, {db_meta.get('reference_longitude')}° E")
print(f"Recorded Landmarks: {len(db_nodes)}")
print(f"Unsurveyed Landmarks (No Coordinates): {sum(1 for n in db_nodes if n.get('latitude') is None)}")
print(f"Recorded Walking Pathways: {len(db_edges)}")
print(f"Routing Network Verified Flag: {has_network}")

df_db_landmarks = pd.DataFrame(db_nodes)[["id", "name", "category", "source_provenance", "verification_status"]]
print("\\nSample Recorded Landmarks in Production DB:")
display(df_db_landmarks.head(6))
repo.close()"""
    ))

    # =========================================================================
    # SECTION 4: GRAPH THEORY FOUNDATIONS
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
r"""---
### 4. Graph Theory Foundations

A pedestrian transportation network is formally modeled as a weighted directed multigraph:

$$G = (V, E, w)$$

Where:
* $V = \{v_1, v_2, \dots, v_n\}$ is the set of vertices (landmarks, corridor intersections, pathway splits, building doors).
* $E \subseteq V \times V$ is the set of ordered pairs representing traversable pathway segments.
* $w: E \to \mathbb{R}^+$ is the cost function assigning an algorithmic impedance or travel resistance to each directed edge.

#### Physical Distance vs. Routing Impedance Cost
In classical textbook routing, edge weights typically equal physical Euclidean length ($w(e) = d(e)$). In a campus navigation system, physical ground distance in metres ($d(e)$) is decoupled from algorithmic traversal impedance ($c(e)$):

$$c(e) = d(e) \cdot \mu_{\text{surface}} \cdot \mu_{\text{slope}} \cdot \mu_{\text{barrier}}$$

Where:
* $\mu_{\text{surface}} \ge 1.0$: Penalty multiplier based on surface quality (e.g. paved = $1.0$, trail = $1.2$).
* $\mu_{\text{slope}} \ge 1.0$: Penalty for elevation changes (steep stairways, ramps).
* $\mu_{\text{barrier}} = \infty$: If the edge is closed or impassable.

Crucially, **both metrics are accumulated simultaneously**:
* `total_distance_m`: Preserves the true, unrounded physical ground distance for walking time estimation.
* `total_cost`: Minimized by Dijkstra's algorithm to determine the optimal pathway."""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Visualize the demonstration graph topology using NetworkX and Matplotlib
G_viz = nx.Graph()

for n in demo_graph.get_nodes():
    G_viz.add_node(n.id, label=n.name, category=n.category)

for e in demo_graph.get_edges(include_blocked=True):
    G_viz.add_edge(e.source_id, e.target_id, weight=e.distance_m, surface=e.surface_type, accessible=e.is_accessible)

# Fixed layout coordinates approximating relative positions
pos = {
    "DEMO_GATE": (0.0, 0.0),
    "DEMO_ACAD": (1.0, 1.0),
    "DEMO_LIBRARY": (2.2, 0.8),
    "DEMO_MESS": (1.8, 2.0),
    "DEMO_HOSTEL": (2.8, 2.6),
    "DEMO_SPORTS": (3.2, 0.2),
}

plt.figure(figsize=(10, 6), dpi=100)
node_colors = {
    "gate": "#37474F",
    "academic": "#1976D2",
    "residential": "#E65100",
    "dining": "#2E7D32",
    "sports": "#C2185B",
}
colors = [node_colors.get(demo_graph.get_node(n).category, "#757575") for n in G_viz.nodes()]

# Draw nodes and labels
nx.draw_networkx_nodes(G_viz, pos, node_color=colors, node_size=1200, alpha=0.9)
nx.draw_networkx_labels(G_viz, pos, font_size=9, font_color="white", font_weight="bold")

# Separate edges by accessibility
accessible_edges = [(u, v) for u, v, d in G_viz.edges(data=True) if d["accessible"]]
inaccessible_edges = [(u, v) for u, v, d in G_viz.edges(data=True) if not d["accessible"]]

nx.draw_networkx_edges(G_viz, pos, edgelist=accessible_edges, width=2.5, edge_color="#455A64", style="solid")
nx.draw_networkx_edges(G_viz, pos, edgelist=inaccessible_edges, width=2.5, edge_color="#D32F2F", style="dashed")

# Edge weight labels (metres)
edge_labels = {(u, v): f"{d['weight']:.1f}m\\n({d['surface']})" for u, v, d in G_viz.edges(data=True)}
nx.draw_networkx_edge_labels(G_viz, pos, edge_labels=edge_labels, font_size=8, font_color="#263238")

plt.title("Synthetic Campus Topology (Solid: Accessible | Red Dashed: Inaccessible/Stairs)", fontsize=12, fontweight="bold", pad=15)
plt.axis("off")
plt.tight_layout()
plt.show()"""
    ))

    # =========================================================================
    # SECTION 5: DIJKSTRA'S ALGORITHM IMPLEMENTATION & TRACE
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
r"""---
### 5. Dijkstra's Algorithm Implementation and Step-by-Step Trace

Dijkstra's algorithm finds the single-source shortest path in a graph with non-negative edge weights.

#### Mathematical Invariant
At every iteration $k$, the algorithm maintains a partition of vertices into:
1. $S$: Settled vertices whose shortest path from source $s$ is proven optimal.
2. $Q = V \setminus S$: Unsettled vertices stored in a priority queue keyed by tentative distance $D[u]$.

The fundamental greedy choice extracts $u^* = \\arg\\min_{u \\in Q} D[u]$. Because all edge weights are non-negative ($w(e) \ge 0$), no subsequent relaxation through another node $v \\in Q$ can yield a path to $u^*$ shorter than $D[u^*]$.

#### Priority Queue Min-Heap Complexity
Using Python's standard library `heapq`:
* Building initial heap: $O(|V|)$
* Extract-min operations: $|V| \times O(\\log |V|) = O(|V| \\log |V|)$
* Edge relaxation insertions: at most $|E| \times O(\\log |V|) = O(|E| \\log |V|)$
* **Total Time Complexity:** $\\mathcal{O}((|V| + |E|) \\log |V|)$
* **Total Space Complexity:** $\\mathcal{O}(|V| + |E|)$ to store distance tables, predecessor mapping, and adjacency lists.

Below, we trace the exact step-by-step state transitions of the algorithm for a journey from `DEMO_GATE` to `DEMO_HOSTEL`."""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Step-by-step trace of Dijkstra's algorithm from DEMO_GATE to DEMO_HOSTEL
import heapq

source = "DEMO_GATE"
target = "DEMO_HOSTEL"

print(f"=== DIJKSTRA EXECUTION TRACE: {source} -> {target} ===\\n")

# Data structures
best_cost = {node.id: float("inf") for node in demo_graph.get_nodes()}
best_dist = {node.id: float("inf") for node in demo_graph.get_nodes()}
predecessor = {}
best_cost[source] = 0.0
best_dist[source] = 0.0

# Min-heap: (accumulated_cost, accumulated_dist, current_node_id)
pq = [(0.0, 0.0, source)]
visited = set()
iteration = 0

while pq:
    current_cost, current_dist, current_node = heapq.heappop(pq)
    
    if current_node in visited:
        continue
    visited.add(current_node)
    iteration += 1
    
    print(f"Iteration {iteration}: Extracting Min-Node '{current_node}'")
    print(f"  * Accumulated Cost: {current_cost:.2f} | Accumulated Distance: {current_dist:.2f} m")
    
    if current_node == target:
        print(f"  -> Destination '{target}' reached! Terminating search early.\\n")
        break
        
    for neighbor_id, edge in demo_graph.get_neighbors(current_node, include_blocked=False, accessible_only=False):
        if neighbor_id in visited:
            continue
            
        edge_cost = edge.effective_cost
        edge_dist = edge.distance_m
        tentative_cost = current_cost + edge_cost
        tentative_dist = current_dist + edge_dist
        
        if tentative_cost < best_cost[neighbor_id]:
            old_cost = best_cost[neighbor_id]
            best_cost[neighbor_id] = tentative_cost
            best_dist[neighbor_id] = tentative_dist
            predecessor[neighbor_id] = current_node
            heapq.heappush(pq, (tentative_cost, tentative_dist, neighbor_id))
            print(f"    - Relaxing edge ({current_node} -> {neighbor_id}): Cost updated {old_cost:.1f} -> {tentative_cost:.1f}")

# Reconstruct path
curr = target
path = []
while curr is not None:
    path.append(curr)
    curr = predecessor.get(curr)
path.reverse()

print("Reconstructed Optimal Route:")
print(" -> ".join(path))
print(f"Total Physical Distance: {best_dist[target]:.2f} m")
print(f"Total Routing Cost: {best_cost[target]:.2f}")"""
    ))

    # =========================================================================
    # SECTION 6: ROUTE CALCULATION DEMONSTRATION
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""---
### 6. Route Calculation Demonstration

We execute actual queries through the reusable `dijkstra_shortest_path` library function across representative campus origin-destination pairs.

For each route, we evaluate:
1. Ordered sequence of waypoint nodes.
2. Exact physical distance ($d$).
3. Algorithmic routing cost ($c$).
4. Number of segments (hops).
5. Theoretical walking duration assuming an average pedestrian pace of $v = 1.4\\text{ m/s}$ (approx. $5.04\\text{ km/h}$):
   $$t_{\\text{walk}} = \\frac{d}{1.4}$$"""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Run multiple routing queries and display tabular results
test_queries = [
    ("DEMO_GATE", "DEMO_HOSTEL"),
    ("DEMO_GATE", "DEMO_SPORTS"),
    ("DEMO_ACAD", "DEMO_LIBRARY"),
    ("DEMO_HOSTEL", "DEMO_LIBRARY"),
    ("DEMO_GATE", "DEMO_GATE"),  # Trivial zero-distance case
]

results = []
for orig, dest in test_queries:
    route = dijkstra_shortest_path(demo_graph, orig, dest)
    
    # Walking time estimate (1.4 m/s)
    time_sec = route.total_distance_m / 1.4 if route.total_distance_m > 0 else 0
    time_str = f"{time_sec:.0f} sec" if time_sec < 60 else f"{time_sec/60:.1f} min"
    
    results.append({
        "Origin": orig,
        "Destination": dest,
        "Waypoint Sequence": " -> ".join(route.nodes),
        "Hops": route.hop_count,
        "Distance (m)": f"{route.total_distance_m:.1f}",
        "Routing Cost": f"{route.total_cost:.1f}",
        "Est. Walk Time (at 1.4 m/s)": time_str,
    })

df_route_results = pd.DataFrame(results)
display(df_route_results)"""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Generate structured human-readable directions for DEMO_GATE -> DEMO_HOSTEL
route = dijkstra_shortest_path(demo_graph, "DEMO_GATE", "DEMO_HOSTEL")
directions = generate_route_directions(demo_graph, route)

print(directions.formatted_text())"""
    ))

    # =========================================================================
    # SECTION 7: NETWORKX CROSS-VALIDATION
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""---
### 7. NetworkX Cross-Validation

To ensure that our custom heap-based Dijkstra algorithm produces mathematically optimal shortest paths, we perform empirical dual-solver validation against **NetworkX** (`networkx.multi_source_dijkstra`).

#### Validation Invariants
The validation harness (`campus_routing.algorithms.validator`) verifies:
1. **Identical Termination:** Both solvers return a route or both raise `PathNotFoundError`.
2. **Endpoint Correctness:** The route starts at $s$ and ends at $t$.
3. **Cost Parity within Epsilon:** $|c_{\\text{custom}} - c_{\\text{ref}}| \\le 10^{-4}$.
4. **Hop Legality:** Every traversed edge $(u, v)$ actually exists in the graph, is not blocked, and respects orientation.
5. **Distance Summation Consistency:** Total reported distance equals the sum of individual edge distances."""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Run empirical cross-validation across all 36 (6 x 6) node pairs
all_nodes = [n.id for n in demo_graph.get_nodes()]
validation_records = []
discrepancies = 0

for u in all_nodes:
    for v in all_nodes:
        custom_res, ref_res = validate_route_against_networkx(demo_graph, u, v)
        cost_diff = abs(custom_res.total_cost - ref_res.total_cost)
        dist_diff = abs(custom_res.total_distance_m - ref_res.total_distance_m)
        nodes_identical = (custom_res.nodes == ref_res.nodes)
        
        validation_records.append({
            "Pair": f"{u} -> {v}",
            "Custom Cost": custom_res.total_cost,
            "NetworkX Cost": ref_res.total_cost,
            "Cost Diff": cost_diff,
            "Sequence Match": nodes_identical,
        })

df_validation = pd.DataFrame(validation_records)
print(f"Total Evaluated Node Pairs: {len(df_validation)}")
print(f"Pairs with 100% Cost Parity: {sum(df_validation['Cost Diff'] < 1e-4)} / {len(df_validation)}")
print(f"Pairs with Identical Node Sequences: {sum(df_validation['Sequence Match'])} / {len(df_validation)}")
print("\\nSample Validation Results:")
display(df_validation.head(8))"""
    ))

    # =========================================================================
    # SECTION 8: BLOCKAGES AND ACCESSIBILITY
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""---
### 8. Dynamic Pathway Blockages and Accessibility Filtering

In operational campus navigation, physical paths may become temporarily unavailable due to construction, weather, or event closures.

#### 1. Dynamic Rerouting under Blockage
We demonstrate how an in-memory blockage triggers automatic recalculation of an alternative optimal route."""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Demonstration of dynamic rerouting
test_graph = CampusGraph.from_json(DEMO_GRAPH_PATH)

print("1. Baseline Route: DEMO_GATE -> DEMO_LIBRARY")
route_before = dijkstra_shortest_path(test_graph, "DEMO_GATE", "DEMO_LIBRARY")
print(f"   Path: {' -> '.join(route_before.nodes)}")
print(f"   Distance: {route_before.total_distance_m:.1f} m | Cost: {route_before.total_cost:.1f}")

# Simulate walkway closure between Academic Complex and Library
print("\\n2. Simulating Pathway Blockage: DEMO_ACAD <-> DEMO_LIBRARY ('Pipe Trenching')")
test_graph.set_edge_blocked("DEMO_ACAD", "DEMO_LIBRARY", is_blocked=True, block_reason="Pipe Trenching")

print("\\n3. Recalculated Route under Blockage:")
route_after = dijkstra_shortest_path(test_graph, "DEMO_GATE", "DEMO_LIBRARY")
print(f"   Alternative Path: {' -> '.join(route_after.nodes)}")
print(f"   New Distance: {route_after.total_distance_m:.1f} m | New Cost: {route_after.total_cost:.1f}")
print(f"   Detour Distance Added: +{route_after.total_distance_m - route_before.total_distance_m:.1f} m")"""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Demonstration of unreachable destination when cut-edges are severed
from campus_routing.exceptions import PathNotFoundError

# Block both edges leading to DEMO_SPORTS
test_graph.set_edge_blocked("DEMO_LIBRARY", "DEMO_SPORTS", is_blocked=True, block_reason="Flooding")
test_graph.set_edge_blocked("DEMO_MESS", "DEMO_SPORTS", is_blocked=True, block_reason="Stair Repair")

try:
    dijkstra_shortest_path(test_graph, "DEMO_GATE", "DEMO_SPORTS")
    print("ERROR: Route was unexpectedly found!")
except PathNotFoundError as err:
    print("Expected Exception Caught Successfully:")
    print(f"PathNotFoundError: {err}")"""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Demonstration of accessibility filtering
# Reset graph
acc_graph = CampusGraph.from_json(DEMO_GRAPH_PATH)

print("Query: DEMO_MESS -> DEMO_SPORTS")
route_standard = dijkstra_shortest_path(acc_graph, "DEMO_MESS", "DEMO_SPORTS", accessible_only=False)
print(f"Standard Route (Accessible=False): {' -> '.join(route_standard.nodes)} ({route_standard.total_distance_m:.1f} m, via stairs)")

# Under accessible_only=True, stairs (MESS-SPORTS) and trail (LIBRARY-SPORTS) are prohibited.
# DEMO_SPORTS is completely unreachable without steps or trails.
try:
    dijkstra_shortest_path(acc_graph, "DEMO_MESS", "DEMO_SPORTS", accessible_only=True)
    print("Route found unexpectedly!")
except PathNotFoundError:
    print("Accessible Route (Accessible=True): Destination DEMO_SPORTS is unreachable without stairs or unpaved trails.")
    print("The system correctly prevents directing mobility-impaired pedestrians onto stairs.")"""
    ))

    # =========================================================================
    # SECTION 9: MAP VISUALIZATION
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""---
### 9. Interactive Map Visualization

The cartographic visualization layer is built using **Folium** (a Python wrapper for Leaflet.js).

The system enforces strict visual separation between two modes:
1. **Campus Context Mode (`create_campus_context_map`):**
   * Displays the institutional reference datum marker (`9.754833° N, 76.650099° E`).
   * Displays an informational banner stating that internal pathways remain unsurveyed.
   * **Zero fabricated pathways or fake building pins are drawn.**
2. **Synthetic Demonstration Mode (`create_demonstration_map`):**
   * Displays the isolated 6-node synthetic demonstration graph.
   * Displays an unmistakable red warning banner: `SYNTHETIC DEMONSTRATION — NOT REAL CAMPUS NAVIGATION`.
   * Highlights active routes in royal blue (`#0D47A1`) with green start and red destination markers.
   * Renders blocked pathways as dashed red lines with tooltips explaining the obstruction."""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Generate and export both map types to HTML
demo_map_graph = CampusGraph.from_json(DEMO_GRAPH_PATH)
sample_route = dijkstra_shortest_path(demo_map_graph, "DEMO_GATE", "DEMO_HOSTEL")

# 1. Campus Context Baseline Map
context_map = create_campus_context_map(width="100%", height="500px")
context_html_path = project_root / "data" / "sample_campus_context_map.html"
export_map_to_html(context_map, context_html_path)
print(f"Generated Campus Context Map: {context_html_path} ({context_html_path.stat().st_size:,} bytes)")

# 2. Synthetic Demonstration Map with Route Overlay
demo_map = create_demonstration_map(graph=demo_map_graph, route_result=sample_route, width="100%", height="500px")
demo_html_path = project_root / "data" / "sample_demo_route_map.html"
export_map_to_html(demo_map, demo_html_path)
print(f"Generated Synthetic Demo Route Map: {demo_html_path} ({demo_html_path.stat().st_size:,} bytes)")"""
    ))

    # =========================================================================
    # SECTION 10: AUTOMATED TESTING & PERFORMANCE BENCHMARKING
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""---
### 10. Automated Testing and Performance Micro-Benchmarking

#### Automated Test Suite Status
The software test harness comprises **123 automated test cases** executed via Pytest.
* 24 Database and Persistence tests (schema, foreign keys, cascades, seeding, provenance).
* 46 Graph model and Dijkstra unit tests.
* 20 Visualization and Cartography tests.
* 18 Streamlit application and UI integration tests (`streamlit.testing.v1.AppTest`).
* 15 Core branch coverage and discrepancy validation tests.
* **Overall Statement Coverage:** **92%** across both `campus_routing` and `app` packages.

#### Empirical Benchmarking Experiment
We compare the execution latency of our custom priority-queue Dijkstra implementation against NetworkX's optimized C/Python `multi_source_dijkstra` across 5 representative query pairs with 500 repetitions each."""
    ))

    cells.append(nbf.v4.new_code_cell(
"""# Run reproducible latency benchmarking experiment
benchmark_pairs = [
    ("DEMO_GATE", "DEMO_ACAD"),      # 1 hop
    ("DEMO_GATE", "DEMO_LIBRARY"),   # 2 hops
    ("DEMO_GATE", "DEMO_HOSTEL"),    # 3 hops
    ("DEMO_GATE", "DEMO_SPORTS"),    # 3 hops
    ("DEMO_HOSTEL", "DEMO_SPORTS"),  # 3 hops
]

N_REPS = 500
bench_records = []

for u, v in benchmark_pairs:
    # 1. Benchmark Custom Dijkstra
    t0 = time.perf_counter_ns()
    for _ in range(N_REPS):
        dijkstra_shortest_path(demo_graph, u, v)
    t1 = time.perf_counter_ns()
    custom_avg_us = (t1 - t0) / (N_REPS * 1_000)
    
    # 2. Benchmark NetworkX
    t0 = time.perf_counter_ns()
    for _ in range(N_REPS):
        networkx_shortest_path(demo_graph, u, v)
    t1 = time.perf_counter_ns()
    nx_avg_us = (t1 - t0) / (N_REPS * 1_000)
    
    bench_records.append({
        "Query Pair": f"{u} -> {v}",
        "Custom Dijkstra (µs)": round(custom_avg_us, 2),
        "NetworkX (µs)": round(nx_avg_us, 2),
        "Ratio (Custom / NX)": round(custom_avg_us / nx_avg_us, 2),
    })

df_bench = pd.DataFrame(bench_records)
print(f"=== LATENCY BENCHMARK RESULTS ({N_REPS} iterations per pair) ===")
display(df_bench)

# Plot benchmark comparison
plt.figure(figsize=(9, 4.5), dpi=100)
x = np.arange(len(benchmark_pairs))
width = 0.35

plt.bar(x - width/2, df_bench["Custom Dijkstra (µs)"], width, label="Custom Dijkstra (Python heapq)", color="#1976D2")
plt.bar(x + width/2, df_bench["NetworkX (µs)"], width, label="NetworkX Reference Solver", color="#FF8F00")

plt.ylabel("Execution Time (microseconds - µs)", fontsize=10)
plt.title("Pathfinding Latency: Custom Dijkstra vs. NetworkX (Lower is Faster)", fontsize=11, fontweight="bold")
plt.xticks(x, [p["Query Pair"] for p in bench_records], rotation=15, ha="right")
plt.legend()
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.show()"""
    ))

    # =========================================================================
    # SECTION 11: CONCLUSION AND FUTURE WORK
    # =========================================================================
    cells.append(nbf.v4.new_markdown_cell(
"""---
### 11. Conclusion and Future Work

#### Academic & Engineering Achievements
1. **Decoupled Architecture:** Clean separation between the relational persistence layer (SQLite), graph theory domain models (`CampusGraph`), routing algorithms, cartography (Folium), and presentation UI (Streamlit).
2. **Dual IEEE-754 Precision:** True physical ground distance in metres is tracked independently from algorithmic traversal impedance, avoiding premature rounding errors.
3. **Verified Data Provenance:** Transparent demarcation between official institutional metadata (18 landmarks awaiting survey) and isolated synthetic test datasets (6 nodes, 6 edges).
4. **Comprehensive Test Automation:** 123 tests passing with 92% statement coverage, validated against real Windows runtime environments.

#### Current Limitations
1. **Field Survey Gap:** Production campus database does not yet possess verified pedestrian pathway coordinates.
2. **Straight-Line Segment Assumption:** Step directions compute initial forward great-circle azimuths between endpoints; subtle curved walkways require polyline survey chains.
3. **Static Pedestrian Speed:** Estimated walking times use a theoretical 1.4 m/s standard without modeling elevation exertion or age demographics.

#### Recommended Roadmap (Milestone 6 / Deployment)
1. **On-Site RTK-GPS Field Survey:** Conduct an empirical survey across the 53-acre IIIT Kottayam campus using dual-frequency GNSS receivers to map physical walkway centerlines, stairs, ramps, and building entrance coordinates.
2. **High-Resolution Elevation Profiling:** Incorporate LiDAR or topographical contour elevation data into the cost multiplier function $\\mu_{\\text{slope}}$.
3. **Turn-by-Turn Mobile PWA:** Package the Streamlit routing engine as a responsive Progressive Web App with indoor floor plans and live GPS positioning."""
    ))

    nb.cells = cells

    output_path = project_root / "notebooks" / "campus_navigation_walkthrough.ipynb"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"Generated {output_path} ({output_path.stat().st_size:,} bytes, {len(cells)} cells)")

if __name__ == "__main__":
    create_notebook()
