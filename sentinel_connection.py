import os
import json
import time
from datetime import datetime
try:
    import serial.tools.list_ports as list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    list_ports = None
    SERIAL_AVAILABLE = False

TELEMETRY_FILENAME = "sentinel_telemetry.json"
DEFAULT_HEARTBEAT_TIMEOUT = 90  # seconds (matches ESP32 ~60s periodic scan interval)

def get_base_dir() -> str:
    """Returns absolute path to the directory containing app.py and telemetry json."""
    return os.path.dirname(os.path.abspath(__file__))

def get_telemetry_file_path() -> str:
    """Finds telemetry JSON path relative to current or base directory."""
    base = get_base_dir()
    cand1 = os.path.join(base, TELEMETRY_FILENAME)
    if os.path.exists(cand1):
        return cand1
    cand2 = os.path.join(os.getcwd(), TELEMETRY_FILENAME)
    if os.path.exists(cand2):
        return cand2
    return cand1

def get_system_serial_ports() -> list:
    """
    Returns unique list of active system COM ports with hardware descriptions.
    Deduplicates ports and never injects hardcoded fallback ports.
    """
    ports = []
    seen = set()
    try:
        for p in list_ports.comports():
            dev = (p.device or "").strip()
            if not dev:
                continue
            dev_upper = dev.upper()
            if dev_upper in seen:
                continue
            seen.add(dev_upper)
            
            desc = (p.description or "").strip()
            # Clean up redundant port prefix if description repeats "COM1 (COM1)"
            if desc.startswith(dev) and len(desc) > len(dev):
                desc = desc[len(dev):].strip(" -:()")
            if not desc:
                desc = "Serial Device"

            ports.append({
                "device": dev,
                "description": desc,
                "hwid": getattr(p, "hwid", "")
            })
    except Exception:
        pass

    # Sort numerically (e.g. COM1, COM2, COM10)
    def port_sort_key(item):
        d = item["device"].upper()
        if d.startswith("COM") and d[3:].isdigit():
            return (0, int(d[3:]))
        return (1, d)

    ports.sort(key=port_sort_key)
    return ports

def is_com_port_connected(target_port: str) -> bool:
    """Checks whether the specified COM port exists in the OS device list."""
    if not target_port:
        return False
    target = target_port.strip().upper()
    try:
        for p in list_ports.comports():
            if (p.device or "").strip().upper() == target:
                return True
    except Exception:
        pass
    return False

def load_telemetry_file(file_path: str = None) -> dict:
    """Safely loads telemetry JSON with error handling against partial file writes."""
    path = file_path or get_telemetry_file_path()
    if not os.path.exists(path):
        return {}
    
    # Try reading file safely with a short retry in case of write contention
    for _ in range(3):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    time.sleep(0.05)
                    continue
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, OSError):
            time.sleep(0.05)
            continue
        except Exception:
            break
    return {}

def parse_last_seen_epoch(last_seen_val, file_mtime: float = None) -> float:
    """Parses last seen into unix epoch timestamp."""
    if isinstance(last_seen_val, (int, float)) and last_seen_val > 0:
        return float(last_seen_val)
    
    if isinstance(last_seen_val, str) and last_seen_val.strip():
        val = last_seen_val.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                dt = datetime.strptime(val, fmt)
                return dt.timestamp()
            except ValueError:
                continue
    
    if file_mtime and file_mtime > 0:
        return file_mtime
    return 0.0

