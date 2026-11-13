import json
import urllib.request

class SentinelLLMAnalyst:
    def __init__(self, ollama_url="http://127.0.0.1:11434", model="llama3:latest"):
        self.ollama_url = ollama_url
        self.model = model

    def _query_ollama(self, prompt: str) -> str:
        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except Exception:
            return ""

    def generate_incident_briefing(self, alert_data: dict, risk_score: float) -> dict:
        threat_type = alert_data.get("threat", "Unknown RF Variation")
        target_ssid = alert_data.get("ssid", "Hidden/Broadcast")
        mac = alert_data.get("mac", "00:00:00:00:00:00")
        vendor = alert_data.get("vendor", "Generic Transceiver")

        mitre_mapping = {
            "Deauth": ("T1498 (Network Denial of Service)", "WiFi Pineapple / ESP32 Marauder Jammer", "Immediate Channel Hopping + Rogue BSSID Deauth Shielding"),
            "Beacon": ("T1499 (Endpoint DoS - Resource Exhaustion)", "Airbase-ng / Flipper Zero Karma Rogue AP", "Blacklist OUI prefix and enable 802.11w Protected Management Frames (PMF)"),
            "Flood": ("T1498.001 (Direct Network Flood)", "Rogue Transmitter packet injector", "Isolate Target Channel & capture forensic PCAP ring buffer")
        }

        technique, threat_actor_sig, mitigation = ("T1498 (Wireless Anomaly)", "Unregistered RF Emitter", "Enforce Airspace Containment")
        for key in mitre_mapping:
            if key.lower() in threat_type.lower():
                technique, threat_actor_sig, mitigation = mitre_mapping[key]
                break

        prompt = (
            f"You are a military-grade SOC RF Analyst. Analyze this incident strictly in 3 sentences:\n"
            f"Threat: {threat_type}, BSSID: {mac}, Vendor: {vendor}, Target SSID: {target_ssid}, AI Risk: {risk_score}%.\n"
            f"Include MITRE ATT&CK mapping, hardware signature suspicion, and immediate mitigation."
        )

        llm_response = self._query_ollama(prompt)
        if not llm_response:
            llm_response = (
                f"Suspicious transmitter [{mac}] ({vendor}) exhibiting {threat_type} behaviors against SSID '{target_ssid}'. "
                f"TTP signature maps to MITRE ATT&CK {technique} (Likely signature: {threat_actor_sig}). "
                f"Recommended containment: {mitigation}."
            )

        return {
            "mitre_technique": technique,
            "suspected_tool": threat_actor_sig,
            "briefing": llm_response,
            "confidence": f"{min(99.2, max(60.0, risk_score + 15.0)):.1f}%"
        }
