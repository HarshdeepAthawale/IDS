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

module.exports = {
  getPackets,
  createPacket,
  getRecentPackets
};
