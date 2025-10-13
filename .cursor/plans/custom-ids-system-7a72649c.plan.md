<!-- 7a72649c-e9bf-435b-9a84-05950961d7ab 29bcf176-29fc-465a-bd90-a4ac9e530e59 -->
# Custom IDS System - 10 Phase Implementation

## Overview

Building a full-stack IDS with real network packet capture, detection algorithms (DoS, Port Scan, Suspicious IP), real-time WebSocket updates, and a modern Next.js dashboard.

## Implementation Strategy

- Each phase will be completed in sequence
- After each phase, a summary will be provided for manual git commit
- Using `pcap` library (requires Npcap/WinPcap on Windows)
- JSON file storage in `/backend/data` (gitignored)
- Real-time updates via Socket.io

## Phase 1: Project Setup & GitHub Integration

**Files to create:**

- `backend/package.json` - Node.js backend dependencies
- `frontend/package.json` - Next.js frontend setup
- `.gitignore` - Ignore node_modules, data files, .env
- `README.md` - Project overview and structure
- Directory structure: `/backend`, `/frontend`

**Key actions:**

- Initialize backend with Express, cors, dotenv, socket.io, pcap
- Initialize Next.js frontend with TypeScript support
- Setup proper .gitignore for both backend and frontend
- Create initial README with tech stack overview

## Phase 2: Backend Foundation & API Structure

**Files to create:**

- `backend/server.js` - Express server entry point
- `backend/routes/api.js` - API route definitions
- `backend/controllers/alertController.js` - Alert handling logic
- `backend/controllers/statsController.js` - Statistics aggregation
- `backend/controllers/packetController.js` - Packet operations
- `backend/utils/storage.js` - JSON file read/write operations
- `backend/models/schemas.js` - Data structure definitions

**Key features:**

- Modular Express app structure
- CORS configuration for Next.js frontend
- Basic routes: GET `/api/alerts`, GET `/api/stats`, POST `/api/packets`
- JSON storage utility functions with error handling
- Environment variable setup (.env.example)

## Phase 3: Packet Capture Integration

**Files to create:**

- `backend/services/packetCapture.js` - Pcap integration and packet parsing
- `backend/data/.gitkeep` - Data directory placeholder
- `backend/config/capture.js` - Capture configuration

**Key features:**

- Initialize pcap session with network interface detection
- Parse raw packets (Ethernet → IP → TCP/UDP layers)
- Extract: timestamp, src_ip, dst_ip, protocol, port, size, flags
- Store packets in `data/packets.json` (rolling buffer, max 10000 packets)
- Error handling for missing permissions/Npcap
- Start/stop capture functions

## Phase 4: IDS Detection Logic

**Files to create:**

- `backend/services/idsEngine.js` - Core detection algorithms
- `backend/config/thresholds.js` - Configurable detection thresholds

**Detection algorithms:**

1. **DoS Detection**: Track packet rate per source IP (>100 packets/sec = alert)
2. **Port Scan Detection**: Monitor unique ports accessed per IP (>20 ports in 10sec = alert)
3. **Suspicious Volume**: Unusual traffic volume per IP (>10MB in 5sec = alert)

**Alert system:**

- Generate alerts with severity (low/medium/high/critical)
- Store in `data/alerts.json` with timestamp, type, source_ip, details
- Alert deduplication (avoid spam for same IP/type within 1 min)

## Phase 5: Complete Backend API Endpoints

**Update files:**

- `backend/controllers/alertController.js` - Implement GET with pagination, filtering
- `backend/controllers/statsController.js` - Implement real-time statistics
- `backend/controllers/packetController.js` - Manual packet injection for testing

**API endpoints:**

- `GET /api/alerts?page=1&limit=50&severity=high` - Paginated alerts
- `GET /api/stats` - Returns: packets/sec, total_intrusions, top_suspicious_ips[], traffic_mb_per_sec
- `POST /api/packets` - Test endpoint to manually inject packets

## Phase 6: WebSocket Real-time Integration

**Files to create:**

- `backend/services/websocket.js` - Socket.io server setup and event broadcasting

**Update:**

- `backend/server.js` - Integrate Socket.io server

**WebSocket events:**

