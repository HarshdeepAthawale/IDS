# 🚀 Quick Start Guide

Get your Custom IDS System up and running in 5 minutes!

## ⚡ Quick Setup

### 1. Prerequisites Check
```bash
# Check Node.js version (16+ required)
node --version

# Check npm version
npm --version

# Windows: Ensure Npcap is installed
# Linux: Install libpcap
sudo apt-get install libpcap-dev  # Ubuntu/Debian
```

### 2. Install Dependencies
```bash
# Backend
cd backend
npm install

# Frontend  
cd ../frontend
npm install
```

### 3. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit if needed (defaults work for most cases)
nano .env
```

### 4. Start the System

#### Terminal 1 - Backend (Run as Administrator/Root)
```bash
cd backend

# Windows (PowerShell as Administrator)
sudo npm start

# Linux/macOS
sudo npm start
```

#### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

### 5. Access Dashboard
Open your browser: **http://localhost:3000**

## 🧪 Quick Test

### Test the System
```bash
cd backend

# Run comprehensive test suite
npm test

# Or test specific components
npm run test:packets
npm run test:dos
npm run test:portscan
```

### Manual Verification
1. **Check Backend**: http://localhost:5000/health
2. **Check API**: http://localhost:5000/api/stats
3. **Check Dashboard**: http://localhost:3000
4. **Start Capture**: Use dashboard or API to start packet capture

## 🎯 First Steps

### 1. Start Packet Capture
- **Via Dashboard**: Go to System Status panel → Click "Start Capture"
- **Via API**: 
  ```bash
  curl -X POST http://localhost:5000/api/packets/start
  ```

### 2. Generate Test Traffic
```bash
cd backend
npm run test:packets
```

### 3. View Results
- **Dashboard**: Check alerts table and statistics
- **API**: `curl http://localhost:5000/api/alerts`

## 🔧 Common Issues

### Permission Denied
```bash
# Run backend with admin privileges
sudo npm start  # Linux/macOS
# PowerShell as Administrator on Windows
```

### No Network Interfaces
```bash
# Check available interfaces
curl http://localhost:5000/api/interfaces

# Use 'any' interface
# Edit .env: CAPTURE_INTERFACE=any
```

### WebSocket Connection Failed
- Check if backend is running on port 5000
- Verify firewall settings
- Check CORS configuration

## 📊 What to Expect

### Normal Operation
- **Backend**: Shows startup banner and service status
- **Frontend**: Dashboard loads with real-time updates
- **Captures**: Network packets are captured and analyzed
- **Alerts**: Threats are detected and displayed

### Test Results
- **API Tests**: All endpoints respond correctly
- **WebSocket**: Real-time connection established
- **Detection**: DoS, port scan, and volume attacks detected
- **Performance**: System handles load efficiently

## 🆘 Need Help?

1. **Check Logs**: `tail -f backend/logs/ids.log`
2. **Run Tests**: `npm test`
3. **Read Docs**: Full documentation in README.md
4. **Check Status**: http://localhost:5000/health

## 🎉 Success!

If everything is working:
- ✅ Backend server running on port 5000
- ✅ Frontend dashboard on port 3000
- ✅ WebSocket connection established
- ✅ Packet capture operational
- ✅ Detection algorithms active
- ✅ Real-time alerts appearing

Your IDS system is ready to monitor your network! 🛡️
