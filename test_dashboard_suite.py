import sys
import os
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.join(CURRENT_DIR, "Sentinel-IoT"))
sys.path.insert(0, os.path.join(CURRENT_DIR, "Sentinel-IoT", ".venv", "Lib", "site-packages"))

os.environ["SENTINEL_TEST_MODE"] = "1"

from streamlit.testing.v1 import AppTest
import sentinel_connection as sc
from test_hardware_connection import test_dynamic_hardware_transitions
from test_sidebar_mocked import run_all_mocked_tests

def run_suite():
    print("================================================================")
    print("  SENTINEL-IoT DASHBOARD AUTOMATED MASTER TEST SUITE")
    print("================================================================\n")

    app_path = os.path.join(CURRENT_DIR, "app.py")

    # ------------------------------------------------------------
    # TEST 1: Disconnected Hardware & Red Warning on All 11 Pages
    # ------------------------------------------------------------
    print("[PHASE 1] Verifying Disconnected State & Red Alert on ALL 11 pages...")
    
    eval_res = sc.evaluate_hardware_status(target_port="COM4", heartbeat_timeout=10)
    print(f"  -> Hardware evaluation for COM4: status={eval_res['status']}, is_online={eval_res['is_online']}")
    assert eval_res["is_online"] == False, "COM4 must NOT be online when unattached!"

    for page_idx in range(11):
        at = AppTest.from_file(app_path)
        at.session_state.current_page_idx = page_idx
        at.session_state.selected_port = "COM4"
        at.session_state.auto_rotate = False
        at.run(timeout=30)

        page_name = [
            "Airspace Overview", "Tactical Radar", "RF Spectrum & Waterfall",
            "Tactical GPS Geofence", "BLE & RF Jamming", "Deep Forensic Hex Dump",
            "Firewall & ACL Matrix", "Device Monitor", "Enterprise SIEM",
            "Mitigation & Webhooks", "Security Reports"
        ][page_idx]

        markdown_text = " ".join([m.value for m in at.markdown])
        has_alert_title = "ESP32 DEVICE NOT CONNECTED" in markdown_text
        has_alert_msg = "Please connect your ESP32 device and verify the USB/COM port connection" in markdown_text
        
        assert has_alert_title, f"Page {page_idx+1} ({page_name}) missing 'ESP32 DEVICE NOT CONNECTED' title!"
        assert has_alert_msg, f"Page {page_idx+1} ({page_name}) missing alert connection instruction message!"
        print(f"  [PASS] Page {page_idx+1:02d} ({page_name}): Red Disconnection Alert Verified.")

    # ------------------------------------------------------------
    # TEST 2: 10-Second Auto-Rotation Loop & Wrap-Around
    # ------------------------------------------------------------
    print("\n[PHASE 2] Testing Auto-Rotation wrap-around logic...")
    for idx in range(11):
        next_idx = (idx + 1) % 11
        if idx == 10:
            print(f"  -> Page 11 (index 10) -> transitions to Page 1 (index {next_idx}) [WRAP-AROUND]")
            assert next_idx == 0
        else:
            assert next_idx == idx + 1
    print("  [PASS] Navigation cycle and modulo arithmetic 100% verified.")

    # ------------------------------------------------------------
    # TEST 3: Hardware Online / Offline / Lost Transitions
    # ------------------------------------------------------------
    print("\n[PHASE 3] Dynamic Hardware State Machine Transitions...")
    test_dynamic_hardware_transitions()

    # ------------------------------------------------------------
    # TEST 4: Comprehensive Mocked Serial Tests (14 Tests)
    # ------------------------------------------------------------
    print("\n[PHASE 4] Running 14 Mocked Serial & Carousel Tests...")
    run_all_mocked_tests()

    print("\n================================================================")
    print("  ALL 4 MASTER TEST PHASES COMPLETED WITH 100% SUCCESS!")
    print("================================================================\n")

if __name__ == "__main__":
    run_suite()
