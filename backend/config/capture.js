/**
 * Packet capture configuration
 */

const config = {
  // Default capture settings
  defaultInterface: 'any',
  defaultFilter: '',
  
  // Buffer settings
  bufferSize: 100,
  saveInterval: 5000, // 5 seconds
  
  // Capture limits
  maxPacketsPerSecond: 10000,
  maxPacketSize: 65536,
  
  // Common filters
  filters: {
    tcp: 'tcp',
    udp: 'udp',
    icmp: 'icmp',
    http: 'tcp port 80',
    https: 'tcp port 443',
    dns: 'udp port 53',
    dhcp: 'udp port 67 or udp port 68',
    ssh: 'tcp port 22',
    ftp: 'tcp port 21',
    smtp: 'tcp port 25',
    pop3: 'tcp port 110',
    imap: 'tcp port 143',
    snmp: 'udp port 161',
    ntp: 'udp port 123',
    telnet: 'tcp port 23',
    rdp: 'tcp port 3389',
    vnc: 'tcp port 5900',
    mysql: 'tcp port 3306',
    postgresql: 'tcp port 5432',
    mongodb: 'tcp port 27017',
    redis: 'tcp port 6379',
    elasticsearch: 'tcp port 9200',
    kibana: 'tcp port 5601',
    grafana: 'tcp port 3000',
    jenkins: 'tcp port 8080',
    docker: 'tcp port 2376',
    kubernetes: 'tcp port 6443'
  },
  
  // Interface detection
  interfaceDetection: {
    excludeLoopback: true,
    excludeVirtual: false,
    preferEthernet: true,
    preferWireless: false
  },
  
  // Performance settings
  performance: {
    enablePromiscuousMode: true,
    enableImmediateMode: false,
    bufferSize: 1024 * 1024, // 1MB
    timeout: 1000 // 1 second
  },
  
  // Security settings
  security: {
    allowedInterfaces: [], // Empty = all interfaces allowed
    blockedIPs: [
      '127.0.0.1',
      '::1'
    ],
    blockedPorts: [],
    requireAuthentication: false
  },
  
  // Logging settings
  logging: {
    logPackets: false, // Set to true for debugging
    logErrors: true,
    logStats: true,
    statsInterval: 30000 // 30 seconds
  }
};

/**
 * Get configuration value
 */
const getConfig = (key, defaultValue = null) => {
  const keys = key.split('.');
  let value = config;
  
  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k];
    } else {
      return defaultValue;
    }
  }
  
  return value;
};

/**
 * Set configuration value
 */
const setConfig = (key, value) => {
  const keys = key.split('.');
  let current = config;
  
  for (let i = 0; i < keys.length - 1; i++) {
    const k = keys[i];
    if (!(k in current) || typeof current[k] !== 'object') {
      current[k] = {};
    }
    current = current[k];
  }
  
  current[keys[keys.length - 1]] = value;
};

/**
 * Get available filters
 */
const getAvailableFilters = () => {
  return Object.keys(config.filters).map(key => ({
    key,
    name: key.toUpperCase(),
    filter: config.filters[key],
    description: getFilterDescription(key)
  }));
};

/**
 * Get filter description
 */
const getFilterDescription = (filterKey) => {
  const descriptions = {
    tcp: 'Capture TCP packets only',
    udp: 'Capture UDP packets only',
    icmp: 'Capture ICMP packets only',
    http: 'Capture HTTP traffic (port 80)',
    https: 'Capture HTTPS traffic (port 443)',
    dns: 'Capture DNS queries (port 53)',
    dhcp: 'Capture DHCP traffic (ports 67, 68)',
    ssh: 'Capture SSH traffic (port 22)',
    ftp: 'Capture FTP traffic (port 21)',
    smtp: 'Capture SMTP traffic (port 25)',
    pop3: 'Capture POP3 traffic (port 110)',
    imap: 'Capture IMAP traffic (port 143)',
    snmp: 'Capture SNMP traffic (port 161)',
    ntp: 'Capture NTP traffic (port 123)',
    telnet: 'Capture Telnet traffic (port 23)',
    rdp: 'Capture RDP traffic (port 3389)',
    vnc: 'Capture VNC traffic (port 5900)',
    mysql: 'Capture MySQL traffic (port 3306)',
    postgresql: 'Capture PostgreSQL traffic (port 5432)',
    mongodb: 'Capture MongoDB traffic (port 27017)',
    redis: 'Capture Redis traffic (port 6379)',
    elasticsearch: 'Capture Elasticsearch traffic (port 9200)',
    kibana: 'Capture Kibana traffic (port 5601)',
    grafana: 'Capture Grafana traffic (port 3000)',
    jenkins: 'Capture Jenkins traffic (port 8080)',
    docker: 'Capture Docker traffic (port 2376)',
    kubernetes: 'Capture Kubernetes traffic (port 6443)'
  };
  
  return descriptions[filterKey] || 'Custom filter';
};

/**
 * Validate filter syntax
 */
const validateFilter = (filter) => {
  if (!filter || typeof filter !== 'string') {
    return { valid: false, error: 'Filter must be a string' };
  }
  
  // Basic validation - check for common syntax errors
  const commonErrors = [
    { pattern: /[^a-zA-Z0-9\s\.\:\,\!\=\<\>\(\)\[\]\&\|\-\+\*\/\%]/, message: 'Invalid characters in filter' },
    { pattern: /\s+and\s+and\s+/, message: 'Consecutive AND operators' },
    { pattern: /\s+or\s+or\s+/, message: 'Consecutive OR operators' },
    { pattern: /^\s*(and|or)\s+/, message: 'Filter cannot start with AND/OR' },
    { pattern: /\s+(and|or)\s*$/, message: 'Filter cannot end with AND/OR' }
  ];
  
  for (const error of commonErrors) {
    if (error.pattern.test(filter)) {
      return { valid: false, error: error.message };
    }
  }
  
  return { valid: true };
};

/**
 * Get recommended filters for common scenarios
 */
const getRecommendedFilters = () => {
  return {
    web_traffic: 'tcp port 80 or tcp port 443',
    email_traffic: 'tcp port 25 or tcp port 110 or tcp port 143 or tcp port 993 or tcp port 995',
    database_traffic: 'tcp port 3306 or tcp port 5432 or tcp port 27017 or tcp port 6379',
    monitoring_traffic: 'tcp port 9200 or tcp port 5601 or tcp port 3000',
    development_traffic: 'tcp port 8080 or tcp port 3000 or tcp port 4200 or tcp port 5000',
    security_traffic: 'tcp port 22 or tcp port 3389 or tcp port 5900',
    network_services: 'udp port 53 or udp port 67 or udp port 68 or udp port 123 or udp port 161'
  };
};

module.exports = {
  config,
  getConfig,
  setConfig,
  getAvailableFilters,
  getFilterDescription,
  validateFilter,
  getRecommendedFilters
};
