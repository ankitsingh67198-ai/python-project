# System Requirements Specification (SRS)
## Smart Campus Navigation System for IIIT Kottayam

**Document Version:** 1.1.0  
**Status:** Draft / Proposed for Review (Pending Milestone 1 Approval)  
**Target Institution:** Indian Institute of Information Technology Kottayam (IIIT Kottayam), Valavoor, Kerala  
**Author:** Senior Python Software Architect & Graph-Algorithm Engineer  
**Date:** October 2026  

---

## 1. Executive Summary & Project Purpose

### 1.1 Project Overview
The **Smart Campus Navigation System for IIIT Kottayam** is an academic software engineering and graph-theoretic application designed to model the physical pedestrian circulation network of IIIT Kottayam's permanent campus in Valavoor, Pala, Kerala. The application computes optimal, minimum-distance walking routes between arbitrary campus landmarks, renders interactive cartographic visualizations with real-time feedback, accounts for dynamic physical obstructions (e.g., maintenance, weather-induced blockages), and provides analytical rigor through dual-solver validation and reproducible Jupyter Notebook experiments.

### 1.2 Core Objectives
1. **Algorithmic Rigor:** Implement a standalone, deterministic Dijkstra's shortest-path algorithm in pure Python utilizing a priority-queue (`heapq`), verified for mathematical optimality and correctness against NetworkX.
2. **Persistent Spatial Domain Model:** Store nodes (landmarks, building access portals, pathway junctions) and edges (walkable segments with measured distances, directionality, accessibility tags, source provenance, and operational statuses) in a normalized SQLite database.
3. **Interactive Visual Interface:** Provide an intuitive Streamlit web application paired with Folium (`streamlit-folium`) for high-fidelity interactive map rendering with dynamic layer controls.
4. **Dynamic Re-Routing:** Enable users to simulate temporary pathway blockages, automatically recalculating the next-shortest alternative route or gracefully signaling disconnected network components.
5. **Academic Reproducibility:** Deliver a comprehensive Jupyter Notebook demonstrating graph construction, algorithm tracing, edge-case evaluations, and benchmark performance, accompanied by an automated test suite (Pytest) and an automated PDF technical report.

---

## 2. Campus Spatial & Domain Analysis (IIIT Kottayam Ground Truth)

### 2.1 Geographic Context & Verified Institutional Facts
All high-level institutional details are grounded in verified official and credible public references:
* **Official Institution:** Indian Institute of Information Technology Kottayam (IIIT Kottayam), an Institute of National Importance established by the Ministry of Education, Government of India, under the IIIT (PPP) Act 2017.
* **Geographic Location:** Valavoor, near Pala, Meenachil Taluk, Kottayam District, Kerala 686635, India.
* **Campus Extent:** 53.5-acre permanent campus set amidst undulating, hilly terrain in the Western Ghats foothills.
* **Regional Geographic Reference Datum (Approximate Campus Centroid):**  
  * Latitude: `9°45′17″ N` (`9.754833° N`)  
  * Longitude: `76°39′00″ E` (`76.650099° E`)  
* **External Primary Access:** Valavoor–Chakkampuzha Road, connecting to the Pala–Thodupuzha Highway (SH 32).
* **OpenStreetMap Reference:** OSM Way ID `1077351803` (`amenity=university`, `name=Indian Institute of Information Technology, Kottayam`).

