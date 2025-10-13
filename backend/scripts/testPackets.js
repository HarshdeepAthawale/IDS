#!/usr/bin/env node

/**
 * Test Packet Injection Script
 * 
 * This script injects test packets to verify the IDS system is working correctly.
 * Run with: node backend/scripts/testPackets.js
 */

const axios = require('axios');

const API_BASE_URL = process.env.BACKEND_URL || 'http://localhost:5000';

// Test packet configurations
const testPackets = [
  {
    name: 'Normal HTTP Traffic',
    packets: [
      { src_ip: '192.168.1.100', dst_ip: '192.168.1.1', protocol: 'TCP', src_port: 12345, dst_port: 80, size: 1024, flags: 'SYN' },
      { src_ip: '192.168.1.100', dst_ip: '192.168.1.1', protocol: 'TCP', src_port: 12345, dst_port: 80, size: 2048, flags: 'ACK' },
      { src_ip: '192.168.1.100', dst_ip: '192.168.1.1', protocol: 'TCP', src_port: 12345, dst_port: 80, size: 512, flags: 'FIN' }
    ]
  },
  {
    name: 'DoS Attack Simulation',
    packets: Array.from({ length: 150 }, (_, i) => ({
      src_ip: '192.168.1.200',
      dst_ip: '192.168.1.1',
      protocol: 'TCP',
      src_port: 12345 + i,
      dst_port: 80,
      size: 64,
      flags: 'SYN'
    }))
  },
  {
    name: 'Port Scan Simulation',
    packets: Array.from({ length: 25 }, (_, i) => ({
      src_ip: '192.168.1.150',
      dst_ip: '192.168.1.1',
      protocol: 'TCP',
      src_port: 12345,
      dst_port: 20 + i,
      size: 64,
      flags: 'SYN'
    }))
  },
  {
    name: 'High Volume Traffic',
    packets: Array.from({ length: 50 }, (_, i) => ({
      src_ip: '192.168.1.175',
      dst_ip: '192.168.1.1',
      protocol: 'TCP',
      src_port: 12345 + i,
      dst_port: 443,
      size: 1024 * 1024, // 1MB per packet
      flags: 'ACK'
    }))
  }
];

async function injectTestPackets() {
  console.log('🧪 Starting packet injection tests...\n');

  try {
    // Test API connectivity
    console.log('🔍 Testing API connectivity...');
    const healthCheck = await axios.get(`${API_BASE_URL}/health`);
    console.log('✅ API is responsive:', healthCheck.data.status);

    // Inject test packets
    for (const test of testPackets) {
      console.log(`\n📦 Injecting ${test.name} (${test.packets.length} packets)...`);
      
      let successCount = 0;
      let errorCount = 0;

      for (const packet of test.packets) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/packets`, packet);
          if (response.status === 201) {
            successCount++;
          }
        } catch (error) {
          errorCount++;
          console.error(`❌ Failed to inject packet:`, error.response?.data || error.message);
        }
        
        // Small delay to simulate real traffic
        await new Promise(resolve => setTimeout(resolve, 10));
      }

      console.log(`✅ Injected ${successCount} packets successfully`);
      if (errorCount > 0) {
        console.log(`❌ ${errorCount} packets failed to inject`);
      }

      // Wait between test scenarios
      await new Promise(resolve => setTimeout(resolve, 2000));
    }

    console.log('\n🎯 Checking for generated alerts...');
    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait for IDS processing

    const alertsResponse = await axios.get(`${API_BASE_URL}/api/alerts?limit=10`);
    const alerts = alertsResponse.data.alerts || [];
    
    console.log(`📊 Found ${alerts.length} recent alerts:`);
    alerts.forEach((alert, index) => {
      console.log(`  ${index + 1}. ${alert.type.toUpperCase()} - ${alert.severity.toUpperCase()} from ${alert.source_ip}`);
    });

    console.log('\n✅ Packet injection tests completed!');
    console.log('\n💡 Check the dashboard to see real-time updates and alerts.');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
    process.exit(1);
  }
}

async function checkSystemStatus() {
  console.log('🔍 Checking system status...\n');
  
  try {
    const [health, stats, alerts] = await Promise.all([
      axios.get(`${API_BASE_URL}/health`),
      axios.get(`${API_BASE_URL}/api/stats`),
      axios.get(`${API_BASE_URL}/api/alerts?limit=5`)
    ]);

    console.log('📊 System Status:');
    console.log(`  Health: ${health.data.status}`);
    console.log(`  Uptime: ${Math.floor(health.data.uptime)} seconds`);
    console.log(`  Packets/sec: ${stats.data.packets_per_second}`);
    console.log(`  Total Intrusions: ${stats.data.total_intrusions}`);
    console.log(`  Recent Alerts: ${alerts.data.alerts?.length || 0}`);

  } catch (error) {
    console.error('❌ Failed to check system status:', error.message);
  }
}

// Main execution
async function main() {
  console.log('🚀 IDS Test Packet Injection Script');
  console.log('=====================================\n');

  await checkSystemStatus();
  console.log('\n' + '='.repeat(50) + '\n');
  await injectTestPackets();
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { injectTestPackets, checkSystemStatus };
