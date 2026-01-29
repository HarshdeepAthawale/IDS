"""
Lightweight smoke test for the PCAP analysis endpoint.
Requires a real PCAP file to test the analysis endpoint.
Usage: python backend/scripts/smoke_pcap.py <path_to_pcap_file>
"""

import os
import sys
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:3002")


def main() -> int:
    if len(sys.argv) < 2:
        print("[ERROR] PCAP file path required")
        print("Usage: python backend/scripts/smoke_pcap.py <path_to_pcap_file>")
        return 1

    pcap_path = sys.argv[1]
    if not os.path.exists(pcap_path):
        print(f"[ERROR] PCAP file not found: {pcap_path}")
        return 1

    try:
        with open(pcap_path, 'rb') as f:
            files = {'file': (os.path.basename(pcap_path), f, 'application/octet-stream')}
            response = requests.post(f"{BACKEND_URL}/api/pcap/analyze", files=files, timeout=30)
            response.raise_for_status()
            payload = response.json()
            risk = payload.get("risk", {})
            meta = payload.get("metadata", {})

            print(f"PCAP analysis successful")
            print(f"Risk: {risk.get('score', '?')} ({risk.get('level', 'unknown')})")
            print(f"Packets: {meta.get('packets_processed', '?')} | Duration: {meta.get('duration_seconds', '?')}s")
            print(f"Detections: {len(payload.get('detections', []))}")
            return 0
    except Exception as exc:
        print(f"[ERROR] PCAP smoke test failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
