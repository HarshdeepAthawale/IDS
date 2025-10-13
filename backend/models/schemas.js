/**
 * Data schemas and validation for IDS system
 */

// Packet schema
const packetSchema = {
  id: 'string',
  timestamp: 'number',
  src_ip: 'string',
  dst_ip: 'string',
  protocol: 'string',
  src_port: 'number',
  dst_port: 'number',
  size: 'number',
  flags: 'string',
  source: 'string' // 'capture', 'manual_test', etc.
};

// Alert schema
const alertSchema = {
  id: 'string',
  timestamp: 'number',
  type: 'string', // 'dos', 'port_scan', 'suspicious_volume'
  severity: 'string', // 'low', 'medium', 'high', 'critical'
  source_ip: 'string',
  description: 'string',
  details: 'object',
  status: 'string' // 'active', 'acknowledged', 'resolved'
};

// Detection thresholds
const thresholds = {
  dos: {
    packets_per_second: 100,
    time_window: 60000 // 1 minute
  },
  port_scan: {
    unique_ports: 20,
    time_window: 10000 // 10 seconds
  },
  suspicious_volume: {
    bytes_per_second: 10 * 1024 * 1024, // 10MB
    time_window: 5000 // 5 seconds
  }
};

// Severity levels
const severityLevels = {
  low: { priority: 1, color: '#10B981', description: 'Low risk' },
  medium: { priority: 2, color: '#F59E0B', description: 'Medium risk' },
  high: { priority: 3, color: '#EF4444', description: 'High risk' },
  critical: { priority: 4, color: '#DC2626', description: 'Critical risk' }
};

// Alert types
const alertTypes = {
  dos: {
    name: 'Denial of Service',
    description: 'High packet rate detected from source IP',
    defaultSeverity: 'high'
  },
  port_scan: {
    name: 'Port Scan',
    description: 'Multiple ports accessed from single source IP',
    defaultSeverity: 'medium'
  },
  suspicious_volume: {
    name: 'Suspicious Traffic Volume',
    description: 'Unusually high data volume from source IP',
    defaultSeverity: 'medium'
  }
};

// Validation functions
const validatePacket = (packet) => {
  const errors = [];
  
  if (!packet.id || typeof packet.id !== 'string') {
    errors.push('Invalid or missing packet ID');
  }
  
  if (!packet.timestamp || typeof packet.timestamp !== 'number') {
    errors.push('Invalid or missing timestamp');
  }
  
  if (!packet.src_ip || typeof packet.src_ip !== 'string') {
    errors.push('Invalid or missing source IP');
  }
  
  if (!packet.dst_ip || typeof packet.dst_ip !== 'string') {
    errors.push('Invalid or missing destination IP');
  }
  
  if (!packet.protocol || typeof packet.protocol !== 'string') {
    errors.push('Invalid or missing protocol');
  }
  
  return errors;
};

const validateAlert = (alert) => {
  const errors = [];
  
  if (!alert.id || typeof alert.id !== 'string') {
    errors.push('Invalid or missing alert ID');
  }
  
  if (!alert.timestamp || typeof alert.timestamp !== 'number') {
    errors.push('Invalid or missing timestamp');
  }
  
  if (!alert.type || typeof alert.type !== 'string') {
    errors.push('Invalid or missing alert type');
  }
  
  if (!alert.severity || typeof alert.severity !== 'string') {
    errors.push('Invalid or missing severity');
  }
  
  if (!alert.source_ip || typeof alert.source_ip !== 'string') {
    errors.push('Invalid or missing source IP');
  }
  
  if (!severityLevels[alert.severity]) {
    errors.push('Invalid severity level');
  }
  
  if (!alertTypes[alert.type]) {
    errors.push('Invalid alert type');
  }
  
  return errors;
};

const validateStats = (stats) => {
  const errors = [];
  
  if (!stats || typeof stats !== 'object') {
    errors.push('Stats must be an object');
    return errors;
  }
  
  if (typeof stats.packets_per_sec !== 'number') {
    errors.push('Invalid or missing packets_per_sec');
  }
  
  if (typeof stats.total_intrusions !== 'number') {
    errors.push('Invalid or missing total_intrusions');
  }
  
  if (typeof stats.traffic_mb_per_sec !== 'number') {
    errors.push('Invalid or missing traffic_mb_per_sec');
  }
  
  if (!Array.isArray(stats.top_suspicious_ips)) {
    errors.push('Invalid or missing top_suspicious_ips');
  }
  
  return errors;
};

// Helper functions
const generateId = () => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toISOString();
};

const formatBytes = (bytes) => {
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 Bytes';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
};

const formatDuration = (milliseconds) => {
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
};

module.exports = {
  packetSchema,
  alertSchema,
  thresholds,
  severityLevels,
  alertTypes,
  validatePacket,
  validateAlert,
  validateStats,
  generateId,
  formatTimestamp,
  formatBytes,
  formatDuration
};