def evaluate_hardware_status(
    target_port: str = None,
    heartbeat_timeout: int = DEFAULT_HEARTBEAT_TIMEOUT,
    telemetry_data: dict = None,
    file_path: str = None,
    available_ports: list = None
) -> dict:
    """
    Evaluates connection status according to the 4 strict SOC hardware states:
    1. ONLINE: Port exists, receiver running, fresh valid serial telemetry (< timeout).
    2. OFFLINE: Port not detected by Windows, or no port selected.
    3. CONNECTION LOST: Port detected & receiver active, but no serial data (< timeout).
    4. RECEIVER STOPPED: Port detected, but receiver bridge is stopped or no heartbeats.
    """
    now = time.time()
    t_path = file_path or get_telemetry_file_path()
    file_exists = os.path.exists(t_path)
    file_mtime = os.path.getmtime(t_path) if file_exists else 0.0

    raw_data = telemetry_data if telemetry_data is not None else load_telemetry_file(t_path)
    if available_ports is None:
        available_ports = get_system_serial_ports()

    # Determine port presence
    cleaned_port = (target_port or "").strip()
    if not cleaned_port or cleaned_port == "NO COM PORT DETECTED":
        port_found = False
        display_port = "NONE"
    else:
        display_port = cleaned_port
        port_found = any(p["device"].upper() == cleaned_port.upper() for p in available_ports)

    # Extract receiver heartbeat & serial telemetry timestamps
    last_seen_epoch = 0.0
    if "last_seen_epoch" in raw_data and raw_data["last_seen_epoch"]:
        try:
            last_seen_epoch = float(raw_data["last_seen_epoch"])
        except (ValueError, TypeError):
            pass
    if last_seen_epoch <= 0:
        last_seen_epoch = parse_last_seen_epoch(raw_data.get("last_seen"), file_mtime)

    heartbeat_epoch = 0.0
    if "heartbeat_timestamp" in raw_data and raw_data["heartbeat_timestamp"]:
        try:
            heartbeat_epoch = float(raw_data["heartbeat_timestamp"])
        except (ValueError, TypeError):
            pass
    if heartbeat_epoch <= 0 and file_exists:
        heartbeat_epoch = file_mtime

    # Calculate age in seconds
    last_com_age = (now - last_seen_epoch) if last_seen_epoch > 0 else 999999.0
    heartbeat_age = (now - heartbeat_epoch) if heartbeat_epoch > 0 else 999999.0

    last_seen_str = raw_data.get("last_seen")
    if not last_seen_str and last_seen_epoch > 0:
        last_seen_str = datetime.fromtimestamp(last_seen_epoch).strftime("%Y-%m-%d %H:%M:%S")
    if not last_seen_str:
        last_seen_str = "Never / No Data"

    # Format human-readable heartbeat age
    if heartbeat_epoch <= 0 or heartbeat_age >= 999999:
        hb_age_str = "N/A"
    elif heartbeat_age < 3:
        hb_age_str = "Live (1s)"
    elif heartbeat_age < 60:
        hb_age_str = f"{int(heartbeat_age)}s ago"
    else:
        hb_age_str = f"{int(heartbeat_age // 60)}m ago"

    # Evaluate against the 4 states
    status = "OFFLINE"
    receiver_status = "STOPPED"
    reason = ""
    is_online = False

    # State 1: OFFLINE
    if not port_found:
        status = "OFFLINE"
        receiver_status = "DISCONNECTED"
        if not cleaned_port or cleaned_port == "NO COM PORT DETECTED":
            reason = "No COM port selected or no physical serial port detected on host."
        else:
            reason = f"Serial port {display_port} is not detected by Windows Device Manager."

    # State 2: RECEIVER STOPPED
    # Port is present, but receiver process is not running, stopped, or sending no heartbeats
    elif (
        not file_exists
        or raw_data.get("receiver_status") == "STOPPED"
        or heartbeat_age > heartbeat_timeout
        or heartbeat_epoch <= 0
        or (raw_data.get("port") and str(raw_data.get("port")).upper() != display_port.upper())
    ):
        status = "RECEIVER STOPPED"
        receiver_status = "STOPPED"
        if raw_data.get("port") and str(raw_data.get("port")).upper() != display_port.upper():
            reason = f"Receiver configured on {raw_data.get('port')}, waiting for bridge on {display_port}."
        elif raw_data.get("last_error"):
            reason = f"Bridge error: {raw_data.get('last_error')}"
        else:
            reason = f"ESP32 receiver process is not running on {display_port} or stopped reporting."

    # State 3: CONNECTION LOST
    # Port is present and receiver is alive/reporting, but device is offline or serial timed out
    elif raw_data.get("device_status") == "OFFLINE" or not raw_data.get("is_connected", True) or last_com_age > heartbeat_timeout:
        status = "CONNECTION LOST"
        receiver_status = "LISTENING (NO PACKETS)"
        if raw_data.get("last_error"):
            reason = f"Hardware bridge link issue: {raw_data.get('last_error')}"
        elif last_seen_epoch > 0:
            reason = f"Receiver active on {display_port}, but telemetry timed out ({int(last_com_age)}s ago > {heartbeat_timeout}s)."
        else:
            reason = f"Receiver active on {display_port}, waiting for incoming ESP32 serial data..."

    # State 4: ONLINE
    # Port present, receiver running, and fresh serial data received within timeout
    else:
        status = "ONLINE"
        is_online = True
        receiver_status = "STREAMING (LIVE)"
        reason = f"Active live serial stream verified on {display_port} (packet received {int(last_com_age)}s ago)."

    return {
        "status": status,
        "is_online": is_online,
        "target_port": display_port,
        "port_found": port_found,
        "available_ports": available_ports,
        "receiver_status": receiver_status,
        "last_seen_str": last_seen_str,
        "last_seen_epoch": last_seen_epoch,
        "last_com_age": last_com_age,
        "heartbeat_age": heartbeat_age,
        "heartbeat_age_str": hb_age_str,
        "heartbeat_timeout": heartbeat_timeout,
        "reason": reason,
        "file_exists": file_exists,
        "file_mtime": file_mtime
    }

