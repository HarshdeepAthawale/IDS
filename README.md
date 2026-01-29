# Intrusion Detection System (IDS)

Real-time network IDS with signature-based detection, Isolation Forest anomaly detection, and supervised classification (SecIDS-CNN by default). Flask backend, Next.js frontend, MongoDB. Live packet capture via Scapy; PCAP upload and analysis supported.

---

## What it does

- **Signature**: SQL injection, XSS, port scan, DoS, brute force, malware, exfil (regex + connection analysis).
- **Anomaly**: Isolation Forest; retrains when enough data is available.
- **Classifier**: Pre-trained [SecIDS-CNN](SecIDS-CNN/README.md) (default) or internal Random Forest/CICIDS2018 pipeline.
- **PCAP**: Heuristic detections + optional ML on extracted features.
- **Dashboard**: Alerts, traffic stats, whitelisting, rate limiting.

---

## Architecture

![System architecture](public/docs/architecture-system.svg)

- **Frontend** (3000): Next.js, proxies API/WebSocket to backend.
- **Backend** (3002): Flask, PacketSniffer, PacketAnalyzer, signature/anomaly/classifier, MongoDB.
- **MongoDB** (host 27018): Alerts and stats.

[Detection pipeline](public/docs/detection-pipeline.svg) · [PCAP flow](public/docs/pcap-analysis-flow.svg) · [Docker layout](public/docs/deployment-docker.svg)

---

## Quick start

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

```bash
docker compose up --build -d
```

- Frontend: http://localhost:3000  
- Backend: http://localhost:3002  
- MongoDB: localhost:27018 (optional, for tools)

**SecIDS-CNN (default):** Download `SecIDS-CNN.h5` from [Hugging Face (Keyven/SecIDS-CNN)](https://huggingface.co/Keyven/SecIDS-CNN), place in `SecIDS-CNN/`. Dockerfile copies it in. To use internal ML instead: `CLASSIFICATION_MODEL_TYPE=random_forest` in env.

**Optional:** `backend/.env` from `backend/env.example`; uncomment `env_file` for backend in `docker-compose.yml` if using Docker.

```bash
docker compose logs -f    # logs
docker compose down      # stop
docker compose down -v   # stop + remove volumes
```

Local backend: `backend/start.sh`; see `backend/README.md`.

---

## SecIDS-CNN (default classifier)

[SecIDS-CNN](SecIDS-CNN/README.md) (Keyvan Hardani): CNN for IDS, ~700 KB, runs on CPU/GPU/edge. **Metrics:** Accuracy 97.72%, Precision 97.74%, Recall 97.72%, F1 0.9772. Top SHAP features: Packet_Length_Mean, Flow_Duration. Training: FP32, batch 32, 50 epochs; multi-GPU; ~72 h on RTX 4090Ti; ~15 kg CO₂.

**Citation:**

```bibtex
@misc{keyvan_hardani_2024,
  author = {{Keyvan Hardani}},
  title  = {SecIDS-CNN (Revision 5daf4a4)},
  year   = 2024,
  url    = {https://huggingface.co/Keyven/SecIDS-CNN},
  doi    = {10.57967/hf/3351},
  publisher = {Hugging Face}
}
```

---

## Stack

**Backend:** Python, Flask, Flask-SocketIO, Scapy, scikit-learn, XGBoost, TensorFlow/Keras (SecIDS-CNN), MongoDB, pandas/NumPy.  
**Frontend:** Next.js, React, TypeScript, Tailwind, shadcn/ui, Recharts, Socket.io.  
**Infra:** Docker, Docker Compose, MongoDB 7.0.

---

## Docs and license

- [backend/docs/SECIDS_CNN.md](backend/docs/SECIDS_CNN.md) – integration and config  
- [SecIDS-CNN/README.md](SecIDS-CNN/README.md) – model details and citation  

**License:** MIT. SecIDS-CNN is cc-by-nc-4.0 ([Hugging Face](https://huggingface.co/Keyven/SecIDS-CNN)).
