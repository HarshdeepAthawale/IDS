# IDS — AI-Powered Real-Time Intrusion Detection System

An intrusion detection system that combines real-time packet monitoring (Scapy) with multi-layer detection: signature-based pattern matching, Isolation Forest anomaly detection, and supervised ML classification (SecIDS-CNN or Random Forest). Alerts and traffic stats are persisted in MongoDB, exposed via a Flask REST API and Socket.IO for live updates, and visualized in a Next.js dashboard.

## Features

- **Real-time packet capture** — Live packet analysis using Scapy with configurable interface and auto-start
- **Signature-based detection** — Pattern matching for known attacks (SQL injection, XSS, port scan, DoS, brute force, malware communication, data exfiltration)
- **Anomaly detection** — Isolation Forest for unsupervised detection of unusual traffic patterns
- **Supervised classification** — Optional SecIDS-CNN (pre-trained CNN) or Random Forest / XGBoost / SVM / Logistic Regression trained on labeled data
- **PCAP analysis** — Upload and analyze PCAP files with configurable packet limit and timeout
- **Alert management** — List, filter, resolve, delete alerts; bulk delete and bulk resolve; history and summary endpoints
- **Traffic statistics** — Protocol distribution, connection tracking, real-time stats, anomaly listings
- **Real-time dashboard** — WebSocket (Socket.IO) updates for traffic and new alerts
- **Training pipeline** — Label samples, import data, train models, evaluate, metrics, confusion matrix, training history
- **Rate limiting** — Flask-Limiter with default and per-endpoint limits
- **Health and system info** — `/api/health` and `/api/system/info` for status and configuration

## Tech stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI, Recharts, socket.io-client, Lucide React |
| **Backend** | Python 3.12, Flask 3, Flask-CORS, Flask-SocketIO, Flask-Limiter, Scapy, PyMongo, scikit-learn, imbalanced-learn, xgboost-cpu, TensorFlow (for SecIDS-CNN) |
| **Data** | MongoDB 7.0 |
| **Deployment** | Docker, multi-stage Dockerfile (backend + frontend; optional single-image) |

## Architecture

1. **Packet capture** — Scapy captures live packets (or test packets are injected via API).
2. **Analysis** — Packets are processed by the analyzer: signature rules, Isolation Forest, and (when enabled) supervised classifier (e.g. SecIDS-CNN).
3. **Persistence** — Alerts and traffic statistics are written to MongoDB (collections: `alerts`, `traffic_stats`, `user_activities`, `pcap_analyses`; default database: `ids_db`).
4. **API and real-time** — Flask REST API and Socket.IO serve the Next.js app; Next.js API routes under `app/api/` proxy to the Flask backend using `FLASK_API_URL`.

Diagrams in the repo:

- [Architecture system](public/docs/architecture-system.svg)
- [Detection pipeline](public/docs/detection-pipeline.svg)
- [PCAP analysis flow](public/docs/pcap-analysis-flow.svg)
- [Deployment (Docker)](public/docs/deployment-docker.svg)

## Project structure

```
├── app/                    # Next.js app router (pages + API routes)
│   ├── page.tsx            # Dashboard
│   ├── alerts/             # Alerts page
│   ├── realtime/           # Real-time page
│   ├── analysis/           # Analysis page
│   ├── summary/            # Summary page
│   ├── stats/              # Stats page
│   └── api/                # Next.js API routes (proxy to Flask)
├── components/             # React components (sidebar, dashboard, UI)
├── contexts/               # React contexts (e.g. WebSocket, PCAP analysis)
├── hooks/                  # Custom hooks (debounce, WebSocket, etc.)
├── lib/                    # Utilities and config (e.g. config.ts, flask-api)
├── public/
│   └── docs/               # Architecture and flow diagrams (SVG)
├── backend/                # Flask IDS backend
│   ├── app.py              # Main Flask app, Socket.IO, health, test endpoints
│   ├── config.py           # Configuration (env-based)
│   ├── env.example         # Environment variables template
│   ├── requirements.txt    # Python dependencies
│   ├── routes/             # Blueprints: alerts, stats, analyze, training, pcap
│   ├── services/           # Packet sniffer, analyzer, logger, classifier, pcap_analyzer, etc.
│   ├── models/             # MongoDB models (db_models.py)
│   └── scripts/            # Training, preprocessing, verification scripts
├── SecIDS-CNN/             # SecIDS-CNN model and docs (optional classifier)
├── docker-compose.yml      # Backend, frontend, MongoDB
├── Dockerfile              # Multi-stage build (backend, frontend)
└── package.json            # Next.js app (Node >=20.9.0)
```

