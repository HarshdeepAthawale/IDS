#!/usr/bin/env node

/**
 * Comprehensive System Test Script
 * 
 * This script performs end-to-end testing of the IDS system including:
 * - API endpoint testing
 * - WebSocket connectivity testing
 * - Detection algorithm testing
 * - Performance testing
 * 
 * Run with: node backend/scripts/testSystem.js
 */

const axios = require('axios');
const { io } = require('socket.io-client');
const { performance } = require('perf_hooks');

const API_BASE_URL = process.env.BACKEND_URL || 'http://localhost:5000';
const SOCKET_URL = process.env.BACKEND_URL || 'http://localhost:5000';

class SystemTester {
  constructor() {
    this.results = {
      api: {},
      websocket: {},
      detection: {},
      performance: {},
      overall: 'PENDING'
    };
    this.socket = null;
  }

  async runAllTests() {
    console.log('🧪 IDS System Comprehensive Test Suite');
    console.log('==========================================\n');

    try {
      // Test API endpoints
      await this.testAPIEndpoints();
      
      // Test WebSocket connectivity
      await this.testWebSocketConnection();
      
      // Test detection algorithms
      await this.testDetectionAlgorithms();
      
      // Test performance
      await this.testPerformance();
      
      // Generate report
      this.generateReport();
      
    } catch (error) {
      console.error('❌ Test suite failed:', error.message);
      this.results.overall = 'FAILED';
      process.exit(1);
    }
  }

  async testAPIEndpoints() {
    console.log('🔗 Testing API Endpoints...');
    
    const endpoints = [
      { method: 'GET', path: '/health', name: 'Health Check' },
      { method: 'GET', path: '/api/status', name: 'API Status' },
      { method: 'GET', path: '/api/stats', name: 'Statistics' },
      { method: 'GET', path: '/api/alerts?limit=5', name: 'Alerts' },
      { method: 'GET', path: '/api/packets?limit=5', name: 'Packets' },
      { method: 'GET', path: '/api/packets/status', name: 'Capture Status' },
      { method: 'GET', path: '/api/interfaces', name: 'Network Interfaces' },
      { method: 'GET', path: '/api/system/info', name: 'System Info' }
    ];

    for (const endpoint of endpoints) {
      try {
        const startTime = performance.now();
        const response = await axios({
          method: endpoint.method,
          url: `${API_BASE_URL}${endpoint.path}`,
          timeout: 5000
        });
        const endTime = performance.now();
        
        this.results.api[endpoint.name] = {
          status: 'PASS',
          statusCode: response.status,
          responseTime: Math.round(endTime - startTime),
          dataSize: JSON.stringify(response.data).length
        };
        
        console.log(`  ✅ ${endpoint.name}: ${response.status} (${Math.round(endTime - startTime)}ms)`);
        
      } catch (error) {
        this.results.api[endpoint.name] = {
          status: 'FAIL',
          error: error.message,
          statusCode: error.response?.status
        };
        
        console.log(`  ❌ ${endpoint.name}: ${error.message}`);
      }
    }
    
    console.log('');
  }

  async testWebSocketConnection() {
    console.log('📡 Testing WebSocket Connection...');
    
    return new Promise((resolve) => {
      this.socket = io(SOCKET_URL, {
        timeout: 5000,
        forceNew: true
      });

      let connectionTested = false;
      let dataReceived = false;

      // Test connection
      this.socket.on('connect', () => {
        if (!connectionTested) {
          connectionTested = true;
          this.results.websocket.connection = { status: 'PASS', latency: 'N/A' };
          console.log('  ✅ WebSocket connection established');
          
          // Request data to test data flow
          this.socket.emit('request-stats');
          this.socket.emit('request-alerts');
        }
      });

      // Test data reception
      this.socket.on('stats-update', (data) => {
        if (!dataReceived) {
          dataReceived = true;
          this.results.websocket.dataFlow = { status: 'PASS', dataReceived: true };
          console.log('  ✅ WebSocket data flow working');
        }
      });

      this.socket.on('alerts-data', (data) => {
        if (!dataReceived) {
          dataReceived = true;
          this.results.websocket.dataFlow = { status: 'PASS', dataReceived: true };
          console.log('  ✅ WebSocket data flow working');
        }
      });

      // Test error handling
      this.socket.on('connect_error', (error) => {
        this.results.websocket.connection = { status: 'FAIL', error: error.message };
        console.log('  ❌ WebSocket connection failed:', error.message);
        resolve();
      });

      // Timeout for connection test
      setTimeout(() => {
        if (!connectionTested) {
          this.results.websocket.connection = { status: 'FAIL', error: 'Connection timeout' };
          console.log('  ❌ WebSocket connection timeout');
        }
        
        if (!dataReceived) {
          this.results.websocket.dataFlow = { status: 'FAIL', error: 'No data received' };
          console.log('  ❌ WebSocket data flow timeout');
        }
        
        this.socket.disconnect();
        resolve();
      }, 10000);
    });
  }

