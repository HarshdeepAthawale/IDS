# Custom IDS System

A comprehensive Intrusion Detection System built with modern web technologies for real-time network monitoring and threat detection.

## Tech Stack

- **Backend:** Node.js with Express.js
- **Frontend:** Next.js (React) with TypeScript
- **Database:** JSON file storage
- **Packet Capture:** pcap library for real network traffic
- **Real-time:** WebSockets (Socket.io)
- **Styling:** Tailwind CSS with dark theme
- **Version Control:** Git with GitHub integration

## Features

- **Real-time Packet Capture:** Monitor network traffic using raw packet capture
- **Intrusion Detection:** Detect DoS attacks, port scans, and suspicious IP activity
- **Live Dashboard:** Real-time visualization of network statistics and alerts
- **WebSocket Integration:** Instant updates for alerts and statistics
- **Modern UI:** Dark theme with responsive design

## Project Structure

```
IDS/
├── backend/                 # Node.js Express server
│   ├── controllers/         # API route handlers
│   ├── services/           # Core IDS logic
│   ├── routes/             # API endpoints
│   ├── models/             # Data schemas
│   ├── utils/              # Helper functions
│   ├── config/             # Configuration files
│   ├── data/               # JSON storage (gitignored)
│   └── server.js           # Main server file
├── frontend/               # Next.js React application
│   ├── app/                # Next.js App Router
│   ├── components/         # React components
│   ├── lib/                # API and utility functions
│   └── public/             # Static assets
└── README.md               # This file
```

## Detection Algorithms

1. **DoS Detection:** Monitors packet rate per source IP (>100 packets/sec triggers alert)
2. **Port Scan Detection:** Tracks unique ports accessed per IP (>20 ports in 10sec triggers alert)
3. **Suspicious Volume:** Detects unusual traffic volume per IP (>10MB in 5sec triggers alert)

## Installation Requirements

### Windows Prerequisites
- **Npcap or WinPcap:** Required for packet capture functionality
- **Node.js:** Version 16.0.0 or higher
- **Administrator privileges:** Required to run packet capture

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd IDS
   ```

2. **Install backend dependencies:**
   ```bash
   cd backend
   npm install
   ```

3. **Install frontend dependencies:**
   ```bash
   cd ../frontend
   npm install
   ```

4. **Setup environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Running the Application

### Backend Server
```bash
cd backend
npm start
# or for development
npm run dev
```

### Frontend Application
```bash
cd frontend
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## API Endpoints

- `GET /api/alerts` - Retrieve paginated alerts
- `GET /api/stats` - Get real-time statistics
- `POST /api/packets` - Manually inject test packets

## WebSocket Events

- `new-alert` - Emitted when a new intrusion is detected
- `stats-update` - Emitted every 2 seconds with live statistics
- `packet-stream` - Emitted for recent packet data

## Development Status

This project is implemented in 10 phases:
- ✅ Phase 1: Project Setup & GitHub Integration
- ⏳ Phase 2: Backend Foundation & API Structure
- ⏳ Phase 3: Packet Capture Integration
- ⏳ Phase 4: IDS Detection Logic
- ⏳ Phase 5: Complete Backend API Endpoints
- ⏳ Phase 6: WebSocket Real-time Integration
- ⏳ Phase 7: Next.js Frontend Foundation
- ⏳ Phase 8: Dashboard Components
- ⏳ Phase 9: Frontend-Backend Integration
- ⏳ Phase 10: Testing, Documentation & Final Polish

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details
