import os
import time
from scapy.all import wrpcap, RadioTap, Dot11, Dot11Beacon, Dot11Elt

PCAP_STORAGE = "sentinel_forensics.pcap"

def append_beacon_to_pcap(ssid, mac_addr, channel=6, rssi=-50):
    """
    Synthesizes valid 802.11 Beacon management frames from ESP32 telemetry
    and appends them to a real Wireshark-compatible PCAP file.
    """
    try:
        # Construct IEEE 802.11 Beacon Frame with Radiotap header
        radio_tap = RadioTap(present="Rate+Channel+dBm_AntSignal", dBm_AntSignal=int(rssi))
        dot11 = Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff", addr2=mac_addr, addr3=mac_addr)
        beacon = Dot11Beacon(cap="ESS+privacy")
        
        # Information Elements (SSID and Channel)
        essid = Dot11Elt(ID="SSID", info=ssid.encode() if isinstance(ssid, str) else ssid)
        dsset = Dot11Elt(ID="DSset", info=bytes([int(channel)]))
        
        frame = radio_tap / dot11 / beacon / essid / dsset
        
        wrpcap(PCAP_STORAGE, frame, append=True)
        print(f"[+] PCAP Frame Captured: {ssid} ({mac_addr}) -> {PCAP_STORAGE}")
        return True
    except Exception as e:
        print(f"[-] PCAP export error: {e}")
        return False

if __name__ == "__main__":
    # Test packet synthesis
    print("[*] Running standalone PCAP export test...")
    append_beacon_to_pcap("Redmi 14C 5g", "FA:CF:19:C8:E2:09", channel=6, rssi=-45)
    append_beacon_to_pcap("POCO M4 5G", "78:11:DC:8A:23:01", channel=11, rssi=-52)
    print(f"[✓] Test completed. Check file: {os.path.abspath(PCAP_STORAGE)}")