- `new-alert` - Emitted when IDS generates alert
- `stats-update` - Emitted every 2 seconds with live stats
- `packet-stream` - Emitted for recent packets (optional, for visualization)
- Connection/disconnection handling with logging

## Phase 7: Next.js Frontend Foundation

**Files to create:**

- `frontend/app/layout.js` - Root layout with dark theme
- `frontend/app/page.js` - Main dashboard page
- `frontend/lib/api.js` - Axios API client
- `frontend/lib/socket.js` - Socket.io client connection
- `frontend/tailwind.config.js` - Tailwind with custom dark theme
- `frontend/components/Header.jsx` - Header with theme toggle

**Setup:**

- Next.js 14+ with App Router
- Tailwind CSS with dark mode support
- Axios for API calls
- Socket.io-client for WebSocket
- Recharts for graphs

## Phase 8: Dashboard Components

**Files to create:**

- `frontend/components/AlertTable.jsx` - Real-time alert display table
- `frontend/components/PacketGraph.jsx` - Live packet rate line chart (Recharts)
- `frontend/components/StatsCard.jsx` - Statistics cards (intrusions, active IPs)
- `frontend/components/LiveIndicator.jsx` - Connection status indicator

**Component features:**

- AlertTable: Color-coded severity badges, timestamp formatting, pagination
- PacketGraph: Real-time line chart with last 60 seconds of packet rate
- StatsCard: Grid layout with animated counters, top suspicious IPs list
- Responsive design with Tailwind CSS

## Phase 9: Frontend-Backend Integration

**Update files:**

- `frontend/app/page.js` - Connect all components with WebSocket listeners
- `frontend/lib/socket.js` - Event listeners and reconnection logic
- `frontend/lib/api.js` - API endpoint functions

**Integration:**

- Fetch initial data on page load (alerts, stats)
- WebSocket listeners: `new-alert` → update AlertTable state
- `stats-update` → update StatsCard and PacketGraph
- Auto-reconnect on disconnect with visual indicator
- Error boundaries and loading states

## Phase 10: Testing, Documentation & Final Polish

**Files to create:**

- `backend/scripts/testPackets.js` - Script to inject test packets
- `backend/scripts/simulateAttack.js` - Simulate DoS/Port scan attacks
- `.env.example` - Environment variable template
- Update `README.md` - Complete documentation

**Documentation includes:**

- Installation steps (Npcap requirement for Windows)
- How to run backend (with elevated permissions)
- How to run frontend
- API documentation
- Testing instructions
- Troubleshooting guide

**Testing:**

- Test DoS detection with packet flood
- Test port scan detection with sequential port access
- Verify WebSocket reconnection
- Test all API endpoints
- Final code cleanup and console logging optimization

## Key Technical Decisions

- **Packet Capture**: Using `pcap` for raw packet access (requires Npcap on Windows)
- **Data Storage**: JSON files in `/backend/data` (gitignored, rolling buffer to prevent huge files)
- **Real-time**: Socket.io for bidirectional communication
- **Frontend**: Next.js 14 App Router with server/client components
- **Styling**: Tailwind CSS with dark theme as default
- **Detection**: Time-window based algorithms with configurable thresholds

## Post-Phase Actions

After each phase completion:

1. Summary of changes will be displayed
2. User manually commits and pushes to GitHub
3. User confirms to proceed to next phase

### To-dos

- [ ] Project Setup & GitHub Integration - Initialize backend/frontend projects, create structure, setup .gitignore and README
- [ ] Backend Foundation & API Structure - Create Express server, routes, controllers, storage utilities
- [ ] Packet Capture Integration - Implement pcap service, packet parsing, JSON storage
- [ ] IDS Detection Logic - Build DoS, Port Scan, Suspicious IP detection algorithms and alert system
- [ ] Complete Backend API Endpoints - Implement controllers for alerts, stats, packets with pagination
- [ ] WebSocket Real-time Integration - Setup Socket.io server and event broadcasting
- [ ] Next.js Frontend Foundation - Setup Next.js, Tailwind, API client, WebSocket client, layout
- [ ] Dashboard Components - Create AlertTable, PacketGraph, StatsCard components
- [ ] Frontend-Backend Integration - Connect components with API/WebSocket, add error handling
- [ ] Testing, Documentation & Final Polish - Create test scripts, complete README, verify all features