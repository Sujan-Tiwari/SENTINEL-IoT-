import sys
import os
import time
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.join(CURRENT_DIR, "Sentinel-IoT"))
sys.path.insert(0, os.path.join(CURRENT_DIR, "Sentinel-IoT", ".venv", "Lib", "site-packages"))

import sentinel_connection as sc

def test_dynamic_hardware_transitions():
    print("\n[TEST 3] Testing Dynamic State: OFFLINE -> ONLINE -> DISCONNECTED...")
    telemetry_path = os.path.join(CURRENT_DIR, "sentinel_telemetry.json")

    # 3a. Fake fresh packet arrival from active bridge on COM1 (detected host port)
    now_epoch = time.time()
    fresh_telemetry = {
        "device_status": "ONLINE",
        "is_connected": True,
        "port": "COM1",
        "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_seen_epoch": now_epoch,
        "heartbeat_timestamp": now_epoch,
        "networks_found": 8,
        "sd_status": "ACTIVE (LOGGING)",
        "airspace_inventory": [
            {"SSID": "Corp_Secure", "BSSID/MAC": "00:11:22:33:44:55", "Signal": "-52 dBm", "Type": "Infrastructure"}
        ],
        "alerts": []
    }
    
    online_eval = sc.evaluate_hardware_status(
        target_port="COM1",
        heartbeat_timeout=10,
        telemetry_data=fresh_telemetry
    )
    print(f"  -> Fresh packet on active port COM1: status={online_eval['status']}, is_online={online_eval['is_online']}")
    assert online_eval["status"] == "ONLINE", f"Expected ONLINE, got {online_eval['status']}"
    assert online_eval["is_online"] == True, "Hardware must be evaluated as ONLINE"
    print("  [PASS] Fresh valid serial packet successfully sets status to ONLINE.")

    # 3b. Expired Heartbeat (> 10s timeout)
    expired_telemetry = dict(fresh_telemetry)
    expired_telemetry["last_seen_epoch"] = now_epoch - 25.0  # 25 seconds ago
    expired_eval = sc.evaluate_hardware_status(
        target_port="COM1",
        heartbeat_timeout=10,
        telemetry_data=expired_telemetry
    )
    print(f"  -> Expired packet (25s ago > 10s timeout): status={expired_eval['status']}, is_online={expired_eval['is_online']}")
    assert expired_eval["status"] == "CONNECTION LOST", f"Expected CONNECTION LOST, got {expired_eval['status']}"
    assert expired_eval["is_online"] == False, "Expired heartbeat must NOT be online!"
    print("  [PASS] Expired heartbeat successfully triggers CONNECTION LOST.")

    # 3c. Unattached port (COM4)
    unattached_eval = sc.evaluate_hardware_status(
        target_port="COM4",
        heartbeat_timeout=10,
        telemetry_data=fresh_telemetry  # Even if telemetry claimed online, port COM4 is not in host
    )
    print(f"  -> Unattached port COM4: status={unattached_eval['status']}, is_online={unattached_eval['is_online']}")
    assert unattached_eval["status"] == "OFFLINE", f"Expected OFFLINE, got {unattached_eval['status']}"
    assert unattached_eval["is_online"] == False, "Unattached port must NEVER be online!"
    print("  [PASS] Unattached port COM4 strictly marked OFFLINE (fake online prevented).")

    # 3d. Explicit OFFLINE / STOPPED signal from receiver
    offline_telemetry = dict(fresh_telemetry)
    offline_telemetry["device_status"] = "OFFLINE"
    offline_telemetry["receiver_status"] = "STOPPED"
    offline_eval = sc.evaluate_hardware_status(
        target_port="COM1",
        heartbeat_timeout=10,
        telemetry_data=offline_telemetry
    )
    print(f"  -> Receiver reports OFFLINE / STOPPED: status={offline_eval['status']}, is_online={offline_eval['is_online']}")
    assert offline_eval["status"] == "RECEIVER STOPPED"
    assert offline_eval["is_online"] == False
    print("  [PASS] Receiver STOPPED message strictly evaluated as RECEIVER STOPPED.")

    print("\n================================================================")
    print("  HARDWARE CONNECTION STATE MACHINE: 100% VERIFIED!")
    print("================================================================\n")

if __name__ == "__main__":
    test_dynamic_hardware_transitions()

