// Mock data generators for development and fallback scenarios

import type { Alert, InsiderThreat, TrafficData, ProtocolData } from "./api"

export function generateMockAlerts(): Alert[] {
  return [
    {
      id: "1",
      timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
      sourceIp: "192.168.1.105",
      destIp: "10.0.0.50",
      protocol: "TCP",
      type: "signature",
      severity: "critical",
      description: "SQL Injection Attempt Detected",
    },
    {
      id: "2",
      timestamp: new Date(Date.now() - 12 * 60000).toISOString(),
      sourceIp: "203.0.113.42",
      destIp: "10.0.0.100",
      protocol: "HTTP",
      type: "anomaly",
      severity: "high",
      description: "Unusual Data Transfer Pattern",
    },
    {
      id: "3",
      timestamp: new Date(Date.now() - 25 * 60000).toISOString(),
      sourceIp: "198.51.100.89",
      destIp: "10.0.0.75",
      protocol: "DNS",
      type: "signature",
      severity: "medium",
      description: "DNS Tunneling Detected",
    },
    {
      id: "4",
      timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
      sourceIp: "192.168.1.200",
      destIp: "10.0.0.25",
      protocol: "SSH",
      type: "anomaly",
      severity: "high",
      description: "Brute Force Attack Pattern",
    },
  ]
}

export function generateMockInsiderThreats(): InsiderThreat[] {
  return [
    {
      id: "1",
      timestamp: new Date(Date.now() - 2 * 60000).toISOString(),
      user: "john.doe@company.com",
      activity: "Accessed sensitive files outside work hours",
      riskLevel: "high",
    },
    {
      id: "2",
      timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
      user: "jane.smith@company.com",
      activity: "Downloaded large dataset to USB",
      riskLevel: "critical",
    },
    {
      id: "3",
      timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
      user: "bob.wilson@company.com",
      activity: "Multiple failed login attempts",
      riskLevel: "medium",
    },
  ]
}

export function generateMockTrafficData(): TrafficData[] {
  return [
    { time: "00:00", packets: 4200, bytes: 1024000 },
    { time: "04:00", packets: 3800, bytes: 950000 },
    { time: "08:00", packets: 5200, bytes: 1280000 },
    { time: "12:00", packets: 6100, bytes: 1500000 },
    { time: "16:00", packets: 5800, bytes: 1420000 },
    { time: "20:00", packets: 4900, bytes: 1200000 },
  ]
}

export function generateMockProtocolData(): ProtocolData[] {
  return [
    { name: "TCP", value: 45 },
    { name: "UDP", value: 30 },
    { name: "ICMP", value: 15 },
    { name: "DNS", value: 10 },
  ]
}

// Generate a new alert (for real-time updates simulation)
export function generateNewAlert(): Alert {
  const protocols = ["TCP", "UDP", "ICMP", "DNS", "SSH", "HTTP"]
  const types: ("signature" | "anomaly")[] = ["signature", "anomaly"]
  const severities: ("critical" | "high" | "medium" | "low")[] = ["critical", "high", "medium", "low"]
  const descriptions = [
    "SQL Injection Attempt Detected",
    "Unusual Data Transfer Pattern",
    "DNS Tunneling Detected",
    "Brute Force Attack Pattern",
    "Port Scan Detected",
    "Malware Signature Match",
  ]

  const randomIp = () =>
    `${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}`

  return {
    id: `alert-${Date.now()}`,
    timestamp: new Date().toISOString(),
    sourceIp: randomIp(),
    destIp: randomIp(),
    protocol: protocols[Math.floor(Math.random() * protocols.length)],
    type: types[Math.floor(Math.random() * types.length)],
    severity: severities[Math.floor(Math.random() * severities.length)],
    description: descriptions[Math.floor(Math.random() * descriptions.length)],
  }
}
