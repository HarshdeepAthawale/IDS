/**
 * Configurable detection thresholds for IDS engine
 */

const defaultThresholds = {
  // DoS Detection
  dos: {
    packets_per_second: 100,
    time_window_ms: 60000, // 1 minute
    severity: 'high',
    enabled: true,
    description: 'Detect high packet rate attacks (DoS/DDoS)'
  },

  // Port Scan Detection
  port_scan: {
    unique_ports: 20,
    time_window_ms: 10000, // 10 seconds
    severity: 'medium',
    enabled: true,
    description: 'Detect port scanning attempts'
  },

  // Suspicious Volume Detection
  suspicious_volume: {
    mb_per_second: 10,
    time_window_ms: 5000, // 5 seconds
    severity: 'medium',
    enabled: true,
    description: 'Detect unusually high data volume'
  },

  // Brute Force Detection
  brute_force: {
    failed_attempts: 5,
    time_window_ms: 300000, // 5 minutes
    severity: 'high',
    enabled: false,
    description: 'Detect brute force login attempts'
  },

  // Suspicious Protocol Detection
  suspicious_protocol: {
    protocols: ['ICMP', 'GRE', 'ESP'],
    time_window_ms: 30000, // 30 seconds
    severity: 'low',
    enabled: false,
    description: 'Detect unusual protocol usage'
  },

  // Geographic Anomaly Detection
  geo_anomaly: {
    enabled: false,
    severity: 'medium',
    description: 'Detect traffic from unusual geographic locations'
  },

  // Time-based Anomaly Detection
  time_anomaly: {
    enabled: false,
    severity: 'low',
    description: 'Detect traffic during unusual hours'
  }
};

/**
 * Severity levels configuration
 */
const severityConfig = {
  low: {
    priority: 1,
    color: '#10B981',
    description: 'Low risk - Monitor',
    notification: false
  },
  medium: {
    priority: 2,
    color: '#F59E0B',
    description: 'Medium risk - Investigate',
    notification: true
  },
  high: {
    priority: 3,
    color: '#EF4444',
    description: 'High risk - Immediate action',
    notification: true
  },
  critical: {
    priority: 4,
    color: '#DC2626',
    description: 'Critical risk - Emergency response',
    notification: true
  }
};

/**
 * Alert types configuration
 */
const alertTypeConfig = {
  dos: {
    name: 'Denial of Service',
    description: 'High packet rate detected from source IP',
    defaultSeverity: 'high',
    mitigation: 'Rate limiting, DDoS protection',
    category: 'availability'
  },
  port_scan: {
    name: 'Port Scan',
    description: 'Multiple ports accessed from single source IP',
    defaultSeverity: 'medium',
    mitigation: 'Port filtering, access control',
    category: 'reconnaissance'
  },
  suspicious_volume: {
    name: 'Suspicious Traffic Volume',
    description: 'Unusually high data volume from source IP',
    defaultSeverity: 'medium',
    mitigation: 'Bandwidth limiting, traffic analysis',
    category: 'data_exfiltration'
  },
  brute_force: {
    name: 'Brute Force Attack',
    description: 'Multiple failed login attempts',
    defaultSeverity: 'high',
    mitigation: 'Account lockout, IP blocking',
    category: 'authentication'
  },
  suspicious_protocol: {
    name: 'Suspicious Protocol Usage',
    description: 'Unusual protocol detected in traffic',
    defaultSeverity: 'low',
    mitigation: 'Protocol filtering, monitoring',
    category: 'anomaly'
  },
  geo_anomaly: {
    name: 'Geographic Anomaly',
    description: 'Traffic from unusual geographic location',
    defaultSeverity: 'medium',
    mitigation: 'Geo-blocking, enhanced monitoring',
    category: 'anomaly'
  },
  time_anomaly: {
    name: 'Time-based Anomaly',
    description: 'Traffic during unusual hours',
    defaultSeverity: 'low',
    mitigation: 'Time-based access control',
    category: 'anomaly'
  }
};

/**
 * Environment-based threshold overrides
 */
const getThresholds = () => {
  const thresholds = { ...defaultThresholds };

  // Override with environment variables if available
  if (process.env.DOS_THRESHOLD_PACKETS_PER_SEC) {
    thresholds.dos.packets_per_second = parseInt(process.env.DOS_THRESHOLD_PACKETS_PER_SEC);
  }
  
  if (process.env.DOS_TIME_WINDOW_MS) {
    thresholds.dos.time_window_ms = parseInt(process.env.DOS_TIME_WINDOW_MS);
  }

  if (process.env.PORT_SCAN_THRESHOLD_PORTS) {
    thresholds.port_scan.unique_ports = parseInt(process.env.PORT_SCAN_THRESHOLD_PORTS);
  }

  if (process.env.PORT_SCAN_TIME_WINDOW_MS) {
    thresholds.port_scan.time_window_ms = parseInt(process.env.PORT_SCAN_TIME_WINDOW_MS);
  }

  if (process.env.SUSPICIOUS_VOLUME_THRESHOLD_MB) {
    thresholds.suspicious_volume.mb_per_second = parseInt(process.env.SUSPICIOUS_VOLUME_THRESHOLD_MB);
  }

  if (process.env.SUSPICIOUS_VOLUME_TIME_WINDOW_MS) {
    thresholds.suspicious_volume.time_window_ms = parseInt(process.env.SUSPICIOUS_VOLUME_TIME_WINDOW_MS);
  }

  return thresholds;
};

