const storage = require('../utils/storage');
const { v4: uuidv4 } = require('uuid');

/**
 * Get paginated packets
 */
const getPackets = async (req, res) => {
  try {
    const { 
      page = 1, 
      limit = 100,
      protocol,
      source_ip,
      dest_ip,
      start_date,
      end_date
    } = req.query;

    const packets = await storage.getPackets();
    
    // Apply filters
    let filteredPackets = packets;
    
    if (protocol) {
      filteredPackets = filteredPackets.filter(packet => packet.protocol === protocol);
    }
    
    if (source_ip) {
      filteredPackets = filteredPackets.filter(packet => packet.src_ip === source_ip);
    }
    
    if (dest_ip) {
      filteredPackets = filteredPackets.filter(packet => packet.dst_ip === dest_ip);
    }
    
    if (start_date) {
      const startTime = new Date(start_date).getTime();
      filteredPackets = filteredPackets.filter(packet => packet.timestamp >= startTime);
    }
    
    if (end_date) {
      const endTime = new Date(end_date).getTime();
      filteredPackets = filteredPackets.filter(packet => packet.timestamp <= endTime);
    }

    // Sort by timestamp (newest first)
    filteredPackets.sort((a, b) => b.timestamp - a.timestamp);

    // Pagination
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + parseInt(limit);
    const paginatedPackets = filteredPackets.slice(startIndex, endIndex);

    res.json({
      packets: paginatedPackets,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: filteredPackets.length,
        pages: Math.ceil(filteredPackets.length / limit)
      }
    });
  } catch (error) {
    console.error('Error getting packets:', error);
    res.status(500).json({ error: 'Failed to retrieve packets' });
  }
};

/**
 * Create a test packet (for testing purposes)
 */
const createPacket = async (req, res) => {
  try {
    const {
      src_ip = '192.168.1.100',
      dst_ip = '192.168.1.1',
      protocol = 'TCP',
      src_port = 80,
      dst_port = 443,
      size = 1024,
      flags = 'SYN'
    } = req.body;

    const packet = {
      id: uuidv4(),
      timestamp: Date.now(),
      src_ip,
      dst_ip,
      protocol,
      src_port,
      dst_port,
      size,
      flags,
      source: 'manual_test'
    };

    await storage.savePacket(packet);

    res.status(201).json({
      message: 'Test packet created successfully',
      packet
    });
  } catch (error) {
    console.error('Error creating packet:', error);
    res.status(500).json({ error: 'Failed to create packet' });
  }
};

/**
 * Get recent packets (last 5 minutes)
 */
const getRecentPackets = async (req, res) => {
  try {
    const { limit = 100 } = req.query;
    const packets = await storage.getPackets();
    
    const fiveMinutesAgo = Date.now() - 300000; // 5 minutes ago
    const recentPackets = packets
      .filter(packet => packet.timestamp >= fiveMinutesAgo)
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, parseInt(limit));

    res.json({
      packets: recentPackets,
      count: recentPackets.length,
      timestamp: Date.now()
    });
  } catch (error) {
    console.error('Error getting recent packets:', error);
    res.status(500).json({ error: 'Failed to retrieve recent packets' });
  }
};

/**
 * Get packet statistics
 */
