# AI-Powered Real-Time Intrusion Detection System

A multi-layered intrusion detection system that combines classical security techniques with modern machine learning to detect and classify network threats in real time. This hybrid approach leverages signature-based pattern matching, unsupervised anomaly detection, and deep learning-based classification to improve detection accuracy while reducing false positives.

## Overview

This IDS implements a three-tier detection strategy designed for comprehensive network security monitoring:

1. **Signature-based Detection** — Pattern matching against known attack signatures for immediate threat identification
2. **Unsupervised Anomaly Detection** — Isolation Forest algorithm to identify previously unseen threats and unusual traffic patterns
3. **Deep Learning Classification** — Convolutional Neural Network (SecIDS-CNN) achieving 97.72% accuracy for sophisticated threat classification

The system performs real-time packet capture and feature extraction, processes network traffic through multiple detection layers, and provides a full-stack monitoring solution with persistent storage, RESTful APIs, and real-time alerting capabilities.

## Key Technical Capabilities

### Detection Engine

- **Real-time Packet Capture & Feature Extraction** — Live network traffic monitoring using Scapy with intelligent packet analysis and feature engineering
- **Signature-based Pattern Matching** — Comprehensive rule-based detection for known attack vectors:
  - SQL injection and XSS attacks
  - Port scanning and reconnaissance activities
  - Denial of Service (DoS) attacks
  - Brute force authentication attempts
  - Malware command & control communication
  - Data exfiltration patterns
- **Isolation Forest Anomaly Detection** — Unsupervised machine learning for identifying zero-day threats and anomalous network behavior
- **Deep Learning Classification** — SecIDS-CNN convolutional neural network trained for network intrusion classification (97.72% accuracy)
- **Flexible Model Support** — Optional supervised models including Random Forest, XGBoost, SVM, and Logistic Regression

### Advanced Features

- **PCAP File Analysis** — Offline investigation capabilities for forensic analysis and historical traffic review
- **Comprehensive Alert Management** — Filtering, history tracking, bulk operations, and resolution workflows
- **Model Training Pipeline** — End-to-end ML pipeline for custom dataset training, evaluation, and performance metrics
- **Traffic Intelligence** — Protocol distribution analysis, connection tracking, and real-time statistics
- **RESTful API Architecture** — Full-featured REST endpoints with WebSocket support for real-time updates
- **Production-Ready Deployment** — Docker containerization with multi-stage builds and health monitoring
- **Rate Limiting & Security** — Built-in request throttling and system health endpoints

## System Architecture

The system is built on a modern, scalable architecture with clear separation of concerns:

1. **Packet Capture Layer** — Scapy-based packet capture engine monitors live network traffic or processes injected test packets via API
2. **Multi-Layer Analysis Engine** — Each packet flows through three detection mechanisms:
   - Signature-based pattern matching for known threats
   - Isolation Forest for anomaly detection
   - Deep learning classification via SecIDS-CNN or alternative supervised models
3. **Persistence Layer** — MongoDB stores alerts, traffic statistics, user activities, and PCAP analysis results with optimized indexing for query performance
4. **API & Real-Time Communication** — Flask REST API with Socket.IO enables real-time bidirectional communication; Next.js frontend consumes API endpoints and WebSocket streams for live updates

## Technology Stack

The system leverages modern technologies across the full stack to ensure performance, scalability, and maintainability.

| Layer       | Technologies |
|------------|--------------|
| **Backend**   | Python 3.12, Flask 3, Scapy, scikit-learn, imbalanced-learn, TensorFlow, XGBoost |
| **Frontend**  | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI, Recharts |
| **Database**      | MongoDB 7.0 |
| **Real-Time Communication** | Socket.IO (WebSocket protocol) |
| **Deployment**| Docker (multi-stage builds), Docker Compose |
| **Machine Learning** | TensorFlow (CNN), scikit-learn (Isolation Forest, Random Forest, SVM), XGBoost |

Classification defaults to the pre-trained SecIDS-CNN model. See [backend/docs/SECIDS_CNN.md](backend/docs/SECIDS_CNN.md) and [SecIDS-CNN/README.md](SecIDS-CNN/README.md) for detailed model documentation.

## Model Performance

The SecIDS-CNN deep learning model demonstrates high accuracy in network intrusion classification:

| Metric    | Value   |
|----------|---------|
| **Accuracy** | 97.72%  |
| **Precision**| 97.74%  |
| **Recall**   | 97.72%  |
| **F1-Score** | 0.9772  |

These metrics reflect evaluation on diverse network traffic patterns including normal traffic and various attack types. The hybrid detection approach combining signature-based rules, anomaly detection, and deep learning classification significantly reduces false positives while maintaining high detection rates.

## Documentation

- [backend/docs/SECIDS_CNN.md](backend/docs/SECIDS_CNN.md) — SecIDS-CNN integration and input/output
- [SecIDS-CNN/README.md](SecIDS-CNN/README.md) — Model source and usage (Hugging Face: [Keyven/SecIDS-CNN](https://huggingface.co/Keyven/SecIDS-CNN))

## License

MIT. SecIDS-CNN model is under Creative Commons Attribution Non Commercial 4.0 (cc-by-nc-4.0); see [SecIDS-CNN/README.md](SecIDS-CNN/README.md).