/**
 * Get threshold for specific detection type
 */
const getThreshold = (detectionType) => {
  const thresholds = getThresholds();
  return thresholds[detectionType] || null;
};

/**
 * Update threshold configuration
 */
const updateThreshold = (detectionType, newConfig) => {
  const thresholds = getThresholds();
  
  if (thresholds[detectionType]) {
    thresholds[detectionType] = { ...thresholds[detectionType], ...newConfig };
    return true;
  }
  
  return false;
};

/**
 * Validate threshold configuration
 */
const validateThreshold = (detectionType, config) => {
  const errors = [];
  
  if (!config) {
    errors.push('Configuration is required');
    return errors;
  }

  switch (detectionType) {
    case 'dos':
      if (config.packets_per_second && (config.packets_per_second < 1 || config.packets_per_second > 10000)) {
        errors.push('Packets per second must be between 1 and 10000');
      }
      if (config.time_window_ms && (config.time_window_ms < 1000 || config.time_window_ms > 300000)) {
        errors.push('Time window must be between 1000ms and 300000ms');
      }
      break;
      
    case 'port_scan':
      if (config.unique_ports && (config.unique_ports < 1 || config.unique_ports > 65535)) {
        errors.push('Unique ports must be between 1 and 65535');
      }
      if (config.time_window_ms && (config.time_window_ms < 1000 || config.time_window_ms > 300000)) {
        errors.push('Time window must be between 1000ms and 300000ms');
      }
      break;
      
    case 'suspicious_volume':
      if (config.mb_per_second && (config.mb_per_second < 1 || config.mb_per_second > 1000)) {
        errors.push('MB per second must be between 1 and 1000');
      }
      if (config.time_window_ms && (config.time_window_ms < 1000 || config.time_window_ms > 300000)) {
        errors.push('Time window must be between 1000ms and 300000ms');
      }
      break;
  }

  if (config.severity && !severityConfig[config.severity]) {
    errors.push(`Invalid severity level: ${config.severity}`);
  }

  return errors;
};

/**
 * Get all available detection types
 */
const getDetectionTypes = () => {
  return Object.keys(defaultThresholds).map(type => ({
    type,
    ...defaultThresholds[type],
    ...alertTypeConfig[type]
  }));
};

/**
 * Get severity configuration
 */
const getSeverityConfig = () => {
  return severityConfig;
};

/**
 * Get alert type configuration
 */
const getAlertTypeConfig = () => {
  return alertTypeConfig;
};

/**
 * Check if detection type is enabled
 */
const isDetectionEnabled = (detectionType) => {
  const thresholds = getThresholds();
  return thresholds[detectionType]?.enabled || false;
};

/**
 * Enable/disable detection type
 */
const setDetectionEnabled = (detectionType, enabled) => {
  const thresholds = getThresholds();
  if (thresholds[detectionType]) {
    thresholds[detectionType].enabled = enabled;
    return true;
  }
  return false;
};

/**
 * Get recommended thresholds for different environments
 */
const getRecommendedThresholds = (environment = 'development') => {
  const recommendations = {
    development: {
      dos: { packets_per_second: 50, time_window_ms: 30000 },
      port_scan: { unique_ports: 10, time_window_ms: 5000 },
      suspicious_volume: { mb_per_second: 5, time_window_ms: 3000 }
    },
    staging: {
      dos: { packets_per_second: 100, time_window_ms: 60000 },
      port_scan: { unique_ports: 20, time_window_ms: 10000 },
      suspicious_volume: { mb_per_second: 10, time_window_ms: 5000 }
    },
    production: {
      dos: { packets_per_second: 200, time_window_ms: 60000 },
      port_scan: { unique_ports: 30, time_window_ms: 15000 },
      suspicious_volume: { mb_per_second: 20, time_window_ms: 5000 }
    }
  };

  return recommendations[environment] || recommendations.staging;
};

module.exports = {
  defaultThresholds,
  severityConfig,
  alertTypeConfig,
  getThresholds,
  getThreshold,
  updateThreshold,
  validateThreshold,
  getDetectionTypes,
  getSeverityConfig,
  getAlertTypeConfig,
  isDetectionEnabled,
  setDetectionEnabled,
  getRecommendedThresholds
};