## Getting started

### Prerequisites

- **Node.js** >= 20.9.0 (for frontend)
- **Python** 3.12 (for backend)
- **MongoDB** (local or remote), or use Docker for all services

### Docker (recommended)

```bash
docker compose up -d
```

- Frontend: http://localhost:3000  
- Backend API: http://localhost:3002  
- MongoDB: host port `27018` (container `27017`), database `ids_db` by default  

Backend container has `NET_ADMIN` and `NET_RAW` for packet capture. Set `CLASSIFICATION_ENABLED=true` and `CLASSIFICATION_MODEL_TYPE=secids_cnn` in the environment to use the pre-trained SecIDS-CNN model (included in the image at `SecIDS-CNN/`).

### Local backend

```bash
cd backend
cp env.example .env
# Edit .env: set MONGODB_URI (e.g. mongodb://localhost:27017/) and other options
pip install -r requirements.txt
python app.py
```

Backend runs on **port 3002** by default (`FLASK_PORT`). For live packet capture on Linux, run with sufficient privileges (e.g. `sudo python app.py`) or set capabilities: `sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/python3`.

### Local frontend

```bash
# From project root
export NEXT_PUBLIC_FLASK_API_URL=http://localhost:3002   # or rely on default in lib/config.ts
npm install
npm run dev
```

Frontend runs on **port 3000**. It uses `NEXT_PUBLIC_FLASK_API_URL` in the browser and, when running in Docker or server-side, `FLASK_API_URL` for proxying to the backend.

## Configuration

Main environment variables (backend). Copy `backend/env.example` to `backend/.env` and adjust.

| Variable | Default / example | Description |
|----------|-------------------|-------------|
| `MONGODB_URI` | `mongodb://localhost:27017/` | MongoDB connection string |
| `MONGODB_DATABASE_NAME` | `ids_db` | Database name |
| `SECRET_KEY` | (set in production) | Flask secret key |
| `FLASK_PORT` | `3002` | Backend port |
| `CLASSIFICATION_ENABLED` | `true` | Enable supervised classification |
| `CLASSIFICATION_MODEL_TYPE` | `secids_cnn` | `secids_cnn`, `random_forest`, etc. |
| `SECIDS_MODEL_PATH` | (optional) | Path to SecIDS-CNN.h5; default resolved from project root |
| `CAPTURE_INTERFACE` | `any` | Scapy capture interface |
| `PACKET_RATE_THRESHOLD` | `1000` | Packet rate threshold |
| `CONNECTION_LIMIT` | `100` | Connection limit |
| `ANOMALY_SCORE_THRESHOLD` | `0.5` | Anomaly score threshold |
| `WHITELIST_IPS` | `127.0.0.1,10.0.0.0/8,192.168.0.0/16` | Comma-separated IP whitelist |
| `ALERT_DEDUP_WINDOW` | `300` | Alert deduplication window (seconds) |
| `PCAP_MAX_PACKETS` | `2000` | Default max packets per PCAP analysis |
| `PCAP_ANALYSIS_TIMEOUT` | `300` | PCAP analysis timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |

Frontend:

- **`FLASK_API_URL`** — Used by Next.js server (e.g. in Docker: `http://backend:3002`).
- **`NEXT_PUBLIC_FLASK_API_URL`** — Used by the browser; default in code is `http://localhost:3002`.

## API reference

All endpoints below are **Flask backend** routes. The Next.js app calls them via `app/api/*` routes that proxy to the backend using `FLASK_API_URL`.

### Health and system

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check (DB, sniffer, analyzer status) |
| GET | `/api/system/info` | System and configuration info |

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts` | List alerts (query: type, severity, resolved, source_ip, limit, start_date, end_date) |
| GET | `/api/alerts/history` | Alert history |
| GET | `/api/alerts/summary` | Alert summary |
| GET | `/api/alerts/critical` | Critical alerts |
| PATCH | `/api/alerts/<alert_id>` | Update alert (e.g. resolve) |
| DELETE | `/api/alerts/<alert_id>` | Delete alert |
| POST | `/api/alerts/bulk-delete` | Bulk delete alerts |
| POST | `/api/alerts/bulk-resolve` | Bulk resolve alerts |

### Stats

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats/traffic` | Traffic statistics |
| GET | `/api/stats/protocols` | Protocol distribution |
| GET | `/api/stats/connections` | Connection stats |
| GET | `/api/stats/anomalies` | Anomaly listings |
| GET | `/api/stats/realtime` | Real-time stats |
| GET | `/api/stats/debug/active-connections` | Debug active connections |