#### Verified Primary References:
1. IIIT Kottayam Official Website: [https://www.iiitkottayam.ac.in/](https://www.iiitkottayam.ac.in/)
2. IIIT Kottayam Campus & Hostels Overview: [https://www.iiitkottayam.ac.in/#!/hostel](https://www.iiitkottayam.ac.in/#!/hostel)
3. OpenStreetMap Entity (Way 1077351803): [https://www.openstreetmap.org/way/1077351803](https://www.openstreetmap.org/way/1077351803)
4. National Portal & Gazetteer Entry: [https://kottayam.nic.in/](https://kottayam.nic.in/)
5. Wikipedia Reference: [https://en.wikipedia.org/wiki/Indian_Institute_of_Information_Technology,_Kottayam](https://en.wikipedia.org/wiki/Indian_Institute_of_Information_Technology,_Kottayam)

### 2.2 Verified Campus Infrastructure & Landmark Catalog
Based on official institute circulars, hostel documentation, and institute publications, the following major infrastructure zones and landmark identities are verified. **Note that their precise entrance GPS coordinates remain unverified pending an on-site physical survey; coordinates are therefore stored as `NULL` in the production database.**

| Node ID | Landmark Name | Zone / Functional Classification | Ground-Truth Verification Status | Description & Operational Role | Coordinates Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GATE_MAIN` | Main Security Gate | Campus Entry / Perimeter | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Primary entrance checkpoint along the Valavoor access road. | Unsurveyed (`NULL`) |
| `ADMIN_01` | Administrative Block | Administration & Leadership | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Houses Office of the Director, Registrar, Academic Section, Boardroom. | Unsurveyed (`NULL`) |
| `ACAD_01` | Academic Block 1 | Academic / Instruction | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Multi-storey block with smart lecture halls, faculty offices, CS labs. | Unsurveyed (`NULL`) |
| `ACAD_02` | Academic Block 2 | Academic / Specialized Labs | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Expanded academic wing housing advanced AI, IoT, and cybersecurity labs. | Unsurveyed (`NULL`) |
| `LIB_01` | Central Library | Academic Resource | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Technical repositories, digital workstations, and quiet study areas. | Unsurveyed (`NULL`) |
| `HOSTEL_M1`| Meenachil Boys Hostel | Student Residential | Verified ([iiitkottayam.ac.in/#!/hostel](https://www.iiitkottayam.ac.in/#!/hostel)) | Multi-storey boys residence with central hostel administration office. | Unsurveyed (`NULL`) |
| `HOSTEL_M2`| Agasthya Boys Hostel | Student Residential | Verified ([iiitkottayam.ac.in/#!/hostel](https://www.iiitkottayam.ac.in/#!/hostel)) | Senior boys residential accommodation block. | Unsurveyed (`NULL`) |
| `HOSTEL_M3`| Manimala Boys Hostel | Student Residential | Verified ([iiitkottayam.ac.in/#!/hostel](https://www.iiitkottayam.ac.in/#!/hostel)) | Additional boys hostel block. | Unsurveyed (`NULL`) |
| `HOSTEL_F1`| Sahyadri Girls Hostel | Student Residential | Verified ([iiitkottayam.ac.in/#!/hostel](https://www.iiitkottayam.ac.in/#!/hostel)) | Primary secure residential block for female students. | Unsurveyed (`NULL`) |
| `HOSTEL_F2`| Anamudi Girls Hostel | Student Residential | Verified ([iiitkottayam.ac.in/#!/hostel](https://www.iiitkottayam.ac.in/#!/hostel)) | Supplementary girls residential block. | Unsurveyed (`NULL`) |
| `MESS_01`  | Central Dining Complex | Dining & Hospitality | Verified ([iiitkottayam.ac.in/#!/hostel](https://www.iiitkottayam.ac.in/#!/hostel)) | Student Co-operative Mess catering daily meals. | Unsurveyed (`NULL`) |
| `CANTEEN_01`| Campus Cafeteria | Auxiliary Dining | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Day canteen and refreshment kiosk adjacent to academic zone. | Unsurveyed (`NULL`) |
| `OAT_01`   | Open Air Theatre (OAT) | Cultural & Student Activity| Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Stepped outdoor amphitheatre utilized for institutional gatherings. | Unsurveyed (`NULL`) |
| `SPORTS_01`| Sports Ground & Courts | Athletics & Recreation | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Open ground for football/cricket, volleyball courts, and open gym. | Unsurveyed (`NULL`) |
| `GUEST_01` | Institute Guest House | Residential Hospitality | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Accommodates visiting professors, examiners, and institutional guests. | Unsurveyed (`NULL`) |
| `RES_01`   | Faculty & Staff Quarters | Staff Residential | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | Residential quarters for permanent institute employees. | Unsurveyed (`NULL`) |
| `HEALTH_01`| Health Centre / Clinic | Medical Services | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | First-aid dispensary and consulting room for campus community. | Unsurveyed (`NULL`) |
| `UTIL_01`  | Utility Store & ATM | Commercial Amenities | Verified ([iiitkottayam.ac.in](https://www.iiitkottayam.ac.in/)) | General grocery store, stationery store, and bank ATM kiosk. | Unsurveyed (`NULL`) |

### 2.3 Data Provenance Taxonomy & Strict Distinctions
To eliminate ambiguity, all data within the application is classified under four explicit provenance tiers:
1. `OFFICIAL_INSTITUTIONAL`: Verified institutional facts sourced from official IIIT Kottayam circulars, websites, and government gazettes (e.g., landmark identities, building roles).
2. `EXTERNAL_PUBLIC_GEODATA`: Public geographic reference data from OpenStreetMap or satellite registries (e.g., the campus centroid datum `9.754833° N, 76.650099° E`, boundary roadway names).
3. `SYNTHETIC_DEMO`: Explicitly synthetic topological data used strictly for algorithmic verification, unit testing, and UI demonstration. **Synthetic data is kept isolated in separate demonstration fixtures and must NEVER be silently committed to the verified campus database.**
4. `FIELD_SURVEY_VERIFIED`: Empirically gathered on-site measurements with physical GNSS coordinates, measured pathway widths, and slope profiles.

### 2.4 Data Gaps & Explicit Distinctions
* **Verified Facts:** Institutional existence, legal jurisdiction, 53.5-acre property size, landmark names, general campus zones, and regional access road.
* **Unverified Data Gaps:**
  1. Micro-level GPS coordinates of building doorways and portals.
  2. Pedestrian pathway network geometry, including pathway intersections, pavement materials, steps, and widths.
  3. Physical surveyed walking distances along curves and slopes.
* **Bounding Box Clarification:**
  The coordinate bounding box:
  $$\text{Latitude} \in [9.750000, 9.760000], \quad \text{Longitude} \in [76.645000, 76.656000]$$
  is strictly an **engineering sanity envelope** designed to filter out gross input errors (e.g., transposed coordinates or points outside the Valavoor region). It **does not represent the actual cadastral boundary or irregular physical perimeter** of the campus property.
* **Database Routing Network Status:**
  The `campus_metadata` table tracks the operational availability of verified routing data:
  ```
  has_verified_routing_network = false
  ```
  This prevents the application from misleadingly claiming that demonstration routes represent actual campus walking paths.

### 2.5 Ground-Truth Field Data Collection Protocol
To transition the system from demonstration status to field-verified operational navigation, campus researchers will follow this survey protocol:
1. **Hardware & Tooling:** Dual-frequency GNSS/RTK handheld GPS receivers or mobile GIS tools with WAAS/SBAS correction (e.g., QGIS Mobile, GPX Logger, or StreetComplete) capable of sub-meter horizontal accuracy.
2. **Node Surveying:** Record physical latitude, longitude, elevation ($z$), and descriptive metadata at:
   - Primary and secondary building ingress/egress doors.
   - All physical pathway bifurcations and intersections (junction nodes).
   - Abrupt terrain transitions (beginnings and ends of outdoor staircases).
3. **Edge Surveying:**
   - Walk the midline of each pedestrian path recording continuous GPX tracks.
   - Record path attributes: surface type (`asphalt`, `paved_tile`, `concrete`, `gravel`, `dirt`, `stairs`), path width (meters), presence of stairs (`step_count`, `handrail`), slope category (`flat`, `moderate`, `steep`), directionality (`is_directed`), and wheelchair accessibility (`boolean`).
4. **Data Ingestion Pipeline:** Convert collected GPX and GeoJSON datasets into normalized SQLite `nodes` and `edges` tables via `campus_routing.db.seeder`.

---

## 3. Analysis of Complete Scope & Missing Requirements

### 3.1 Junction Nodes vs. User-Selectable Landmark Nodes
* **Gap Identified:** Users navigate between destinations ("Academic Block 1" to "Central Mess"), but physical paths traverse intermediate trail forks and road bends ("Junction 4B").
* **Requirement:** The graph model explicitly separates:
  * `is_landmark = 1`: Human-identifiable POIs that appear in UI origin/destination selectors.
  * `is_landmark = 0`: Pure routing junctions and geometry waypoints, excluded from UI origin/destination selectors.

### 3.2 Dynamic Obstacles & Pathway Blockages
* **Gap Identified:** Real campuses encounter construction closures, weather-related mud/waterlogging, or maintenance scaffolding.
* **Requirement:** Dynamic edge-blocking capability without record deletion. Blocked edges are marked `is_blocked = 1` with a `block_reason` in SQLite, allowing instant re-routing and fallback evaluation.

### 3.3 Graph Disconnection & Unreachable States
* **Gap Identified:** If an edge closure isolates a portion of the campus, pathfinding will fail to find a target.
* **Requirement:** The routing engine must detect unreachable destinations, emit standard domain exceptions (`PathNotFoundError`, `DisconnectedGraphError`), and present actionable UI notifications (e.g., "No walking route available due to 2 blocked pathways").

### 3.4 Separation of Physical Distance and Routing Cost (Impedance)
* **Gap Identified:** IIIT Kottayam's 53-acre Valavoor campus is hilly. A path with a 15% incline or 60 concrete steps requires vastly more physical effort than a flat contour path of identical horizontal distance. Naive implementations conflate physical distance with perceived effort.
* **Requirement:** 
  1. The physical distance along an edge must always be preserved as `distance_m` (in meters).
  2. Any future weighted routing cost (impedance score) considering slope, surface roughness, or user preferences will be computed via a separate algorithmic cost function $C(e)$:
     $$C(e) = \text{cost}(\text{distance\_m}, \text{incline}, \text{surface}, \text{preferences})$$
  3. The routing engine must report the true physical distance traveled separately from any impedance score.

### 3.5 Full-Precision Floating-Point Calculation
* **Gap Identified:** Premature rounding during path relaxation introduces numerical drift and false discrepancies when comparing against NetworkX.
* **Requirement:** Full IEEE 754 double-precision floating-point values are maintained across all internal routing accumulations and comparisons. Rounding (e.g., to 1 decimal place) is strictly reserved for the presentation layer.

### 3.6 Accessibility & Mobility Routing
* **Gap Identified:** Individuals with physical disabilities, injuries, or wheeled equipment cannot navigate staircases.
* **Requirement:** Edges include `is_accessible` flags. The pathfinding service supports `avoid_stairs=True`, dynamically filtering inaccessible edges during Dijkstra traversal.

---

## 4. Functional Requirements (FR)

### FR-01: Graph Topology Modeling
* **FR-01.1:** The system shall model the campus network as a weighted graph $G = (V, E)$, supporting both bidirectional pathways and directed pathways (e.g., one-way turnstiles).
* **FR-01.2:** For undirected pathways, storage shall enforce canonical ordering (`source_id < target_id`) to prevent duplicate reverse records and reverse-direction ambiguity.
* **FR-01.3:** Edge weights shall represent physical ground distance in meters.

### FR-02: SQLite Spatial Data Persistence
* **FR-02.1:** All campus nodes, edges, landmark metadata, active obstructions, and verification statuses shall persist in a standalone SQLite database (`data/campus.db`).
* **FR-02.2:** Foreign keys shall be enforced on all connections (`PRAGMA foreign_keys = ON;`).
* **FR-02.3:** Coordinate pairs must be complete: either both latitude and longitude are `NULL`, or both are valid non-null coordinates within the sanity bounding envelope. Partial coordinates (one `NULL`, one non-null) must be rejected by database constraints.
* **FR-02.4:** Database seeding must be idempotent: repeated executions shall not duplicate records or overwrite user-modified fields.

### FR-03: Custom Dijkstra Routing Engine
* **FR-03.1:** The system shall implement Dijkstra’s algorithm from scratch using `heapq`, achieving $O((|E| + |V|) \log |V|)$ time complexity.
* **FR-03.2:** The custom algorithm shall return:
  1. An ordered sequence of node IDs $[v_{\text{start}}, \dots, v_{\text{end}}]$.
  2. The unrounded, full-precision physical distance in meters.
  3. Intermediate waypoint coordinates for map visualization.
* **FR-03.3:** The custom algorithm shall detect negative edge weights and immediately raise `ValueError`.

### FR-04: NetworkX Dual-Solver Validation
* **FR-04.1:** The core library shall integrate NetworkX (`networkx.Graph` / `networkx.DiGraph`) as an independent ground-truth verification engine.
* **FR-04.2:** The system shall assert that the total path distance calculated by the custom solver equals the NetworkX result within a numerical tolerance of $\epsilon = 10^{-4}$ meters.
* **FR-04.3:** If multiple distinct optimal paths exist, the validation harness shall confirm that the custom solver's path is a valid optimal path of identical total distance.

### FR-05: Dynamic Obstruction & Alternative Routing
* **FR-05.1:** Users/administrators can mark any pathway as blocked without deleting the underlying record.
* **FR-05.2:** Active blocked edges are omitted from pathfinding. If the shortest path is obstructed, the next-shortest valid alternative path is automatically returned.
* **FR-05.3:** If no alternative route exists, `PathNotFoundError` is raised and reported cleanly to the UI.

### FR-06: Interactive Streamlit Web Interface
* **FR-06.1:** Intuitive web UI built with Streamlit.
* **FR-06.2:** Origin and destination dropdowns populated exclusively from verified landmark nodes (`is_landmark = 1`).
* **FR-06.3:** Prevents identical origin/destination selection.
* **FR-06.4:** Dedicated pathway status panel for toggling obstructions.
* **FR-06.5:** Renders distance, estimated walking time (based on $4.5\text{ km/h}$), and turn counts.

### FR-07: Interactive Map Visualization (Folium)
* **FR-07.1:** Embeds interactive Folium map centered on IIIT Kottayam reference datum (`9.7548° N, 76.6501° E`).
* **FR-07.2:** Distinct markers for landmark categories, pathways rendered with high contrast, and blocked paths highlighted in red.
* **FR-07.3:** Computed routes overlaid as prominent polyline with start (green) and destination (red) pins.

### FR-08: Academic Jupyter Notebook
* **FR-08.1:** Demonstrates theoretical formulation, priority-queue tracing, NetworkX comparisons, and edge-case evaluations using shared `campus_routing` modules.

### FR-09: Automated PDF Technical Report Generation
* **FR-09.1:** Automated ReportLab script compiling verification logs, empirical benchmark charts, and academic summaries into `reports/IIITK_Campus_Navigation_Report.pdf`.

### FR-10: Automated Testing Suite
* **FR-10.1:** Comprehensive Pytest suite covering database transactions, constraints, graph construction, Dijkstra pathfinding, and edge cases.
* **FR-10.2:** Code coverage across `campus_routing/` maintained $\ge 90\%$.

---

## 5. Non-Functional Requirements (NFR)

### NFR-01: Performance & Latency
* Shortest-path calculation executes in under $5\text{ ms}$ on campus-scale graphs ($|V| \le 200, |E| \le 500$).
* UI redraw and map re-generation complete within $1.5\text{ s}$.

### NFR-02: Algorithmic Robustness & Fault Tolerance
* Zero uncaught exceptions; graceful error messaging for unreachable or invalid nodes.
* Safe handling of graph cycles and multi-edges.

### NFR-03: Code Architecture & Modularity
* Strict separation of presentation, domain logic, and persistence.
* 100% type-annotated code adhering to PEP 8.

### NFR-04: Portability & Environment Compatibility
* Native Windows 10/11 compatibility using `pathlib.Path`.
* Self-contained SQLite database with zero external server dependencies.

---

## 6. Data Model Specification & Validation Rules

### 6.1 Entity-Relationship (ER) Schema

```
 +-----------------------------+       +------------------------------------+
 |            nodes            |       |               edges                |
 +-----------------------------+       +------------------------------------+
 | PK id (TEXT)                |<---+  | PK id (INTEGER AUTO)               |
 |    name (TEXT)              |    +--| FK source_id (TEXT)                |
 |    category (TEXT)          |    +--| FK target_id (TEXT)                |
 |    latitude (REAL NULLABLE) |       |    distance_m (REAL > 0)           |
 |    longitude(REAL NULLABLE) |       |    is_directed (INT: 0 or 1)       |
 |    elevation_m (REAL NULL)  |       |    surface_type (TEXT)             |
 |    is_landmark (INT: 0 or 1)|       |    is_accessible (INT: 0 or 1)     |
 |    description (TEXT)       |       |    is_blocked (INT: 0 or 1)        |
 |    source_provenance (TEXT) |       |    block_reason (TEXT)             |
 |    verification_status(TEXT)|       |    source_provenance (TEXT)        |
 |    created_at (TIMESTAMP)   |       |    verification_status (TEXT)      |
 +-----------------------------+       +------------------------------------+
           |                                             |
           +---------------------+-----------------------+
                                 |
                     +-----------------------+
                     |    campus_metadata    |
                     +-----------------------+
                     | PK key (TEXT)         |
                     |    value (TEXT)       |
                     |    updated_at (TEXT)  |
                     +-----------------------+
```

### 6.2 Data Integrity & Validation Constraints
1. **Coordinate Completeness Constraint:**
   Either both `latitude` and `longitude` are `NULL`, or both are non-null and within the sanity bounding envelope:
   $$(\text{lat IS NULL} \land \text{lon IS NULL}) \lor (\text{lat} \in [9.750, 9.760] \land \text{lon} \in [76.645, 76.656])$$
2. **Pathway Directionality & Canonical Representation:**
   - For undirected pathways (`is_directed = 0`), storage enforces `source_id < target_id` to eliminate reverse-duplicate ambiguity.
   - For directed pathways (`is_directed = 1`), `source_id != target_id` is enforced.
3. **Physical Distance Positivity:**
   $$\text{distance\_m} > 0.0$$
4. **Idempotent Upsert & State Preservation:**
   Re-running database seeding must never overwrite user modifications (e.g., active pathway blockages).

---

## 7. Unresolved Technical & Domain Questions

The following questions represent genuine research and data-gathering gaps to be resolved in subsequent milestones or through institutional collaboration:
1. **Precise Entrance Coordinates:** What are the exact surveyed coordinates for the primary entrance doors of Academic Block 1, Academic Block 2, Administrative Block, and individual hostel wings?
2. **Ingress/Egress Directionality:** Are there any security turnstiles, one-way gates, or emergency-only exits that operate unidirectionally?
3. **Topographic Elevation Profiles:** What are the exact step counts and elevation changes between the residential hostel zone and the central academic complex?
4. **Covered Pathway Network:** Which pedestrian segments feature permanent monsoon roofs or covered walkways, and should this be an additional routing preference filter?

---

## 8. Acceptance Criteria Framework

### 8.1 Web Application Acceptance Criteria (AC-APP)
* **AC-APP-1:** App launches via `streamlit run app/streamlit_app.py` on Windows PowerShell without deprecation errors.
* **AC-APP-2:** Origin/destination selectors populate only with valid landmark nodes (`is_landmark = 1`).
* **AC-APP-3:** Selecting identical origin and destination triggers an inline user-friendly warning.
* **AC-APP-4:** Interactive map reflects dynamic pathway blockages immediately.

### 8.2 Routing Engine Acceptance Criteria (AC-ROUTER)
* **AC-ROUTER-1:** Custom Dijkstra reproduces identical shortest path physical lengths to NetworkX on 100% of tested pairs.
* **AC-ROUTER-2:** Unrounded full-precision floating-point values are preserved internally.
* **AC-ROUTER-3:** Priority queue operations execute in $O((|E| + |V|) \log |V|)$ time.

### 8.3 Test Suite Acceptance Criteria (AC-TEST)
* **AC-TEST-1:** `pytest` passes 100% of automated tests across database, graph, and routing logic.
* **AC-TEST-2:** Code coverage across `campus_routing/` exceeds 90%.
* **AC-TEST-3:** Constraints for coordinate completeness, foreign keys, and canonical edge representation are fully tested.