  async testDetectionAlgorithms() {
    console.log('🎯 Testing Detection Algorithms...');
    
    const testScenarios = [
      {
        name: 'DoS Detection',
        packets: Array.from({ length: 120 }, (_, i) => ({
          src_ip: '192.168.1.200',
          dst_ip: '192.168.1.1',
          protocol: 'TCP',
          src_port: 12345 + i,
          dst_port: 80,
          size: 64,
          flags: 'SYN'
        })),
        expectedAlert: 'dos'
      },
      {
        name: 'Port Scan Detection',
        packets: Array.from({ length: 25 }, (_, i) => ({
          src_ip: '192.168.1.150',
          dst_ip: '192.168.1.1',
          protocol: 'TCP',
          src_port: 12345,
          dst_port: 20 + i,
          size: 64,
          flags: 'SYN'
        })),
        expectedAlert: 'port_scan'
      },
      {
        name: 'High Volume Detection',
        packets: Array.from({ length: 15 }, (_, i) => ({
          src_ip: '192.168.1.175',
          dst_ip: '192.168.1.1',
          protocol: 'TCP',
          src_port: 12345 + i,
          dst_port: 443,
          size: 1024 * 1024, // 1MB
          flags: 'ACK'
        })),
        expectedAlert: 'suspicious_volume'
      }
    ];

    for (const scenario of testScenarios) {
      try {
        console.log(`  🧪 Testing ${scenario.name}...`);
        
        // Inject test packets
        for (const packet of scenario.packets) {
          await axios.post(`${API_BASE_URL}/api/packets`, packet);
          await new Promise(resolve => setTimeout(resolve, 10)); // Small delay
        }
        
        // Wait for IDS processing
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Check for alerts
        const alertsResponse = await axios.get(`${API_BASE_URL}/api/alerts?limit=10`);
        const alerts = alertsResponse.data.alerts || [];
        
        const relevantAlert = alerts.find(alert => 
          alert.type === scenario.expectedAlert && 
          alert.source_ip === scenario.packets[0].src_ip
        );
        
        if (relevantAlert) {
          this.results.detection[scenario.name] = {
            status: 'PASS',
            alertFound: true,
            alertId: relevantAlert.id,
            severity: relevantAlert.severity
          };
          console.log(`    ✅ ${scenario.name} detected successfully`);
        } else {
          this.results.detection[scenario.name] = {
            status: 'FAIL',
            alertFound: false,
            expectedType: scenario.expectedAlert
          };
          console.log(`    ❌ ${scenario.name} not detected`);
        }
        
      } catch (error) {
        this.results.detection[scenario.name] = {
          status: 'FAIL',
          error: error.message
        };
        console.log(`    ❌ ${scenario.name} test failed: ${error.message}`);
      }
    }
    
    console.log('');
  }