### Analyze

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Analyze a single packet |
| POST | `/api/analyze/bulk` | Analyze multiple packets |
| POST | `/api/analyze/flow` | Analyze flow |
| GET | `/api/analyze/model-info` | Model information |

### Training

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/training/label` | Label a sample |
| GET | `/api/training/data` | Get training data |
| GET | `/api/training/data/unlabeled` | Get unlabeled samples |
| POST | `/api/training/import` | Import training data |
| DELETE | `/api/training/data/<sample_id>` | Delete a sample |
| GET | `/api/training/statistics` | Training statistics |
| POST | `/api/training/train` | Train model |
| GET | `/api/training/evaluate` | Evaluation results |
| GET | `/api/training/metrics` | Metrics |
| GET | `/api/training/model-info` | Model info |
| GET | `/api/training/confusion-matrix` | Confusion matrix |
| GET | `/api/training/history` | Training history |

### PCAP

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pcap/analyze` | Analyze uploaded PCAP |
| GET | `/api/pcap/last` | Last PCAP analysis result |
| GET | `/api/pcap/stats` | PCAP analysis stats |
| GET | `/api/pcap/analyses` | List PCAP analyses |
| GET | `/api/pcap/analyses/<analysis_id>` | Get one PCAP analysis |

### Test

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/test/trigger-alert` | Manually trigger a test alert (broadcast via WebSocket) |
| POST | `/api/test/inject-packet` | Inject a test packet into the pipeline |

## WebSocket (Socket.IO)

- **Server**: Flask-SocketIO on the same host/port as the Flask app (default 3002).
- **CORS**: `http://localhost:3000`, `http://127.0.0.1:3000`.

Events:

- **connect** — Client connected; server may emit `connected`.
- **join_room** — Client joins a room (e.g. `dashboard`); server emits `joined_room`.
- **leave_room** — Client leaves a room; server emits `left_room`.
- **traffic_update** — Server broadcasts traffic stats (packet rate, threats, connections, protocol distribution, etc.).
- **new_alert** — Server broadcasts a new alert (e.g. after detection or test trigger).
- **connection_update** — Server broadcasts active connection count changes.

## Rate limits

- **Default**: 200 requests per hour, 50 per minute (Flask-Limiter, per IP).
- **Stricter per endpoint**:
  - Delete alert: 10/minute  
  - Bulk delete alerts: 5/minute  
  - Bulk resolve alerts: 10/minute  
  - Analyze packet: 30/minute  
  - Analyze bulk: 10/minute  
  - Train model: 20/minute  
  - Label sample: 20/minute  
  - PCAP analyze: 8/minute  
  - PCAP get last result: 20/minute  

## SecIDS-CNN

Optional pre-trained CNN for intrusion detection. Source: [SecIDS-CNN](SecIDS-CNN/README.md) (Hugging Face: [Keyven/SecIDS-CNN](https://huggingface.co/Keyven/SecIDS-CNN)); license: Creative Commons Attribution Non Commercial 4.0 (cc-by-nc-4.0).

- **Enable**: `CLASSIFICATION_ENABLED=true`, `CLASSIFICATION_MODEL_TYPE=secids_cnn`.
- **Model path**: Set `SECIDS_MODEL_PATH` if needed; otherwise the backend resolves the default path (e.g. project root `SecIDS-CNN/SecIDS-CNN.h5`). In Docker, the image copies `SecIDS-CNN/` into the backend container.
- **Dependencies**: TensorFlow (see `backend/requirements.txt`).

## Testing

Backend tests (pytest):

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

With Docker:

```bash
docker compose exec backend python -m pytest tests/ -v
```

Full backend dependencies (including TensorFlow for SecIDS-CNN) are required for all tests.

## License and credits

- **Project**: See repository for license and attribution.
- **SecIDS-CNN**: CC BY-NC 4.0; model by Keyvan Hardani; see [SecIDS-CNN/README.md](SecIDS-CNN/README.md) and [Hugging Face](https://huggingface.co/Keyven/SecIDS-CNN).

For backend-only setup and scripts, see [backend/README.md](backend/README.md).
