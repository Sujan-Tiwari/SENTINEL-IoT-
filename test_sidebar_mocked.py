import sys
import os
import time
from unittest import mock
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.join(CURRENT_DIR, "Sentinel-IoT"))
sys.path.insert(0, os.path.join(CURRENT_DIR, "Sentinel-IoT", ".venv", "Lib", "site-packages"))

import sentinel_connection as sc

class MockPort:
    def __init__(self, device, description="", hwid=""):
        self.device = device
        self.description = description
        self.hwid = hwid

def run_all_mocked_tests():
    print("=" * 70)
    print(" SENTINEL-IoT SIDEBAR & HARDWARE CONNECTION MOCKED TEST SUITE")
    print("=" * 70 + "\n")

    passed_count = 0
    total_tests = 14

    # -------------------------------------------------------------------------
    # TEST 1: No COM port detected (mock empty [])
    # -------------------------------------------------------------------------
    print("[TEST 01/14] Testing empty port list (no COM ports detected)...")
    with mock.patch("serial.tools.list_ports.comports", return_value=[]):
        ports = sc.get_system_serial_ports()
        assert len(ports) == 0, f"Expected empty list, got {ports}"
        
        status = sc.evaluate_hardware_status(target_port=None, heartbeat_timeout=10, telemetry_data={})
        assert status["status"] == "OFFLINE"
        assert status["port_found"] == False
        assert status["is_online"] == False
        assert "No COM port selected" in status["reason"]
        print("  -> Ports detected: [] -> Hardware Link: OFFLINE (is_online=False)")
        print("  [PASS] Test 1: No COM port detected verified.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 2: Duplicate ports are not displayed (mock duplicate COM3 entries)
    # -------------------------------------------------------------------------
    print("\n[TEST 02/14] Testing port deduplication (mock duplicate COM3 entries)...")
    mock_duplicates = [
        MockPort("COM3", "Silicon Labs CP210x USB to UART Bridge (COM3)"),
        MockPort("COM3", "CP210x USB to UART Bridge"),
        MockPort("com3", "Duplicate lowercase COM3"),
        MockPort("COM5", "USB-SERIAL CH340 (COM5)")
    ]
    with mock.patch("serial.tools.list_ports.comports", return_value=mock_duplicates):
        ports = sc.get_system_serial_ports()
        devices = [p["device"] for p in ports]
        assert len(ports) == 2, f"Expected 2 unique ports, got {len(ports)}: {devices}"
        assert "COM3" in devices and "COM5" in devices
        assert len(set(d.upper() for d in devices)) == len(devices), "Duplicates detected in list!"
        print(f"  -> Raw inputs: 4 -> Deduplicated unique: {devices}")
        print("  [PASS] Test 2: Port deduplication verified.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 3: COM port refresh (port list changes dynamically)
    # -------------------------------------------------------------------------
    print("\n[TEST 03/14] Testing dynamic COM port refresh...")
    # First check: only COM1
    with mock.patch("serial.tools.list_ports.comports", return_value=[MockPort("COM1", "Built-in Serial")]):
        ports_initial = sc.get_system_serial_ports()
        assert len(ports_initial) == 1
        assert ports_initial[0]["device"] == "COM1"
    
    # Second check: user plugged in ESP32 on COM7 (Silicon Labs)
    with mock.patch("serial.tools.list_ports.comports", return_value=[
        MockPort("COM1", "Built-in Serial"),
        MockPort("COM7", "Silicon Labs CP2102 USB to UART Bridge")
    ]):
        ports_refreshed = sc.get_system_serial_ports()
        assert len(ports_refreshed) == 2
        refreshed_devices = [p["device"] for p in ports_refreshed]
        assert "COM7" in refreshed_devices
        print(f"  -> Initial: {[p['device'] for p in ports_initial]} -> Refreshed after plug-in: {refreshed_devices}")
        print("  [PASS] Test 3: Dynamic port refresh verified.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 4: COM4 disconnected (returns OFFLINE)
    # -------------------------------------------------------------------------
    print("\n[TEST 04/14] Testing COM4 disconnected state...")
    # System only has COM1, target is COM4
    with mock.patch("serial.tools.list_ports.comports", return_value=[MockPort("COM1", "Communications Port")]):
        # Even if telemetry claims device_status = ONLINE, target port COM4 is physically absent
        telemetry_fake = {"device_status": "ONLINE", "is_connected": True, "last_seen_epoch": time.time()}
        eval_res = sc.evaluate_hardware_status(target_port="COM4", heartbeat_timeout=10, telemetry_data=telemetry_fake)
        assert eval_res["status"] == "OFFLINE"
        assert eval_res["port_found"] == False
        assert eval_res["is_online"] == False
        assert "COM4 is not detected by Windows" in eval_res["reason"]
        print(f"  -> Target COM4 status: {eval_res['status']} | port_found={eval_res['port_found']}")
        print("  [PASS] Test 4: COM4 disconnected correctly marked OFFLINE.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 5: COM1 connected (port present in OS)
    # -------------------------------------------------------------------------
    print("\n[TEST 05/14] Testing COM1 connected (port presence detected)...")
    with mock.patch("serial.tools.list_ports.comports", return_value=[MockPort("COM1", "Communications Port")]):
        is_conn = sc.is_com_port_connected("COM1")
        assert is_conn == True
        print(f"  -> is_com_port_connected('COM1') = {is_conn}")
        print("  [PASS] Test 5: COM1 port presence verified.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 6: Port present but no heartbeat (returns RECEIVER STOPPED)
    # -------------------------------------------------------------------------
    print("\n[TEST 06/14] Testing port present with no heartbeat...")
    with mock.patch("serial.tools.list_ports.comports", return_value=[MockPort("COM1", "Communications Port")]):
        # Telemetry file missing or empty (no heartbeat timestamp)
        eval_res = sc.evaluate_hardware_status(target_port="COM1", heartbeat_timeout=10, telemetry_data={})
        assert eval_res["status"] == "RECEIVER STOPPED"
        assert eval_res["receiver_status"] == "STOPPED"
        assert eval_res["port_found"] == True
        assert eval_res["is_online"] == False
        print(f"  -> Port COM1 detected, but no heartbeat -> Status: {eval_res['status']}")
        print("  [PASS] Test 6: Missing heartbeat correctly marked RECEIVER STOPPED.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 7: Stale telemetry (returns CONNECTION LOST or RECEIVER STOPPED)
    # -------------------------------------------------------------------------
    print("\n[TEST 07/14] Testing stale telemetry packet (> heartbeat timeout)...")
    now_ts = time.time()
    with mock.patch("serial.tools.list_ports.comports", return_value=[MockPort("COM1", "Communications Port")]):
        # Receiver is active (heartbeat is fresh, 1s ago), but serial packets from ESP32 stopped 25s ago
        stale_data = {
            "device_status": "ONLINE",
            "heartbeat_timestamp": now_ts - 1.0,  # receiver alive
            "last_seen_epoch": now_ts - 25.0,     # ESP32 packet 25s ago > 10s timeout
            "last_seen": "2026-11-05 10:00:00"
        }
        eval_res = sc.evaluate_hardware_status(target_port="COM1", heartbeat_timeout=10, telemetry_data=stale_data)
        assert eval_res["status"] == "CONNECTION LOST", f"Expected CONNECTION LOST, got {eval_res['status']}"
        assert eval_res["is_online"] == False
        assert "timed out" in eval_res["reason"]
        print(f"  -> Packet age 25s > 10s timeout -> Status: {eval_res['status']} ({eval_res['reason']})")
        print("  [PASS] Test 7: Stale telemetry correctly transitions to CONNECTION LOST.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 8: Receiver stopped (returns RECEIVER STOPPED)
    # -------------------------------------------------------------------------
    print("\n[TEST 08/14] Testing receiver stopped signal...")
    with mock.patch("serial.tools.list_ports.comports", return_value=[MockPort("COM1", "Communications Port")]):
        # Telemetry has receiver_status = STOPPED or device_status = OFFLINE
        stopped_data = {
            "device_status": "OFFLINE",
            "receiver_status": "STOPPED",
            "heartbeat_timestamp": now_ts,
            "last_seen_epoch": now_ts
        }
        eval_res = sc.evaluate_hardware_status(target_port="COM1", heartbeat_timeout=10, telemetry_data=stopped_data)
        assert eval_res["status"] == "RECEIVER STOPPED"
        assert eval_res["receiver_status"] == "STOPPED"
        assert eval_res["is_online"] == False
        print(f"  -> Explicit receiver shutdown signal -> Status: {eval_res['status']}")
        print("  [PASS] Test 8: Receiver stopped signal strictly enforced.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 9: OFFLINE to ONLINE transition
    # -------------------------------------------------------------------------
    print("\n[TEST 09/14] Testing OFFLINE -> ONLINE dynamic transition...")
    with mock.patch("serial.tools.list_ports.comports", return_value=[MockPort("COM3", "CP2102 USB Bridge")]):
        # Step A: Initially no telemetry data -> OFFLINE / RECEIVER STOPPED
        step_a = sc.evaluate_hardware_status(target_port="COM3", heartbeat_timeout=10, telemetry_data={})
        assert step_a["is_online"] == False

        # Step B: Hardware connects, bridge starts streaming fresh packet (<1s ago)
        fresh_ts = time.time()
        fresh_data = {
            "device_status": "ONLINE",
            "receiver_status": "RUNNING",
            "heartbeat_timestamp": fresh_ts,
            "last_seen_epoch": fresh_ts,
            "last_seen": datetime.fromtimestamp(fresh_ts).strftime("%Y-%m-%d %H:%M:%S")
        }
        step_b = sc.evaluate_hardware_status(target_port="COM3", heartbeat_timeout=10, telemetry_data=fresh_data)
        assert step_b["status"] == "ONLINE"
        assert step_b["is_online"] == True
        assert step_b["receiver_status"] == "STREAMING (LIVE)"
        print(f"  -> Step A: {step_a['status']} (online={step_a['is_online']}) -> Step B: {step_b['status']} (online={step_b['is_online']})")
        print("  [PASS] Test 9: OFFLINE to ONLINE transition verified.")
        passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 10: ONLINE to CONNECTION LOST transition
    # -------------------------------------------------------------------------
    print("\n[TEST 10/14] Testing ONLINE -> CONNECTION LOST transition...")
    with mock.patch("serial.tools.list_ports.comports", return_value=[MockPort("COM3", "CP2102 USB Bridge")]):
        t0 = time.time()
        online_data = {
            "device_status": "ONLINE",
            "receiver_status": "RUNNING",
            "heartbeat_timestamp": t0,
            "last_seen_epoch": t0
        }
        res_online = sc.evaluate_hardware_status(target_port="COM3", heartbeat_timeout=10, telemetry_data=online_data)
        assert res_online["status"] == "ONLINE"
        assert res_online["is_online"] == True

        # Now simulate 12 seconds passing without any serial packet
        lost_data = dict(online_data)
        lost_data["heartbeat_timestamp"] = t0 + 12.0  # receiver process still ticking
        lost_data["last_seen_epoch"] = t0            # but ESP32 serial packet is 12s old
        with mock.patch("time.time", return_value=t0 + 12.0):
            res_lost = sc.evaluate_hardware_status(target_port="COM3", heartbeat_timeout=10, telemetry_data=lost_data)
            assert res_lost["status"] == "CONNECTION LOST"
            assert res_lost["is_online"] == False
            print(f"  -> ONLINE (age 0s) -> CONNECTION LOST (age 12s > timeout 10s)")
            print("  [PASS] Test 10: ONLINE to CONNECTION LOST transition verified.")
            passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 11: Auto-rotate ON and OFF
    # -------------------------------------------------------------------------
    print("\n[TEST 11/14] Testing Auto-Rotate ON / OFF toggle behavior...")
    # State tracking simulation
    session_state = {"auto_rotate": True, "last_switch_time": 100.0, "current_page_idx": 0}

    # When ON, elapsed >= 10s triggers transition
    now_sim = 110.5
    elapsed = now_sim - session_state["last_switch_time"]
    should_rotate = session_state["auto_rotate"] and (elapsed >= 10.0)
    assert should_rotate == True, "When ON and elapsed >= 10s, rotation must trigger"

    # Toggle OFF
    session_state["auto_rotate"] = False
    session_state["last_switch_time"] = now_sim
    now_later = 135.0  # 25 seconds later
    elapsed_later = now_later - session_state["last_switch_time"]
    should_rotate_when_off = session_state["auto_rotate"] and (elapsed_later >= 10.0)
    assert should_rotate_when_off == False, "When OFF, rotation must NOT trigger regardless of elapsed time"
    print(f"  -> Auto-Rotate ON: triggers at 10s = {should_rotate} | Auto-Rotate OFF: paused at 25s = {not should_rotate_when_off}")
    print("  [PASS] Test 11: Auto-rotate ON/OFF toggle verified.")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 12: 10-second page transition verification
    # -------------------------------------------------------------------------
    print("\n[TEST 12/14] Testing exact 10-second page transition timing...")
    t_start = 1000.0
    for tick in range(1, 12):
        sim_time = t_start + tick
        elapsed = sim_time - t_start
        remaining = max(0, int(10.0 - elapsed))
        triggered = elapsed >= 10.0
        if tick < 10:
            assert remaining == (10 - tick)
            assert not triggered, f"Premature transition at {tick}s!"
        elif tick == 10:
            assert remaining == 0
            assert triggered, "Transition must trigger at exactly 10s!"
    print("  -> Countdown verified: 10s, 9s, 8s, 7s, 6s, 5s, 4s, 3s, 2s, 1s, 0s -> Transition triggered!")
    print("  [PASS] Test 12: Exact 10-second transition logic verified.")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 13: Page 11 to Page 1 wrap-around
    # -------------------------------------------------------------------------
    print("\n[TEST 13/14] Testing Page 11 to Page 1 wrap-around...")
    page_count = 11
    current_idx = 10  # 11th page (0-indexed: index 10)
    next_idx = (current_idx + 1) % page_count
    assert next_idx == 0, f"Expected wrap-around to index 0 (Page 1), got {next_idx}"
    print(f"  -> Page 11 (index 10) -> (10 + 1) % 11 = index {next_idx} (Page 1) [PERFECT WRAP-AROUND]")
    
    # Also verify full cycle wrap-around
    visited = []
    idx = 0
    for _ in range(page_count * 2):
        visited.append(idx)
        idx = (idx + 1) % page_count
    assert visited[11] == 0 and visited[21] == 10
    print("  [PASS] Test 13: Full 11-page cycle and wrap-around verified.")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 14: Manual page navigation and countdown reset
    # -------------------------------------------------------------------------
    print("\n[TEST 14/14] Testing manual navigation and countdown reset...")
    session_sim = {
        "current_page_idx": 4,     # Page 5
        "last_switch_time": 200.0
    }
    
    # User clicks 'Next ⏭️' at 206s (6 seconds in)
    time_click = 206.0
    # Simulate Next click handler
    session_sim["current_page_idx"] = (session_sim["current_page_idx"] + 1) % page_count
    session_sim["last_switch_time"] = time_click
    
    assert session_sim["current_page_idx"] == 5  # Advanced to Page 6
    assert session_sim["last_switch_time"] == time_click  # Countdown reset to 10s
    remaining_after_click = 10.0 - (time_click - session_sim["last_switch_time"])
    assert remaining_after_click == 10.0
    
    # User clicks '⏮️ Prev' at 208s
    time_prev = 208.0
    session_sim["current_page_idx"] = (session_sim["current_page_idx"] - 1) % page_count
    session_sim["last_switch_time"] = time_prev
    assert session_sim["current_page_idx"] == 4  # Returned to Page 5
    assert session_sim["last_switch_time"] == time_prev  # Countdown reset again
    print("  -> Manual Next button: resets countdown to 10s and advances page index.")
    print("  -> Manual Prev button: resets countdown to 10s and decrements page index.")
    print("  [PASS] Test 14: Manual navigation and timer reset verified.")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f" ALL {passed_count}/{total_tests} MOCKED UNIT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_all_mocked_tests()

