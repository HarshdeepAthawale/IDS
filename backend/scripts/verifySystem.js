#!/usr/bin/env node

/**
 * System Verification Script
 * Tests all major components of the IDS system
 */

const fs = require('fs').promises;
const path = require('path');

// Test configuration
const tests = [
  {
    name: 'Check data directory exists',
    test: async () => {
      const dataDir = path.join(__dirname, '../data');
      try {
        await fs.access(dataDir);
        return { success: true, message: 'Data directory exists' };
      } catch {
        await fs.mkdir(dataDir, { recursive: true });
        return { success: true, message: 'Data directory created' };
      }
    }
  },
  {
    name: 'Check required files exist',
    test: async () => {
      const requiredFiles = [
        '../data/packets.json',
        '../data/alerts.json'
      ];
      
      for (const file of requiredFiles) {
        const filePath = path.join(__dirname, file);
        try {
          await fs.access(filePath);
        } catch {
          await fs.writeFile(filePath, JSON.stringify([], null, 2));
        }
      }
      
      return { success: true, message: 'Required files exist or created' };
    }
  },
  {
    name: 'Test IDS Engine initialization',
    test: async () => {
      try {
        const idsEngine = require('../services/idsEngine');
        const status = idsEngine.getStatus();
        return { 
          success: true, 
          message: `IDS Engine status: ${status.isRunning ? 'Running' : 'Stopped'}` 
        };
      } catch (error) {
        return { success: false, message: `IDS Engine error: ${error.message}` };
      }
    }
  },
  {
    name: 'Test Packet Capture Service',
    test: async () => {
      try {
        const packetCapture = require('../services/packetCapture');
        const status = packetCapture.getStatus();
        return { 
          success: true, 
          message: `Packet Capture: ${status.isCapturing ? 'Active' : 'Inactive'}` 
        };
      } catch (error) {
        return { success: false, message: `Packet Capture error: ${error.message}` };
      }
    }
  },
  {
    name: 'Test Storage System',
    test: async () => {
      try {
        const storage = require('../utils/storage');
        const packets = await storage.getPackets();
        const alerts = await storage.getAlerts();
        return { 
          success: true, 
          message: `Storage: ${packets.length} packets, ${alerts.length} alerts` 
        };
      } catch (error) {
        return { success: false, message: `Storage error: ${error.message}` };
      }
    }
  },
  {
    name: 'Test Configuration Loading',
    test: async () => {
      try {
        const thresholds = require('../config/thresholds');
        const capture = require('../config/capture');
        
        const thresholdConfig = thresholds.getThresholds();
        const captureConfig = capture.getConfig('defaultInterface');
        
        return { 
          success: true, 
          message: `Config loaded: ${Object.keys(thresholdConfig).length} thresholds` 
        };
      } catch (error) {
        return { success: false, message: `Config error: ${error.message}` };
      }
    }
  }
];

async function runTests() {
  console.log('\n' + '='.repeat(60));
  console.log('🔍 IDS SYSTEM VERIFICATION');
  console.log('='.repeat(60));
  
  let passed = 0;
  let failed = 0;
  
  for (const test of tests) {
    try {
      console.log(`\n🧪 ${test.name}...`);
      const result = await test.test();
      
      if (result.success) {
        console.log(`✅ ${result.message}`);
        passed++;
      } else {
        console.log(`❌ ${result.message}`);
        failed++;
      }
    } catch (error) {
      console.log(`❌ Test failed with error: ${error.message}`);
      failed++;
    }
  }
  
  console.log('\n' + '='.repeat(60));
  console.log('📊 VERIFICATION RESULTS');
  console.log('='.repeat(60));
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`📈 Success Rate: ${Math.round((passed / (passed + failed)) * 100)}%`);
  
  if (failed === 0) {
    console.log('\n🎉 All tests passed! System is ready to run.');
    process.exit(0);
  } else {
    console.log('\n⚠️  Some tests failed. Please check the errors above.');
    process.exit(1);
  }
}

// Run tests if called directly
if (require.main === module) {
  runTests().catch(error => {
    console.error('❌ Verification script failed:', error);
    process.exit(1);
  });
}

module.exports = { runTests, tests };
