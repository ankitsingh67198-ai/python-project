# Smart Campus Navigation System for IIIT Kottayam

🌐 **Live Demo:** [https://python-project-jscosaaocsrpgkzuj4v8a5.streamlit.app/](https://python-project-jscosaaocsrpgkzuj4v8a5.streamlit.app/)

A Python-based graph-theoretic navigation system engineered to model and calculate walking routes across the permanent campus of the **Indian Institute of Information Technology Kottayam (IIIT Kottayam)** at Valavoor, Pala, Kerala.

---

## 1. Project Overview

The system models campus landmarks, entrances, and pathway junctions as a graph network, computing shortest walking paths via a custom priority-queue Dijkstra implementation cross-validated against NetworkX. The application supports dynamic pathway obstructions, accessibility routing (e.g., avoiding stairs), interactive map visualization via Folium, an interactive Streamlit web application, an academic Jupyter analysis notebook, and a formal PDF technical report.

### Milestone Status: All Milestones Complete (1–5)
- **Milestone 1:** Database Schema, Relational Integrity & Persistence Layer. (Complete — 24 tests)
- **Milestone 2:** Core Graph Models & Dual Dijkstra Routing Engine. (Complete — 46 tests)
- **Milestone 3:** Interactive Cartography & Visual Overlay Module. (Complete — 20 tests)
- **Milestone 4:** Streamlit Web Application & Interactive UI. (Complete — 18 tests)
- **Milestone 5:** Academic Jupyter Notebook & PDF Report. (Complete — 15 tests, 123 tests total, 92% coverage)

---

## 2. Environment Setup (Windows PowerShell)

All commands should be executed from the project root using the project-local virtual environment (`.venv`):

### 1. Activate or Reference the Virtual Environment
```powershell
# Direct invocation (recommended):
.\.venv\Scripts\python.exe <command>

# Or activate the shell session:
.\.venv\Scripts\Activate.ps1
```

### 2. Run the Full Test Suite
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

### 3. Run Statement Coverage Analysis
```powershell
.\.venv\Scripts\python.exe -m pytest --cov=campus_routing --cov=app --cov-report=term-missing
```

---

## 3. Launching the Interactive Streamlit Web Application

To launch the web application locally:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

Open `http://localhost:8501` in any desktop browser.

### Application Modes:
* **Mode A: Campus Context Mode:** Shows institutional reference datum (`9.754833° N, 76.650099° E`, Valavoor, Pala) and live SQLite landmark metadata. Real-world pedestrian routing is **explicitly disabled** with an empty state explaining the required field survey steps.
* **Mode B: Synthetic Demonstration Mode:** Loads an isolated 6-node synthetic graph (`data/demonstration_graph.json`) with an unmistakable red warning banner. Supports shortest-path calculation, in-memory pathway blocking with instant rerouting, and step-free accessibility filtering.

---

## 4. Academic Jupyter Notebook

The project includes an executed, self-contained computational notebook:

* **Location:** [`notebooks/campus_navigation_walkthrough.ipynb`](file:///w:/Downloads/Smart-Campus-Navigation/notebooks/campus_navigation_walkthrough.ipynb)
* **Contents (11 Sections):** Problem statement, software architecture, dataset inspection, graph theory foundations, Dijkstra algorithm trace, route demonstration, NetworkX cross-validation, dynamic blockages, Folium cartography, performance micro-benchmarking, and future roadmap.

### Opening the Notebook Interactively
```powershell
.\.venv\Scripts\python.exe -m jupyter lab notebooks/campus_navigation_walkthrough.ipynb
# or
.\.venv\Scripts\python.exe -m jupyter notebook notebooks/campus_navigation_walkthrough.ipynb
```

### Re-executing the Notebook In-Place
To re-run all cells from top to bottom and refresh outputs, figures, and benchmark measurements:
```powershell
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=120 notebooks/campus_navigation_walkthrough.ipynb
```

---

## 5. Generating the Formal PDF Technical Report

The repository includes a maintainable Python script that typesets a publication-quality academic report using ReportLab:

* **Source Script:** [`reports/generate_pdf_report.py`](file:///w:/Downloads/Smart-Campus-Navigation/reports/generate_pdf_report.py)
* **Output Document:** [`reports/IIITK_Campus_Navigation_Report.pdf`](file:///w:/Downloads/Smart-Campus-Navigation/reports/IIITK_Campus_Navigation_Report.pdf)

### Re-generating the PDF Report
```powershell
.\.venv\Scripts\python.exe reports/generate_pdf_report.py
```

The generated report contains all 18 required academic sections, formal mathematical derivations, dual-solver validation tables, performance benchmarks, and interface screenshots.

---

## 6. Directory Layout

```
Smart-Campus-Navigation/
├── app/                        # Streamlit web application layer
│   ├── components/             # Reusable modular UI components
│   │   ├── blockage_panel.py   # Dynamic walkway obstruction controls (Demo mode)
│   │   ├── metrics_card.py     # Accurate distance, impedance & walking time metrics
│   │   ├── sidebar.py          # Mode selector, origin/destination & preferences
│   │   └── __init__.py
│   ├── streamlit_app.py        # Streamlit layout orchestration & state management
│   └── __init__.py
├── campus_routing/             # Core reusable domain library
│   ├── algorithms/             # Dijkstra, NetworkX solver, cross-validator
│   │   ├── dijkstra.py         # Priority-queue Dijkstra shortest-path engine
│   │   ├── networkx_solver.py  # Reference NetworkX solver
│   │   └── validator.py        # Dual-solver empirical validation harness
│   ├── db/                     # SQLite persistence layer
│   │   ├── connection.py       # Connection management, WAL mode, transaction context
│   │   ├── repository.py       # CRUD operations, domain validation, metadata
│   │   ├── schema.sql          # DDL tables, foreign keys, check constraints
│   │   └── seeder.py           # Idempotent landmark seeding
│   ├── models/                 # Domain entity models
│   │   ├── edge.py             # Directed/undirected Edge model
│   │   ├── graph.py            # In-memory CampusGraph model
│   │   └── node.py             # Spatial Node model
│   ├── visualization/          # Cartographic Folium map builders
│   │   ├── directions.py       # Approximate bearing and step direction generator
│   │   ├── map_builder.py      # Campus context and demo map builders
│   │   └── styles.py           # Color palette, icons, polyline styling, legend
│   ├── config.py               # Pathlib filesystem paths and geographic constants
│   ├── exceptions.py           # Domain exceptions hierarchy
│   └── __init__.py
├── data/                       # Datasets & persistent SQLite DB
│   ├── campus.db               # SQLite database file (18 verified landmarks)
│   ├── seed_landmarks.json     # Verified institutional landmarks catalog
│   └── demonstration_graph.json# Isolated synthetic demonstration graph
├── docs/                       # Formal specifications & milestone completion reports
│   ├── REQUIREMENTS.md         # System Requirements Specification (SRS)
│   ├── PROJECT_PLAN.md         # Architecture & Project Plan
│   ├── milestone3_completion_report.md
│   ├── milestone4_completion_report.md
│   └── milestone5_completion_report.md
├── notebooks/                  # Academic computational notebook
│   ├── build_notebook.py       # Notebook builder script
│   └── campus_navigation_walkthrough.ipynb # Executed Jupyter notebook (11 sections)
├── reports/                    # Formal technical PDF report
│   ├── generate_pdf_report.py  # ReportLab PDF compilation script
│   ├── IIITK_Campus_Navigation_Report.pdf  # Compiled 10-page academic report
│   ├── screenshot_mode_a_context.png
│   ├── screenshot_mode_b_route.png
│   └── screenshot_mode_b_blockage.png
├── tests/                      # Automated test suite (123 passing tests, 92% coverage)
│   ├── conftest.py             # Shared pytest fixtures
│   ├── integration/            # Dual solver & Streamlit AppTest integration tests
│   │   ├── test_dual_solver.py
│   │   ├── test_visualization_integration.py
│   │   └── test_streamlit_app.py
│   └── unit/                   # Unit test suites
│       ├── test_app.py
│       ├── test_core_coverage.py
│       ├── test_dijkstra.py
│       ├── test_models.py
│       ├── test_repository.py
│       └── test_visualization.py
├── pyproject.toml              # Build system & pytest configuration
├── requirements.txt            # Project dependencies
├── .gitignore
└── README.md
```

---

## 7. Verification Metrics Summary

* **Total Automated Tests:** 123 tests (100% pass rate)
* **Core Library Coverage (`campus_routing`):** 92%
* **Application Package Coverage (`app`):** 92%
* **Execution Time:** ~8.4 seconds
* **Verified Database State:** 18 institutional landmarks, 0 verified footways, zero fabricated routes.
* **Demonstration Network:** 6 synthetic nodes, 6 synthetic edges, 100% cost parity with NetworkX.
* **Notebook Execution:** 13/13 code cells executed without error, 208 KB output payload.
* **PDF Report:** 10 pages, 561 KB, covers all 18 academic sections.
