const fs = require('fs').promises;
const path = require('path');

const DATA_DIR = path.join(__dirname, '../data');
const PACKETS_FILE = path.join(DATA_DIR, 'packets.json');
const ALERTS_FILE = path.join(DATA_DIR, 'alerts.json');

// Ensure data directory exists
const ensureDataDir = async () => {
  try {
    await fs.access(DATA_DIR);
  } catch {
    await fs.mkdir(DATA_DIR, { recursive: true });
  }
};

// Initialize empty files if they don't exist
const initializeFiles = async () => {
  await ensureDataDir();
  
  try {
    await fs.access(PACKETS_FILE);
  } catch {
    await fs.writeFile(PACKETS_FILE, JSON.stringify([], null, 2));
  }
  
  try {
    await fs.access(ALERTS_FILE);
  } catch {
    await fs.writeFile(ALERTS_FILE, JSON.stringify([], null, 2));
  }
};

// Packet operations
const getPackets = async () => {
  try {
    await initializeFiles();
    const data = await fs.readFile(PACKETS_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading packets:', error);
    return [];
  }
};

const savePacket = async (packet) => {
  try {
    await initializeFiles();
    const packets = await getPackets();
    
    // Add packet to beginning of array
    packets.unshift(packet);
    
    // Keep only last 10000 packets to prevent huge files
    const maxPackets = 10000;
    if (packets.length > maxPackets) {
      packets.splice(maxPackets);
    }
    
    await fs.writeFile(PACKETS_FILE, JSON.stringify(packets, null, 2));
    return true;
  } catch (error) {
    console.error('Error saving packet:', error);
    return false;
  }
};

const savePackets = async (packets) => {
  try {
    await initializeFiles();
    const existingPackets = await getPackets();
    
    // Add new packets to beginning
    const allPackets = [...packets, ...existingPackets];
    
    // Keep only last 10000 packets
    const maxPackets = 10000;
    if (allPackets.length > maxPackets) {
      allPackets.splice(maxPackets);
    }
    
    await fs.writeFile(PACKETS_FILE, JSON.stringify(allPackets, null, 2));
    return true;
  } catch (error) {
    console.error('Error saving packets:', error);
    return false;
  }
};

// Alert operations
const getAlerts = async () => {
  try {
    await initializeFiles();
    const data = await fs.readFile(ALERTS_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading alerts:', error);
    return [];
  }
};

const saveAlert = async (alert) => {
  try {
    await initializeFiles();
    const alerts = await getAlerts();
    
    // Add alert to beginning of array
    alerts.unshift(alert);
    
    // Keep only last 5000 alerts
    const maxAlerts = 5000;
    if (alerts.length > maxAlerts) {
      alerts.splice(maxAlerts);
    }
    
    await fs.writeFile(ALERTS_FILE, JSON.stringify(alerts, null, 2));
    return true;
  } catch (error) {
    console.error('Error saving alert:', error);
    return false;
  }
};

const deleteAlert = async (alertId) => {
  try {
    await initializeFiles();
    const alerts = await getAlerts();
    const filteredAlerts = alerts.filter(alert => alert.id !== alertId);
    
    if (filteredAlerts.length === alerts.length) {
      return false; // Alert not found
    }
    
    await fs.writeFile(ALERTS_FILE, JSON.stringify(filteredAlerts, null, 2));
    return true;
  } catch (error) {
    console.error('Error deleting alert:', error);
    return false;
  }
};

const clearAllAlerts = async () => {
  try {
    await initializeFiles();
    await fs.writeFile(ALERTS_FILE, JSON.stringify([], null, 2));
    return true;
  } catch (error) {
    console.error('Error clearing alerts:', error);
    return false;
  }
};

// Utility functions
const getFileStats = async () => {
  try {
    await initializeFiles();
    
    const packetsStats = await fs.stat(PACKETS_FILE);
    const alertsStats = await fs.stat(ALERTS_FILE);
    
    return {
      packets: {
        size: packetsStats.size,
        modified: packetsStats.mtime
      },
      alerts: {
        size: alertsStats.size,
        modified: alertsStats.mtime
      }
    };
  } catch (error) {
    console.error('Error getting file stats:', error);
    return null;
  }
};

module.exports = {
  // Packet operations
  getPackets,
  savePacket,
  savePackets,
  
  // Alert operations
  getAlerts,
  saveAlert,
  deleteAlert,
  clearAllAlerts,
  
  // Utility functions
  getFileStats,
  initializeFiles
};
