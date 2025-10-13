#!/usr/bin/env node

/**
 * Attack Simulation Script
 * 
 * This script simulates various types of network attacks to test IDS detection capabilities.
 * Run with: node backend/scripts/simulateAttack.js [attack-type]
 * 
 * Attack types: dos, portscan, volume, mixed
 */

const axios = require('axios');
const { performance } = require('perf_hooks');

const API_BASE_URL = process.env.BACKEND_URL || 'http://localhost:5000';

class AttackSimulator {
  constructor() {
    this.attacks = {
      dos: this.simulateDoS.bind(this),
      portscan: this.simulatePortScan.bind(this),
      volume: this.simulateHighVolume.bind(this),
      mixed: this.simulateMixedAttack.bind(this)
    };
  }

  async simulateDoS(packetsPerSecond = 120, durationSeconds = 30) {
    console.log(`🚨 Simulating DoS Attack: ${packetsPerSecond} pps for ${durationSeconds}s`);
    
    const startTime = performance.now();
    const packetInterval = 1000 / packetsPerSecond;
    let packetCount = 0;

    const attackPackets = Array.from({ length: packetsPerSecond * durationSeconds }, (_, i) => ({
      src_ip: `192.168.1.${200 + (i % 10)}`, // Rotate source IPs
      dst_ip: '192.168.1.1',
      protocol: 'TCP',
      src_port: 12345 + (i % 1000),
      dst_port: 80,
      size: 64,
      flags: 'SYN'
    }));

    for (const packet of attackPackets) {
      try {
        await axios.post(`${API_BASE_URL}/api/packets`, packet);
        packetCount++;
        
        if (packetCount % 100 === 0) {
          console.log(`📦 Injected ${packetCount} DoS packets...`);
        }
        
        await new Promise(resolve => setTimeout(resolve, packetInterval));
      } catch (error) {
        console.error(`❌ Failed to inject DoS packet:`, error.message);
      }
    }

    const endTime = performance.now();
    console.log(`✅ DoS simulation completed: ${packetCount} packets in ${Math.round((endTime - startTime) / 1000)}s`);
  }

  async simulatePortScan(portsToScan = 50, delayMs = 100) {
    console.log(`🔍 Simulating Port Scan: ${portsToScan} ports`);
    
    const commonPorts = [20, 21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3389, 5900, 8080];
    const additionalPorts = Array.from({ length: portsToScan - commonPorts.length }, (_, i) => 1024 + i);
    const allPorts = [...commonPorts, ...additionalPorts].slice(0, portsToScan);

    for (let i = 0; i < allPorts.length; i++) {
      const packet = {
        src_ip: '192.168.1.180',
        dst_ip: '192.168.1.1',
        protocol: 'TCP',
        src_port: 12345 + i,
        dst_port: allPorts[i],
        size: 64,
        flags: 'SYN'
      };

      try {
        await axios.post(`${API_BASE_URL}/api/packets`, packet);
        console.log(`🎯 Scanning port ${allPorts[i]}...`);
        
        await new Promise(resolve => setTimeout(resolve, delayMs));
      } catch (error) {
        console.error(`❌ Failed to inject port scan packet:`, error.message);
      }
    }

    console.log(`✅ Port scan simulation completed: ${allPorts.length} ports scanned`);
  }

  async simulateHighVolume(mbPerSecond = 15, durationSeconds = 10) {
    console.log(`📈 Simulating High Volume Traffic: ${mbPerSecond} MB/s for ${durationSeconds}s`);
    
    const bytesPerSecond = mbPerSecond * 1024 * 1024;
    const packetSize = 1024 * 1024; // 1MB packets
    const packetsPerSecond = Math.ceil(bytesPerSecond / packetSize);
    const totalPackets = packetsPerSecond * durationSeconds;

    for (let i = 0; i < totalPackets; i++) {
      const packet = {
        src_ip: '192.168.1.190',
        dst_ip: '192.168.1.1',
        protocol: 'TCP',
        src_port: 12345 + (i % 100),
        dst_port: 443,
        size: packetSize,
        flags: 'ACK'
      };

      try {
        await axios.post(`${API_BASE_URL}/api/packets`, packet);
        
        if (i % 10 === 0) {
          console.log(`📊 Injected ${i + 1}/${totalPackets} high-volume packets...`);
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000 / packetsPerSecond));
      } catch (error) {
        console.error(`❌ Failed to inject high-volume packet:`, error.message);
      }
    }

    console.log(`✅ High volume simulation completed: ${totalPackets} packets`);
  }

  async simulateMixedAttack() {
    console.log('🎭 Simulating Mixed Attack Scenario');
    console.log('=====================================\n');

    // Phase 1: Reconnaissance (port scan)
    console.log('📋 Phase 1: Reconnaissance');
    await this.simulatePortScan(15, 200);
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Phase 2: DoS Attack
    console.log('\n💥 Phase 2: DoS Attack');
    await this.simulateDoS(80, 20);
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Phase 3: High Volume Data Exfiltration
    console.log('\n📤 Phase 3: Data Exfiltration');
    await this.simulateHighVolume(12, 15);

    console.log('\n✅ Mixed attack simulation completed!');
  }

  async checkAlerts() {
    console.log('\n🔍 Checking for generated alerts...');
    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait for IDS processing

    try {
      const alertsResponse = await axios.get(`${API_BASE_URL}/api/alerts?limit=20`);
      const alerts = alertsResponse.data.alerts || [];
      
      console.log(`📊 Found ${alerts.length} alerts:`);
      
      const alertTypes = {};
      alerts.forEach(alert => {
        alertTypes[alert.type] = (alertTypes[alert.type] || 0) + 1;
      });

      Object.entries(alertTypes).forEach(([type, count]) => {
        console.log(`  - ${type}: ${count} alerts`);
      });

      // Show recent alerts
      console.log('\n📋 Recent Alerts:');
      alerts.slice(0, 10).forEach((alert, index) => {
        const time = new Date(alert.timestamp).toLocaleTimeString();
        console.log(`  ${index + 1}. [${time}] ${alert.type.toUpperCase()} - ${alert.severity.toUpperCase()} from ${alert.source_ip}`);
      });

    } catch (error) {
      console.error('❌ Failed to check alerts:', error.message);
    }
  }

  async runAttack(attackType = 'mixed') {
    if (!this.attacks[attackType]) {
      console.error(`❌ Unknown attack type: ${attackType}`);
      console.log('Available types: dos, portscan, volume, mixed');
      return;
    }

    console.log(`🎯 Starting ${attackType.toUpperCase()} attack simulation`);
    console.log('==========================================\n');

    const startTime = performance.now();
    
    try {
      await this.attacks[attackType]();
      
      const endTime = performance.now();
      console.log(`\n⏱️  Attack simulation took ${Math.round((endTime - startTime) / 1000)}s`);
      
      await this.checkAlerts();
      
    } catch (error) {
      console.error('❌ Attack simulation failed:', error.message);
    }
  }
}

// Command line interface
async function main() {
  const attackType = process.argv[2] || 'mixed';
  
  console.log('🚨 IDS Attack Simulation Script');
  console.log('=================================\n');
  
  console.log('⚠️  WARNING: This script simulates network attacks for testing purposes only!');
  console.log('   Make sure you have permission to run this on your network.\n');

  const simulator = new AttackSimulator();
  await simulator.runAttack(attackType);
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = AttackSimulator;