const getPacketStats = async (req, res) => {
  try {
    const { time_range = '1h' } = req.query;
    const packets = await storage.getPackets();
    
    const now = Date.now();
    let timeWindow;
    
    switch (time_range) {
      case '5m':
        timeWindow = 300000; // 5 minutes
        break;
      case '1h':
        timeWindow = 3600000; // 1 hour
        break;
      case '24h':
        timeWindow = 86400000; // 24 hours
        break;
      case '7d':
        timeWindow = 604800000; // 7 days
        break;
      default:
        timeWindow = 3600000; // Default to 1 hour
    }
    
    const recentPackets = packets.filter(p => p.timestamp >= (now - timeWindow));
    
    // Protocol distribution
    const protocolCounts = {};
    recentPackets.forEach(packet => {
      protocolCounts[packet.protocol] = (protocolCounts[packet.protocol] || 0) + 1;
    });
    
    const topProtocols = Object.entries(protocolCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([protocol, count]) => ({ protocol, count }));
    
    // Source IP distribution
    const sourceIPCounts = {};
    recentPackets.forEach(packet => {
      sourceIPCounts[packet.src_ip] = (sourceIPCounts[packet.src_ip] || 0) + 1;
    });
    
    const topSourceIPs = Object.entries(sourceIPCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([ip, count]) => ({ ip, count }));
    
    // Destination IP distribution
    const destIPCounts = {};
    recentPackets.forEach(packet => {
      destIPCounts[packet.dst_ip] = (destIPCounts[packet.dst_ip] || 0) + 1;
    });
    
    const topDestIPs = Object.entries(destIPCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([ip, count]) => ({ ip, count }));
    
    // Port distribution
    const portCounts = {};
    recentPackets.forEach(packet => {
      if (packet.dst_port) {
        portCounts[packet.dst_port] = (portCounts[packet.dst_port] || 0) + 1;
      }
    });
    
    const topPorts = Object.entries(portCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([port, count]) => ({ port: parseInt(port), count }));
    
    // Size statistics
    const sizes = recentPackets.map(p => p.size || 0);
    const totalBytes = sizes.reduce((sum, size) => sum + size, 0);
    const avgSize = sizes.length > 0 ? totalBytes / sizes.length : 0;
    const maxSize = Math.max(...sizes);
    const minSize = Math.min(...sizes.filter(s => s > 0));
    
    res.json({
      time_range,
      total_packets: recentPackets.length,
      total_bytes: totalBytes,
      total_mb: totalBytes / (1024 * 1024),
      avg_packet_size: Math.round(avgSize),
      max_packet_size: maxSize,
      min_packet_size: minSize,
      top_protocols: topProtocols,
      top_source_ips: topSourceIPs,
      top_dest_ips: topDestIPs,
      top_ports: topPorts,
      timestamp: now
    });
  } catch (error) {
    console.error('Error getting packet stats:', error);
    res.status(500).json({ error: 'Failed to retrieve packet statistics' });
  }
};

/**
 * Export packets to CSV format
 */
const exportPackets = async (req, res) => {
  try {
    const { 
      format = 'csv',
      start_date,
      end_date,
      protocol,
      source_ip,
      dest_ip
    } = req.query;
    
    const packets = await storage.getPackets();
    
    // Apply filters
    let filteredPackets = packets;
    
    if (start_date) {
      const startTime = new Date(start_date).getTime();
      filteredPackets = filteredPackets.filter(packet => packet.timestamp >= startTime);
    }
    
    if (end_date) {
      const endTime = new Date(end_date).getTime();
      filteredPackets = filteredPackets.filter(packet => packet.timestamp <= endTime);
    }
    
    if (protocol) {
      filteredPackets = filteredPackets.filter(packet => packet.protocol === protocol);
    }
    
    if (source_ip) {
      filteredPackets = filteredPackets.filter(packet => packet.src_ip === source_ip);
    }
    
    if (dest_ip) {
      filteredPackets = filteredPackets.filter(packet => packet.dst_ip === dest_ip);
    }
    
    // Sort by timestamp (newest first)
    filteredPackets.sort((a, b) => b.timestamp - a.timestamp);
    
    if (format === 'csv') {
      // Generate CSV
      const headers = ['timestamp', 'src_ip', 'dst_ip', 'protocol', 'src_port', 'dst_port', 'size', 'flags', 'source'];
      const csvRows = [headers.join(',')];
      
      filteredPackets.forEach(packet => {
        const row = [
          new Date(packet.timestamp).toISOString(),
          packet.src_ip,
          packet.dst_ip,
          packet.protocol,
          packet.src_port || '',
          packet.dst_port || '',
          packet.size || '',
          packet.flags || '',
          packet.source || ''
        ];
        csvRows.push(row.join(','));
      });
      
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="packets_${Date.now()}.csv"`);
      res.send(csvRows.join('\n'));
    } else {
      res.json({
        packets: filteredPackets,
        count: filteredPackets.length,
        filters: { start_date, end_date, protocol, source_ip, dest_ip },
        timestamp: Date.now()
      });
    }
  } catch (error) {
    console.error('Error exporting packets:', error);
    res.status(500).json({ error: 'Failed to export packets' });
  }
};
