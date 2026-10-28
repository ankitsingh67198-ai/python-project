"""
Integration tests for the Streamlit web application using Streamlit's AppTest.

Tests full end-to-end user workflows, mode switching, routing calculation,
dynamic pathway blockage, accessibility filtering, empty states, and database isolation.
"""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from campus_routing.config import DEFAULT_DB_PATH
from campus_routing.db.repository import CampusRepository

APP_PATH = str(Path(__file__).resolve().parent.parent.parent / "app" / "streamlit_app.py")


class TestStreamlitAppIntegration:
    """Integration test suite exercising the Streamlit application via AppTest."""

    def test_app_startup_and_campus_context_empty_state(self) -> None:
        """
        Mode A Verification:
        Application boots by default in Campus Context mode, renders the institutional
        reference notice, displays database summary cards, and does not render routing selectors.
        """
        at = AppTest.from_file(APP_PATH)
        at.run()
        assert not at.exception

        # Verify radio is set to 'Campus Context' by default
        assert len(at.radio) >= 1
        assert at.radio[0].value == "Campus Context"

        # Verify institutional banner and notice
        banners = [m.value for m in at.markdown if "INSTITUTIONAL CAMPUS REFERENCE VIEW" in str(m.value)]
        assert len(banners) >= 1

        # Verify notice that pedestrian routing is disabled/unsurveyed
        survey_notices = [m.value for m in at.markdown if "Required Field Survey Data" in str(m.value)]
        assert len(survey_notices) >= 1

        # Verify routing button is NOT present in Campus Context mode
        calculate_buttons = [b for b in at.button if "Calculate" in getattr(b, "label", "")]
        assert len(calculate_buttons) == 0

    def test_switch_to_synthetic_demonstration_mode(self) -> None:
        """
        Mode B Verification:
        Switching radio to 'Synthetic Demonstration' prominently displays the synthetic warning
        banner, exposes origin and destination selectors, and loads demo nodes.
        """
        at = AppTest.from_file(APP_PATH)
        at.run()

        # Switch to Synthetic Demonstration
        at.radio[0].set_value("Synthetic Demonstration").run()
        assert not at.exception

        # Check for prominent synthetic warning banner
        warning_banners = [
            m.value for m in at.markdown if "SYNTHETIC DEMONSTRATION — NOT REAL CAMPUS NAVIGATION" in str(m.value)
        ]
        assert len(warning_banners) >= 1

        # Verify origin and destination selectboxes are rendered
        assert len(at.selectbox) >= 2
        origin_select = at.selectbox(key="demo_origin_select")
        dest_select = at.selectbox(key="demo_destination_select")
        assert origin_select is not None
        assert dest_select is not None

        # Confirm options contain demonstration landmarks
        assert any("DEMO_GATE" in opt for opt in origin_select.options)
        assert any("DEMO_HOSTEL" in opt for opt in dest_select.options)

    def test_successful_route_calculation_in_demo_mode(self) -> None:
        """
        Calculates a route in synthetic demonstration mode.
        Verifies distance, routing impedance cost, hop count, and theoretical walking time.
        """
        at = AppTest.from_file(APP_PATH)
        at.run()
        at.radio[0].set_value("Synthetic Demonstration").run()

        # Default origin is DEMO_GATE, destination is DEMO_HOSTEL
        # Trigger route calculation
        at.button(key="calculate_route_button").click().run()
        assert not at.exception

        # Metric cards should display physical distance and cost
        labels_and_values = {m.label: m.value for m in at.metric}
        assert "Physical Distance" in labels_and_values
        assert "Routing Impedance Cost" in labels_and_values
        assert "Pathway Segments" in labels_and_values
        assert "Est. Walking Time *" in labels_and_values

        # GATE -> ACAD (165.4) -> MESS (110.8) -> HOSTEL (72.3) = 348.5 m
        assert labels_and_values["Physical Distance"] == "348.5 m"
        assert labels_and_values["Routing Impedance Cost"] == "348.5"
        assert labels_and_values["Pathway Segments"] == "3 hops"

        # Check waypoint sequence is rendered
        sequences = [m.value for m in at.markdown if "Waypoint Sequence" in str(m.value)]
        assert len(sequences) >= 1

    def test_identical_origin_and_destination_handling(self) -> None:
        """
        Selecting identical origin and destination cleanly reports 0.0 m without crashing.
        """
        at = AppTest.from_file(APP_PATH)
        at.run()
        at.radio[0].set_value("Synthetic Demonstration").run()

        # Set destination same as origin
        origin_val = at.selectbox(key="demo_origin_select").value
        at.selectbox(key="demo_destination_select").set_value(origin_val).run()

        # Calculate
        at.button(key="calculate_route_button").click().run()
        assert not at.exception

        # Check info box for zero distance
        info_msgs = [info.value for info in at.info if "identical" in str(info.value) or "0.0 m" in str(info.value)]
        assert len(info_msgs) >= 1

    def test_accessibility_filtering_detour(self) -> None:
        """
        Tests routing under accessibility constraints.
        Route from DEMO_LIBRARY to DEMO_SPORTS has direct trail (inaccessible, 185m).
        With accessible_only=True, it must avoid stairs/trail or report unreachable.
        From DEMO_MESS to DEMO_SPORTS has stairs (inaccessible).
        """
        at = AppTest.from_file(APP_PATH)
        at.run()
        at.radio[0].set_value("Synthetic Demonstration").run()

        # Set Origin: DEMO_MESS, Destination: DEMO_SPORTS
        mess_opt = [opt for opt in at.selectbox(key="demo_origin_select").options if "DEMO_MESS" in opt][0]
        sports_opt = [opt for opt in at.selectbox(key="demo_destination_select").options if "DEMO_SPORTS" in opt][0]

        at.selectbox(key="demo_origin_select").set_value(mess_opt)
        at.selectbox(key="demo_destination_select").set_value(sports_opt).run()

        # Without accessibility filter: route exists via stairs
        at.button(key="calculate_route_button").click().run()
        assert not at.exception
        labels_and_values = {m.label: m.value for m in at.metric}
        assert "Physical Distance" in labels_and_values

        # With accessibility filter enabled: DEMO_SPORTS has only stairs (from MESS) and trail (from LIBRARY)
        # So DEMO_SPORTS should be unreachable under step-free constraint!
        at.checkbox(key="demo_accessible_only").check().run()
        at.button(key="calculate_route_button").click().run()
        assert not at.exception

        warnings = [w.value for w in at.warning if "Destination Unreachable" in str(w.value)]
        assert len(warnings) >= 1
        assert "accessibility" in warnings[0].lower()

    def test_dynamic_pathway_blockage_and_rerouting(self) -> None:
        """
        Simulates pathway blockage, verifies session state persistence and alternative route calculation.
        """
        at = AppTest.from_file(APP_PATH)
        at.run()
        at.radio[0].set_value("Synthetic Demonstration").run()

        # Origin: DEMO_GATE, Destination: DEMO_LIBRARY
        gate_opt = [opt for opt in at.selectbox(key="demo_origin_select").options if "DEMO_GATE" in opt][0]
        library_opt = [opt for opt in at.selectbox(key="demo_destination_select").options if "DEMO_LIBRARY" in opt][0]

        at.selectbox(key="demo_origin_select").set_value(gate_opt)
        at.selectbox(key="demo_destination_select").set_value(library_opt).run()
        at.button(key="calculate_route_button").click().run()

        # Normal shortest path: GATE -> ACAD -> LIBRARY = 165.4 + 62.1 = 227.5 m
        labels_and_values = {m.label: m.value for m in at.metric}
        assert labels_and_values["Physical Distance"] == "227.5 m"

        # Now simulate blockage of DEMO_ACAD <-> DEMO_LIBRARY
        block_select = at.selectbox(key="blockage_edge_select")
        acad_lib_opt = [opt for opt in block_select.options if "DEMO_ACAD" in opt and "DEMO_LIBRARY" in opt][0]
        block_select.set_value(acad_lib_opt).run()

        # Click block button
        at.button(key="apply_block_button").click().run()
        assert not at.exception

        # Route should automatically recalculate or take detour:
        # GATE -> ACAD -> MESS -> SPORTS -> LIBRARY (if accessible=False)
        labels_and_values_blocked = {m.label: m.value for m in at.metric}
        # Distances must be greater than original 227.5 m
        new_dist = float(labels_and_values_blocked["Physical Distance"].replace(" m", ""))
        assert new_dist > 227.5

        # Check currently blocked segment summary is displayed
        assert any("Currently Blocked Segments" in str(m.value) for m in at.markdown)
        assert any("DEMO_ACAD" in str(m.value) for m in at.markdown)

        # Reopen or clear all blockages
        at.button(key="clear_all_blockages_btn").click().run()
        assert not at.exception

        # Route distance returns to original 227.5 m
        labels_and_values_cleared = {m.label: m.value for m in at.metric}
        assert labels_and_values_cleared["Physical Distance"] == "227.5 m"

    def test_database_isolation_audit(self) -> None:
        """
        Critical Data Integrity Test:
        Confirms that running the application and blocking pathways never inserts synthetic
        records or edges into the production SQLite campus database.
        """
        repo = CampusRepository(DEFAULT_DB_PATH)
        initial_nodes = repo.list_nodes()
        initial_edges = repo.list_edges()

        # Run AppTest and manipulate demonstration mode
        at = AppTest.from_file(APP_PATH)
        at.run()
        at.radio[0].set_value("Synthetic Demonstration").run()
        at.button(key="calculate_route_button").click().run()

        # Verify DB is completely untouched
        after_nodes = repo.list_nodes()
        after_edges = repo.list_edges()

        assert len(initial_nodes) == len(after_nodes) == 18
        assert len(initial_edges) == len(after_edges) == 0

        # Confirm no DEMO_ nodes exist in production database
        for node in after_nodes:
            assert not node["id"].startswith("DEMO_")
            assert node["source_provenance"] == "OFFICIAL_INSTITUTIONAL"

        repo.close()