def get_demo_airspace() -> dict:
    """Returns segregated demo/simulation dataset with clear markings."""
    return {
        "tracked_emitters": 5,
        "threat_alerts": 2,
        "sensor_link": "DEMO (SIMULATED)",
        "forensic_sd": "ACTIVE (SIMULATED)",
        "noise_floor": -91,
        "data_source": "DEMO_DATA",
        "airspace_inventory": [
            {
                "SSID": "POCO M4 5G",
                "BSSID/MAC": "78:11:DC:8A:23:01",
                "Vendor": "Xiaomi / POCO",
                "Type": "Mobile Hotspot",
                "Status": "UNSECURED",
                "First Seen": "2026-10-22 11:31:45",
                "Signal": "-50 dBm",
                "CH": 1,
                "lat": 26.7606,
                "lon": 83.3732
            },
            {
                "SSID": "MCC_LAB",
                "BSSID/MAC": "54:E6:FC:98:41:AA",
                "Vendor": "TP-Link Technologies",
                "Type": "Infrastructure",
                "Status": "PROTECTED",
                "First Seen": "2026-10-22 11:31:45",
                "Signal": "-62 dBm",
                "CH": 1,
                "lat": 26.7610,
                "lon": 83.3739
            },
            {
                "SSID": "ISEAE_4",
                "BSSID/MAC": "80:7A:BF:12:09:55",
                "Vendor": "Espressif Inc (IoT Node)",
                "Type": "Corporate WPA3",
                "Status": "PROTECTED",
                "First Seen": "2026-10-22 11:31:45",
                "Signal": "-58 dBm",
                "CH": 1,
                "lat": 26.7602,
                "lon": 83.3725
            },
            {
                "SSID": "Vivo T2x 5G",
                "BSSID/MAC": "AC:84:C6:E3:44:02",
                "Vendor": "Vivo Mobile",
                "Type": "Mobile AP",
                "Status": "SUSPICIOUS",
                "First Seen": "2026-10-22 11:31:45",
                "Signal": "-51 dBm",
                "CH": 6,
                "lat": 26.7615,
                "lon": 83.3745
            },
            {
                "SSID": "DIRECT-10-HP",
                "BSSID/MAC": "B4:69:21:77:80:CC",
                "Vendor": "HP Inc (Wi-Fi Direct)",
                "Type": "Wi-Fi Direct",
                "Status": "ISOLATED",
                "First Seen": "2026-10-22 11:31:45",
                "Signal": "-67 dBm",
                "CH": 11,
                "lat": 26.7598,
                "lon": 83.3718
            }
        ],
        "alerts": [
            {
                "time": "13:38:45",
                "ssid": "Target_Corp_WiFi",
                "mac": "DE:AD:BE:EF:00:13",
                "vendor": "Rogue ESP32 Marauder",
                "threat": "Deauthentication Burst Flood",
                "risk": "CRITICAL"
            },
            {
                "time": "10:17:34",
                "ssid": "Target_Corp_WiFi",
                "mac": "DE:AD:BE:EF:00:13",
                "vendor": "Rogue ESP32 Marauder",
                "threat": "Deauthentication Burst Flood",
                "risk": "HIGH"
            }
        ]
    }
