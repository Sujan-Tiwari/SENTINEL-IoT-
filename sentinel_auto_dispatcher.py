import time
import json
import os
import urllib.request
import urllib.parse
from datetime import datetime

TELEMETRY_FILE = r"C:\Users\ACER\Desktop\sentinel-iot\sentinel_telemetry.json"
CONFIG_FILE = r"C:\Users\ACER\Desktop\sentinel-iot\telegram_config.json"

# Cooldown dictionary taaki ek hi attack ka bar-bar spam na aaye (60 seconds)
LAST_DISPATCH = {}
COOLDOWN_SECONDS = 60

def get_credentials():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"bot_token": "", "chat_id": "6630152067", "auto_alert_enabled": True}

def send_telegram_alert(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[-] Telegram dispatch failed: {e}")
        return False

def monitor_airspace():
    print("[*] Sentinel-IoT Autonomous Threat Dispatcher Active...")
    while True:
        cfg = get_credentials()
        bot_token = cfg.get("bot_token", "")
        chat_id = cfg.get("chat_id", "")
        auto_enabled = cfg.get("auto_alert_enabled", True)

        if auto_enabled and bot_token and os.path.exists(TELEMETRY_FILE):
            try:
                with open(TELEMETRY_FILE, "r") as f:
                    data = json.load(f)
                
                alerts = data.get("alerts", [])
                for alert in alerts:
                    threat_type = alert.get("threat", "Unknown Anomaly")
                    target_bssid = alert.get("mac", "UNKNOWN")
                    ssid = alert.get("ssid", "Broadcast")
                    now = time.time()

                    # Threat signature key
                    incident_key = f"{threat_type}_{target_bssid}"
                    if now - LAST_DISPATCH.get(incident_key, 0) > COOLDOWN_SECONDS:
                        message = (
                            f"🚨 *[AUTONOMOUS TACTICAL ALERT]*\n\n"
                            f"🛡️ *Threat:* {threat_type}\n"
                            f"🎯 *Target SSID:* {ssid}\n"
                            f"📡 *Offender BSSID:* {target_bssid}\n"
                            f"⚡ *SOC Action:* Quarantined via Airspace Shield\n"
                            f"🕒 *Timestamp:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        success = send_telegram_alert(bot_token, chat_id, message)
                        if success:
                            LAST_DISPATCH[incident_key] = now
                            print(f"[+] Autonomous alert dispatched to smartphone: {incident_key}")
            except Exception as e:
                pass
        time.sleep(2)

if __name__ == "__main__":
    monitor_airspace()
