import http.server
import socketserver
import json
import os
import sys

sys.path.append(r"C:\Users\ACER\Desktop\sentinel-iot")

from ai_anomaly_engine import SentinelAIEngine
from temporal_lstm_engine import TemporalSequenceEngine

PORT = 9100
TELEMETRY_PATH = r"C:\Users\ACER\Desktop\sentinel-iot\sentinel_telemetry.json"

ai_engine = SentinelAIEngine()
temporal_engine = TemporalSequenceEngine(sequence_length=10)

def get_telemetry():
    if os.path.exists(TELEMETRY_PATH):
        try:
            with open(TELEMETRY_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"networks_found": 19, "alerts": [], "device_status": "ONLINE", "sd_status": "ACTIVE"}

class RobustHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            data = get_telemetry()
            networks = float(data.get("networks_found", 19))
            threats = float(len(data.get("alerts", [])))
            hw_online = 1.0 if data.get("device_status") == "ONLINE" else 0.0
            sd_active = 1.0 if "ACTIVE" in data.get("sd_status", "") else 0.0

            ai_eval = ai_engine.evaluate(networks, threats)
            ai_risk_score = float(ai_eval.get("risk_score", 40.0))
            ai_anomaly = 1.0 if ai_eval.get("is_anomaly", False) else 0.0

            temp_eval = temporal_engine.push_sample(networks, threats)
            temp_score = float(temp_eval.get("temporal_anomaly_score", 15.0))
            temp_burst = 1.0 if temp_eval.get("burst_flag", False) else 0.0

            body = (
                f"# HELP sentinel_networks_discovered Total Wi-Fi/RF networks detected\n"
                f"sentinel_networks_discovered {networks}\n"
                f"# HELP sentinel_active_threats Number of active WIDS threat alerts\n"
                f"sentinel_active_threats {threats}\n"
                f"# HELP sentinel_hardware_online Hardware Node Status\n"
                f"sentinel_hardware_online {hw_online}\n"
                f"# HELP sentinel_sdcard_active Forensic SD Card Status\n"
                f"sentinel_sdcard_active {sd_active}\n"
                f"# HELP sentinel_ai_anomaly_detected ML Anomaly Flag\n"
                f"sentinel_ai_anomaly_detected {ai_anomaly}\n"
                f"# HELP sentinel_ai_risk_score AI Static Risk Score\n"
                f"sentinel_ai_risk_score {ai_risk_score}\n"
                f"# HELP sentinel_temporal_anomaly_score Temporal Dynamic Score\n"
                f"sentinel_temporal_anomaly_score {temp_score}\n"
                f"# HELP sentinel_temporal_burst_detected Temporal Burst Flag\n"
                f"sentinel_temporal_burst_detected {temp_burst}\n"
            ).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return  # Quiet console

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", PORT), RobustHandler) as httpd:
    print(f"[+] Sentinel-IoT Metrics Exporter ACTIVE on http://127.0.0.1:{PORT}/metrics")
    httpd.serve_forever()