  async testPerformance() {
    console.log('⚡ Testing Performance...');
    
    try {
      // Test API response times
      const apiTests = [];
      for (let i = 0; i < 10; i++) {
        apiTests.push(
          axios.get(`${API_BASE_URL}/api/stats`).then(response => ({
            responseTime: performance.now(),
            status: response.status
          }))
        );
      }
      
      const apiResults = await Promise.all(apiTests);
      const avgResponseTime = apiResults.reduce((sum, r) => sum + r.responseTime, 0) / apiResults.length;
      
      this.results.performance.apiResponse = {
        status: avgResponseTime < 1000 ? 'PASS' : 'WARN',
        averageResponseTime: Math.round(avgResponseTime),
        threshold: 1000
      };
      
      console.log(`  ✅ API Response Time: ${Math.round(avgResponseTime)}ms average`);
      
      // Test packet injection performance
      const packetTests = [];
      const startTime = performance.now();
      
      for (let i = 0; i < 100; i++) {
        packetTests.push(
          axios.post(`${API_BASE_URL}/api/packets`, {
            src_ip: '192.168.1.100',
            dst_ip: '192.168.1.1',
            protocol: 'TCP',
            src_port: 12345 + i,
            dst_port: 80,
            size: 1024,
            flags: 'SYN'
          })
        );
      }
      
      await Promise.all(packetTests);
      const endTime = performance.now();
      const totalTime = endTime - startTime;
      const packetsPerSecond = Math.round((100 / totalTime) * 1000);
      
      this.results.performance.packetInjection = {
        status: packetsPerSecond > 50 ? 'PASS' : 'WARN',
        packetsPerSecond: packetsPerSecond,
        totalTime: Math.round(totalTime),
        threshold: 50
      };
      
      console.log(`  ✅ Packet Injection: ${packetsPerSecond} packets/sec`);
      
    } catch (error) {
      this.results.performance = {
        status: 'FAIL',
        error: error.message
      };
      console.log(`  ❌ Performance test failed: ${error.message}`);
    }
    
    console.log('');
  }

  generateReport() {
    console.log('📊 Test Results Summary');
    console.log('=======================\n');
    
    // Calculate overall status
    const allResults = [
      ...Object.values(this.results.api),
      ...Object.values(this.results.websocket),
      ...Object.values(this.results.detection),
      ...Object.values(this.results.performance)
    ].filter(r => r && r.status);
    
    const passCount = allResults.filter(r => r.status === 'PASS').length;
    const failCount = allResults.filter(r => r.status === 'FAIL').length;
    const warnCount = allResults.filter(r => r.status === 'WARN').length;
    
    this.results.overall = failCount > 0 ? 'FAILED' : warnCount > 0 ? 'WARNINGS' : 'PASSED';
    
    console.log(`Overall Status: ${this.getStatusIcon(this.results.overall)} ${this.results.overall}`);
    console.log(`Tests Passed: ${passCount}`);
    console.log(`Tests Failed: ${failCount}`);
    console.log(`Warnings: ${warnCount}\n`);
    
    // API Results
    console.log('🔗 API Endpoints:');
    Object.entries(this.results.api).forEach(([name, result]) => {
      console.log(`  ${this.getStatusIcon(result.status)} ${name}: ${result.status}`);
      if (result.responseTime) {
        console.log(`    Response Time: ${result.responseTime}ms`);
      }
    });
    
    // WebSocket Results
    console.log('\n📡 WebSocket:');
    Object.entries(this.results.websocket).forEach(([name, result]) => {
      console.log(`  ${this.getStatusIcon(result.status)} ${name}: ${result.status}`);
    });
    
    // Detection Results
    console.log('\n🎯 Detection Algorithms:');
    Object.entries(this.results.detection).forEach(([name, result]) => {
      console.log(`  ${this.getStatusIcon(result.status)} ${name}: ${result.status}`);
    });
    
    // Performance Results
    console.log('\n⚡ Performance:');
    Object.entries(this.results.performance).forEach(([name, result]) => {
      console.log(`  ${this.getStatusIcon(result.status)} ${name}: ${result.status}`);
      if (result.packetsPerSecond) {
        console.log(`    ${result.packetsPerSecond} packets/sec`);
      }
      if (result.averageResponseTime) {
        console.log(`    ${result.averageResponseTime}ms average response time`);
      }
    });
    
    console.log('\n' + '='.repeat(50));
    
    if (this.results.overall === 'PASSED') {
      console.log('🎉 All tests passed! The IDS system is working correctly.');
    } else if (this.results.overall === 'WARNINGS') {
      console.log('⚠️  Tests passed with warnings. Review the results above.');
    } else {
      console.log('❌ Some tests failed. Check the results above and fix the issues.');
      process.exit(1);
    }
  }

  getStatusIcon(status) {
    switch (status) {
      case 'PASS': return '✅';
      case 'FAIL': return '❌';
      case 'WARN': return '⚠️';
      case 'PASSED': return '🎉';
      case 'WARNINGS': return '⚠️';
      case 'FAILED': return '❌';
      default: return '❓';
    }
  }
}

// Main execution
async function main() {
  const tester = new SystemTester();
  await tester.runAllTests();
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = SystemTester;
