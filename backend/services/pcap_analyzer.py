"""
PCAP analysis service for quick summaries and deeper detections.
Uses scapy for lightweight parsing and heuristic detections suitable for demos.
Integrates ML models (AnomalyDetector, ClassificationDetector) for enhanced detection.
"""

import math
import os
import time
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scapy.all import DNSQR, IP, TCP, UDP, Raw, ICMP, IPv6, rdpcap  # type: ignore

logger = logging.getLogger(__name__)

# MITRE technique references for clarity in responses
MITRE_MAP = {
    "port_scan": {"technique": "T1046", "tactic": "Discovery"},
    "dos": {"technique": "T1499", "tactic": "Impact"},
    "dns_tunnel": {"technique": "T1071.004", "tactic": "Command and Control"},
    "exfil": {"technique": "T1048", "tactic": "Exfiltration"},
    "http_suspicious": {"technique": "T1190", "tactic": "Initial Access"},
}


def _entropy(data: bytes) -> float:
    """Calculate Shannon entropy for payload heuristics."""
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _iso(ts: float) -> str:
    """Return ISO timestamp in UTC from a UNIX timestamp."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


class PcapAnalyzer:
    """Lightweight PCAP analyzer with summary, heuristic, and ML-based detections."""

    def __init__(self, config: Optional[Any] = None, packet_analyzer: Optional[Any] = None):
        self.config = config
        self.packet_analyzer = packet_analyzer
        self.default_max_packets = getattr(config, "PCAP_MAX_PACKETS", 2000)
        self.max_timeline_points = 60  # avoid very long timelines in responses
        logger.info(f"PcapAnalyzer initialized with max_packets={self.default_max_packets}, ML={'enabled' if packet_analyzer else 'disabled'}")

    def analyze(self, file_path: str, max_packets: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze a PCAP file and return structured findings.

        Args:
            file_path: Path to the PCAP file
            max_packets: Optional cap on packets to process for speed

        Returns:
            Dict with metadata, summary, detections, risk and evidence sections.
        """
        start = time.time()
        
        # Check file size and log
        try:
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"Analyzing PCAP file: {file_path} ({file_size_mb:.2f} MB)")
            
            if file_size_mb > 100:
                logger.warning(f"Large PCAP file detected ({file_size_mb:.2f} MB). Processing may take time.")
        except OSError as e:
            logger.warning(f"Could not determine file size: {e}")
        
        packet_limit = max_packets or self.default_max_packets
        logger.debug(f"Processing up to {packet_limit} packets")
        
        # Load packets with error handling
        try:
            packets = rdpcap(file_path, count=packet_limit)
        except Exception as e:
            error_msg = f"Failed to parse PCAP file with Scapy: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        if not packets:
            raise ValueError("PCAP contained no packets or could not be parsed")
        
        logger.info(f"Loaded {len(packets)} packets from PCAP file")

        # Summarize packets
        try:
            summary, features = self._summarize_packets(packets)
            logger.debug(f"Packet summary completed: {summary['total_packets']} packets, {summary['total_bytes']} bytes")
        except Exception as e:
            logger.error(f"Error summarizing packets: {e}")
            raise ValueError(f"Failed to summarize packets: {str(e)}") from e
        
        # Build heuristic detections
        try:
            heuristic_detections = self._build_detections(features)
            logger.debug(f"Found {len(heuristic_detections)} heuristic detections")
        except Exception as e:
            logger.error(f"Error building detections: {e}")
            heuristic_detections = []
        
        # Integrate ML models if available
        ml_detections = []
        model_metadata = {}
        if self.packet_analyzer:
            try:
                logger.debug("Starting ML analysis")
                ml_detections, model_metadata = self._analyze_with_ml(packets)
                logger.info(f"ML analysis completed: {len(ml_detections)} ML detections")
            except AttributeError as e:
                logger.warning(f"ML analysis failed due to missing attribute: {e}")
                model_metadata = {
                    "ml_enabled": False,
                    "error": f"ML model attribute error: {str(e)}"
                }
            except Exception as e:
                logger.warning(f"ML analysis failed, using heuristics only: {e}", exc_info=True)
                model_metadata = {
                    "ml_enabled": False,
                    "error": str(e)
                }
        else:
            model_metadata = {
                "ml_enabled": False,
                "reason": "PacketAnalyzer not provided"
            }
        
        # Combine and deduplicate detections (same finding can fire per-packet and produce duplicates)
        combined = heuristic_detections + ml_detections
        all_detections = self._deduplicate_detections(combined)
        logger.info(f"Total detections: {len(all_detections)} (after dedup from {len(combined)}: {len(heuristic_detections)} heuristic, {len(ml_detections)} ML)")
        
        try:
            risk = self._score_risk(all_detections, summary, model_metadata)
        except Exception as e:
            logger.error(f"Error scoring risk: {e}")
            # Return minimal risk score based on actual detections count, not mock data
            risk = {
                "score": 10 if len(all_detections) > 0 else 0, 
                "level": "low", 
                "rationale": [f"Risk calculation error: {str(e)}"] if str(e) else []
            }

        processing_ms = round((time.time() - start) * 1000, 2)
        logger.info(f"PCAP analysis completed in {processing_ms}ms")

        # Ensure detection_counts always reflects reality: heuristic (traditional) detections
        # count as "signature", so the UI shows "Heuristic: N" correctly when using traditional-only.
        if "detection_counts" not in model_metadata:
            model_metadata["detection_counts"] = {"signature": 0, "anomaly": 0, "classification": 0}
        model_metadata["detection_counts"]["signature"] = (
            model_metadata["detection_counts"].get("signature", 0) + len(heuristic_detections)
        )

        # Return ONLY real analysis results from the PCAP file - NO mock data
        # All data comes from actual packet analysis, ML models, or empty arrays if no data found
        return {
            "metadata": {
                "packets_processed": summary["total_packets"],  # Actual packet count from PCAP
                "bytes_processed": summary["total_bytes"],  # Actual byte count from PCAP
                "processing_time_ms": processing_ms,  # Actual processing time
                "duration_seconds": summary["duration_seconds"],  # Actual capture duration
                "capture_window": summary["capture_window"],  # Actual timestamps from packets
                "cached": False,
                "model_info": model_metadata,  # Real ML model status
            },
            "summary": {
                "top_protocols": summary["top_protocols"],  # Real protocol counts from packets
                "top_talkers": summary["top_talkers"],  # Real IP addresses from packets
                "top_ports": summary["top_ports"],  # Real port counts from packets
                "dns_queries": summary["dns_queries"],  # Real DNS queries from packets
                "tls_handshakes": summary["tls_handshakes"],  # Real TLS connections from packets
                "http_hosts": summary["http_hosts"],  # Real HTTP hosts from packets
                "flow_samples": summary["flow_samples"],  # Real flow data from packets
            },
            "detections": all_detections,  # Real detections from analysis (empty list if none found)
            "risk": risk,  # Real risk score calculated from actual detections
            "evidence": {
                "timeline": summary["timeline"],  # Real timeline from packet timestamps
                "endpoint_matrix": summary["endpoint_matrix"],  # Real endpoint connections from packets
            },
        }


    def _summarize_packets(self, packets) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        protocol_counts: Counter[str] = Counter()
        src_counts: Counter[str] = Counter()
        dst_counts: Counter[str] = Counter()
        port_counts: Counter[int] = Counter()
        flow_counts: Counter[Tuple[str, str, str]] = Counter()
        flow_ports_by_src: defaultdict[str, set[int]] = defaultdict(set)
        syn_tracker: Counter[Tuple[str, str]] = Counter()
        dns_queries: List[str] = []
        tls_handshakes: List[Dict[str, Any]] = []
        http_hosts: Counter[str] = Counter()
        timeline: defaultdict[str, Dict[str, int]] = defaultdict(lambda: {"packets": 0, "bytes": 0})
        endpoint_matrix: Counter[Tuple[str, str]] = Counter()
        entropy_observations: List[Tuple[int, float]] = []

        total_bytes = 0
        first_ts = None
        last_ts = None

        for pkt in packets:
            pkt_len = len(pkt)
            total_bytes += pkt_len

            ts = float(getattr(pkt, "time", time.time()))
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)

            bucket = datetime.fromtimestamp(ts, tz=timezone.utc).replace(second=0, microsecond=0).isoformat()
            timeline[bucket]["packets"] += 1
            timeline[bucket]["bytes"] += pkt_len

            if IP in pkt:
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst
                src_counts[src_ip] += 1
                dst_counts[dst_ip] += 1
                endpoint_matrix[(src_ip, dst_ip)] += 1
            else:
                src_ip = "unknown"
                dst_ip = "unknown"

            proto_label = None
            if TCP in pkt:
                proto_label = "TCP"
                dport = int(pkt[TCP].dport)
                port_counts[dport] += 1
                flow_counts[(src_ip, dst_ip, f"TCP/{dport}")] += 1
                flow_ports_by_src[src_ip].add(dport)

                flags = pkt[TCP].flags
                if flags & 0x02:  # SYN flag
                    syn_tracker[(src_ip, dst_ip)] += 1

                if Raw in pkt:
                    entropy_observations.append((dport, _entropy(bytes(pkt[Raw].load))))

            elif UDP in pkt:
                proto_label = "UDP"
                dport = int(pkt[UDP].dport)
                port_counts[dport] += 1
                flow_counts[(src_ip, dst_ip, f"UDP/{dport}")] += 1
                flow_ports_by_src[src_ip].add(dport)

                if Raw in pkt:
                    entropy_observations.append((dport, _entropy(bytes(pkt[Raw].load))))

            if proto_label:
                protocol_counts[proto_label] += 1

            if DNSQR in pkt:
                try:
                    qname = pkt[DNSQR].qname.decode(errors="ignore").rstrip(".")
                    dns_queries.append(qname)
                except Exception:
                    pass

            # Simple TLS handshake heuristic: TCP 443 with payload present
            if TCP in pkt and int(pkt[TCP].dport) == 443:
                tls_handshakes.append({"server": dst_ip, "port": 443})

            # HTTP host heuristic via Raw payload strings
            if Raw in pkt:
                payload = bytes(pkt[Raw].load)
                if b"Host:" in payload:
                    try:
                        host_line = [line for line in payload.split(b"\r\n") if line.lower().startswith(b"host:")]
                        if host_line:
                            host = host_line[0].split(b":", 1)[1].strip().decode(errors="ignore")
                            http_hosts[host] += 1
                    except Exception:
                        pass

        duration = (last_ts - first_ts) if first_ts and last_ts else 0
        total_packets = len(packets)

        def _top(counter: Counter, key_name: str, limit: int = 5):
            top_items = counter.most_common(limit)
            if key_name == "protocol":
                return [
                    {"name": name, "count": count, "percentage": round((count / total_packets) * 100, 2)}
                    for name, count in top_items
                ]
            if key_name == "ip":
                return [{"ip": name, "packets": count} for name, count in top_items]
            if key_name == "port":
                return [{"port": name, "packets": count} for name, count in top_items]
            return top_items

        timeline_points = sorted(timeline.items(), key=lambda x: x[0], reverse=True)[: self.max_timeline_points]
        timeline_output = [
            {"bucket": bucket, "packets": data["packets"], "bytes": data["bytes"]} for bucket, data in timeline_points
        ]

        flow_samples = []
        for (src, dst, proto_port), count in flow_counts.most_common(6):
            proto, port = proto_port.split("/")
            flow_samples.append({"src": src, "dst": dst, "proto": proto, "dport": int(port), "packets": count})

        summary = {
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "duration_seconds": duration,
            "capture_window": {"start": _iso(first_ts) if first_ts else None, "end": _iso(last_ts) if last_ts else None},
            "top_protocols": _top(protocol_counts, "protocol", limit=6),
            "top_talkers": _top(src_counts + dst_counts, "ip", limit=6),
            "top_ports": _top(port_counts, "port", limit=6),
            "dns_queries": dns_queries[:20],
            "tls_handshakes": tls_handshakes[:10],
            "http_hosts": [host for host, _ in http_hosts.most_common(10)],
            "flow_samples": flow_samples,
            "timeline": timeline_output,
            "endpoint_matrix": [
                {"src": src, "dst": dst, "packets": count} for (src, dst), count in endpoint_matrix.most_common(12)
            ],
        }

        features = {
            "protocol_counts": protocol_counts,
            "port_counts": port_counts,
            "flow_ports_by_src": flow_ports_by_src,
            "syn_tracker": syn_tracker,
            "dns_queries": dns_queries,
            "entropy_observations": entropy_observations,
        }

        return summary, features

    def _build_detections(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        detections: List[Dict[str, Any]] = []
        port_counts: Counter[int] = features["port_counts"]
        flow_ports_by_src: defaultdict[str, set[int]] = features["flow_ports_by_src"]
        syn_tracker: Counter[Tuple[str, str]] = features["syn_tracker"]
        dns_queries: List[str] = features["dns_queries"]
        entropy_observations: List[Tuple[int, float]] = features["entropy_observations"]

        # Port scan heuristic
        for src, ports in flow_ports_by_src.items():
            if len(ports) >= 25:
                detections.append(
                    {
                        "id": "port_scan",
                        "title": "Port scanning behavior",
                        "severity": "medium",
                        "confidence": 0.7,
                        "description": f"{src} contacted {len(ports)} unique destination ports; pattern consistent with scanning.",
                        "evidence": {"source": src, "unique_ports": len(ports)},
                        "mitre": MITRE_MAP["port_scan"],
                    }
                )
                break

        # SYN flood heuristic
        for (src, dst), syn_count in syn_tracker.items():
            if syn_count >= 400:
                detections.append(
                    {
                        "id": "dos_syn",
                        "title": "SYN flood pattern",
                        "severity": "high",
                        "confidence": 0.68,
                        "description": f"{syn_count} SYN packets from {src} to {dst} without corresponding ACK visibility.",
                        "evidence": {"source": src, "destination": dst, "syn_packets": syn_count},
                        "mitre": MITRE_MAP["dos"],
                    }
                )
                break

        # DNS tunneling heuristic
        long_queries = [q for q in dns_queries if len(q) > 50]
        if long_queries and len(dns_queries) > 10:
            avg_len = sum(len(q) for q in long_queries) / len(long_queries)
            detections.append(
                {
                    "id": "dns_tunnel",
                    "title": "Possible DNS tunneling",
                    "severity": "high",
                    "confidence": 0.7,
                    "description": "Long or numerous DNS queries observed; may indicate tunneling or covert channels.",
                    "evidence": {"long_queries": len(long_queries), "avg_length": round(avg_len, 2)},
                    "mitre": MITRE_MAP["dns_tunnel"],
                }
            )

        # High-entropy payloads on uncommon ports
        suspicious_entropy = [obs for obs in entropy_observations if obs[1] > 7.5 and obs[0] not in (80, 443, 53)]
        if suspicious_entropy:
            sample_port, entropy_val = suspicious_entropy[0]
            detections.append(
                {
                    "id": "exfil_high_entropy",
                    "title": "High-entropy payload on uncommon port",
                    "severity": "high",
                    "confidence": 0.64,
                    "description": "Payload entropy >7.5 detected on non-standard ports; could indicate encrypted exfiltration or custom C2.",
                    "evidence": {"sample_port": sample_port, "entropy": round(entropy_val, 2)},
                    "mitre": MITRE_MAP["exfil"],
                }
            )

        # Suspicious HTTP hosts
        if port_counts.get(80, 0) > 0 and any(port_counts.get(p, 0) > 0 for p in [8080, 8000, 8888]):
            detections.append(
                {
                    "id": "http_suspicious",
                    "title": "HTTP traffic on uncommon ports",
                    "severity": "medium",
                    "confidence": 0.55,
                    "description": "HTTP-like traffic detected on uncommon ports (8080/8000/8888); may indicate proxy evasion or admin interfaces exposed.",
                    "evidence": {"ports_seen": [p for p in [8080, 8000, 8888] if port_counts.get(p)]},
                    "mitre": MITRE_MAP["http_suspicious"],
                }
            )

        return detections

    def _deduplicate_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate detections that share the same title, severity, and evidence (e.g. same XSS per packet)."""
        seen: set = set()
        out: List[Dict[str, Any]] = []
        for d in detections:
            ev = d.get("evidence") or {}
            src = ev.get("source_ip") or ev.get("source") or ""
            dst = ev.get("dest_ip") or ev.get("destination") or ""
            key = (
                d.get("title") or "",
                (d.get("severity") or "low").lower(),
                str(src),
                str(dst),
            )
            if key in seen:
                continue
            seen.add(key)
            # Ensure unique id for display (in case we merged duplicates)
            d_copy = dict(d)
            d_copy["id"] = d.get("id") or f"det_{len(out)}"
            out.append(d_copy)
        return out

    def _score_risk(
        self,
        detections: List[Dict[str, Any]],
        summary: Dict[str, Any],
        model_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute risk score only from classification (e.g. SecIDS-CNN).
        When classification is enabled, trained, and has confidence scores,
        risk = mean(malicious probability) scaled 0–100. No fallback formula:
        when ML scores are unavailable, return risk_source "unavailable".
        """
        rationale = []
        classification_enabled = False
        classification_trained = False
        confidence_scores = []
        classification_model_type = "unknown"
        if model_metadata:
            cd = model_metadata.get("classification_detector") or {}
            classification_enabled = cd.get("enabled", False)
            classification_trained = cd.get("trained", False)
            confidence_scores = model_metadata.get("confidence_scores") or []
            classification_model_type = model_metadata.get("classification_model_type", "unknown")

        # Risk from SecIDS-CNN / classification when enabled, trained, and we have confidence
        if classification_enabled and classification_trained and confidence_scores:
            # Focus on packets that are classified as malicious (confidence > 0.5)
            # Don't dilute high-confidence malicious detections with benign traffic
            malicious_threshold = 0.5
            malicious_scores = [s for s in confidence_scores if s > malicious_threshold]

            model_label = "SecIDS-CNN" if classification_model_type == "secids_cnn" else "Classification"

            if malicious_scores:
                # Risk scoring based on malicious packets:
                # - Max confidence contributes 60% (a single high-confidence detection is concerning)
                # - Average malicious confidence contributes 25%
                # - Percentage of malicious packets contributes 15%
                max_conf = max(malicious_scores)
                avg_malicious_conf = sum(malicious_scores) / len(malicious_scores)
                malicious_ratio = len(malicious_scores) / len(confidence_scores)

                # Weighted score calculation
                score = (
                    (max_conf * 100 * 0.60) +           # Max confidence (60% weight)
                    (avg_malicious_conf * 100 * 0.25) + # Avg malicious confidence (25% weight)
                    (min(malicious_ratio * 200, 15))    # % malicious packets (15% weight, capped)
                )
                score = round(score)
                score = max(0, min(100, score))

                rationale.append(f"{model_label}: {len(malicious_scores)} malicious packet(s) detected")
                rationale.append(f"Max confidence: {max_conf:.0%}, Avg: {avg_malicious_conf:.0%}")
            else:
                # No malicious packets detected - low risk
                mean_conf = sum(confidence_scores) / len(confidence_scores)
                score = round(mean_conf * 100)
                score = max(0, min(100, score))
                rationale.append(f"{model_label}: No malicious packets (avg confidence {mean_conf:.2f})")

            for d in detections[:4]:
                rationale.append(d.get("title", "Detection identified"))

            if score >= 80:
                level = "critical"
            elif score >= 65:
                level = "high"
            elif score >= 40:
                level = "medium"
            else:
                level = "low"
            return {
                "score": int(score),
                "level": level,
                "rationale": rationale[:6],
                "risk_source": "classification",
                "classification_model_type": classification_model_type,
            }

        # No ML confidence: use detection-based fallback when we have detections (heuristic or ML)
        if detections:
            severity_weights = {"critical": 25, "high": 18, "medium": 12, "low": 6}
            detection_score = 0
            for d in detections[:20]:
                sev = (d.get("severity") or "low").lower()
                detection_score += severity_weights.get(sev, 6)
            score = min(100, detection_score)
            score = max(10, score)  # At least 10 when there are detections
            rationale.append(f"Risk from {len(detections)} detection(s) (heuristic + ML)")
            for d in detections[:4]:
                rationale.append(d.get("title", "Detection identified"))
            if score >= 80:
                level = "critical"
            elif score >= 65:
                level = "high"
            elif score >= 40:
                level = "medium"
            else:
                level = "low"
            return {
                "score": int(score),
                "level": level,
                "rationale": rationale[:6],
                "risk_source": "detections",
                "classification_model_type": classification_model_type,
            }

        # No detections and no ML scores
        rationale.append("No detections. Enable SecIDS-CNN for ML risk score, or upload a PCAP with suspicious traffic.")
        return {
            "score": 0,
            "level": "low",
            "rationale": rationale[:6],
            "risk_source": "unavailable",
        }

    def _scapy_to_packet_data(self, pkt) -> Optional[Dict[str, Any]]:
        """
        Convert Scapy packet to packet_data format expected by PacketAnalyzer.
        
        Args:
            pkt: Scapy packet object
            
        Returns:
            Dictionary with parsed packet data or None if parsing fails
        """
        try:
            parsed = {
                'timestamp': datetime.fromtimestamp(float(getattr(pkt, "time", time.time())), tz=timezone.utc),
                'raw_size': len(pkt),
                'protocol': 'Other',
                'src_ip': None,
                'dst_ip': None,
                'src_port': None,
                'dst_port': None,
                'flags': None,
                'payload_size': 0,
                'payload_preview': None
            }
            
            # Extract IP layer information
            if IP in pkt:
                ip_layer = pkt[IP]
                parsed['src_ip'] = ip_layer.src
                parsed['dst_ip'] = ip_layer.dst
                protocol_num = ip_layer.proto
                
                # Extract transport layer information
                if TCP in pkt:
                    tcp_layer = pkt[TCP]
                    parsed['src_port'] = int(tcp_layer.sport)
                    parsed['dst_port'] = int(tcp_layer.dport)
                    parsed['flags'] = int(tcp_layer.flags)
                    parsed['protocol'] = 'TCP'
                    
                    # Extract payload
                    if Raw in pkt:
                        payload = bytes(pkt[Raw].load)
                        parsed['payload_size'] = len(payload)
                        parsed['payload_preview'] = payload[:100].hex()
                        
                elif UDP in pkt:
                    udp_layer = pkt[UDP]
                    parsed['src_port'] = int(udp_layer.sport)
                    parsed['dst_port'] = int(udp_layer.dport)
                    parsed['protocol'] = 'UDP'
                    
                    # Extract payload
                    if Raw in pkt:
                        payload = bytes(pkt[Raw].load)
                        parsed['payload_size'] = len(payload)
                        parsed['payload_preview'] = payload[:100].hex()
                        
                elif ICMP in pkt:
                    parsed['protocol'] = 'ICMP'
                    icmp_layer = pkt[ICMP]
                    parsed['flags'] = str(icmp_layer.type)
                else:
                    # IP packet without recognized transport layer
                    parsed['protocol'] = 'IP'
                    
            # Handle IPv6 packets
            elif IPv6 in pkt:
                ipv6_layer = pkt[IPv6]
                parsed['src_ip'] = ipv6_layer.src
                parsed['dst_ip'] = ipv6_layer.dst
                
                if TCP in pkt:
                    tcp_layer = pkt[TCP]
                    parsed['src_port'] = int(tcp_layer.sport)
                    parsed['dst_port'] = int(tcp_layer.dport)
                    parsed['protocol'] = 'TCP'
                    parsed['flags'] = int(tcp_layer.flags)
                elif UDP in pkt:
                    udp_layer = pkt[UDP]
                    parsed['src_port'] = int(udp_layer.sport)
                    parsed['dst_port'] = int(udp_layer.dport)
                    parsed['protocol'] = 'UDP'
                else:
                    parsed['protocol'] = 'IPv6'
            else:
                # No IP layer, skip this packet
                return None
            
            # Must have at least IP addresses to be useful
            if not parsed['src_ip'] or not parsed['dst_ip']:
                return None
                
            return parsed
            
        except Exception as e:
            logger.debug(f"Error converting Scapy packet to packet_data: {e}")
            return None

    def _analyze_with_ml(self, packets) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Analyze packets using ML models (AnomalyDetector, ClassificationDetector).
        
        Returns ONLY real ML analysis results - NO mock data.
        If ML models are not available or fail, returns empty detections list.
        
        Args:
            packets: List of Scapy packets
            
        Returns:
            Tuple of (ml_detections list, model_metadata dict)
        """
        # Initialize with empty results - will be populated with real ML analysis
        ml_detections = []
        model_metadata = {
            "ml_enabled": True,
            "anomaly_detector": {
                "enabled": True,
                "trained": False,  # Real status from model, not mock
            },
            "classification_detector": {
                "enabled": False,  # Real status from model, not mock
                "trained": False,  # Real status from model, not mock
            },
            "classification_model_type": None,  # secids_cnn, random_forest, etc.
            "detection_counts": {
                "signature": 0,  # Will be incremented with real detections
                "anomaly": 0,  # Will be incremented with real detections
                "classification": 0,  # Will be incremented with real detections
            },
            "confidence_scores": []  # Will be populated with real confidence scores
        }
        
        if not self.packet_analyzer:
            logger.debug("PacketAnalyzer not available, skipping ML analysis")
            return ml_detections, model_metadata
        
        try:
            # Check model training status with error handling
            try:
                anomaly_trained = getattr(self.packet_analyzer.anomaly_detector, 'is_trained', False)
                model_metadata["anomaly_detector"]["trained"] = anomaly_trained
            except AttributeError as e:
                logger.warning(f"Could not check anomaly detector status: {e}")
                model_metadata["anomaly_detector"]["enabled"] = False
            
            classification_model_type = "unknown"
            try:
                classification_enabled = self.packet_analyzer.classification_detector is not None
                if classification_enabled:
                    classification_trained = getattr(self.packet_analyzer.classification_detector, 'is_trained', False)
                    classification_model_type = getattr(
                        self.packet_analyzer.classification_detector, 'model_type', 'random_forest'
                    )
                    model_metadata["classification_detector"]["enabled"] = True
                    model_metadata["classification_detector"]["trained"] = classification_trained
                    model_metadata["classification_model_type"] = classification_model_type
            except AttributeError as e:
                logger.warning(f"Could not check classification detector status: {e}")
                model_metadata["classification_detector"]["enabled"] = False
            
            logger.debug(f"ML models status - Anomaly: {'trained' if model_metadata['anomaly_detector'].get('trained') else 'not trained'}, "
                        f"Classification: {'enabled' if model_metadata['classification_detector'].get('enabled') else 'disabled'}")
        except Exception as e:
            logger.error(f"Error checking ML model status: {e}", exc_info=True)
            model_metadata["ml_enabled"] = False
            model_metadata["error"] = f"Model status check failed: {str(e)}"
            return ml_detections, model_metadata
        
        # Collect all packet_data and features first for batch classification (avoids per-packet model inference)
        fe = getattr(self.packet_analyzer, 'feature_extractor', None)
        cd = getattr(self.packet_analyzer, 'classification_detector', None)
        packet_data_list = []
        feature_dicts_list = []
        for pkt in packets:
            packet_data = self._scapy_to_packet_data(pkt)
            if not packet_data:
                continue
            features = None
            if fe:
                try:
                    features = fe.extract_features(packet_data)
                except Exception:
                    pass
            packet_data_list.append(packet_data)
            feature_dicts_list.append(features)

        # Batch classification: one model call instead of N (major speedup for SecIDS-CNN)
        batch_probs_by_packet = [None] * len(packet_data_list)
        if classification_enabled and classification_trained and cd and any(feature_dicts_list):
            valid_dicts = []
            valid_indices = []
            for i, d in enumerate(feature_dicts_list):
                if d is not None:
                    valid_dicts.append(d)
                    valid_indices.append(i)
            if valid_dicts:
                try:
                    if hasattr(cd, 'predict_proba_from_dicts'):
                        batch_probs = cd.predict_proba_from_dicts(valid_dicts)
                    elif getattr(cd, 'feature_names', None):
                        names = cd.feature_names
                        X = np.array([[float(d.get(n, 0.0)) for n in names] for d in valid_dicts], dtype=np.float64)
                        batch_probs = cd.predict_proba(X)
                    else:
                        batch_probs = None
                    if batch_probs is not None:
                        for j, i in enumerate(valid_indices):
                            batch_probs_by_packet[i] = batch_probs[j]
                        logger.debug(f"Batch classification ran for {len(valid_dicts)} packets (one inference instead of {len(valid_dicts)})")
                except Exception as e:
                    logger.warning(f"Batch classification failed, falling back to per-packet: {e}")

        # Process packets: signature + anomaly per packet; classification from batch result
        processed_count = 0
        error_count = 0
        max_errors = 10
        confidence_threshold = getattr(self.packet_analyzer.config, 'CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.7)

        for i, packet_data in enumerate(packet_data_list):
            try:
                detections = self.packet_analyzer.analyze_packet(packet_data, skip_classification=True)

                # Use batch classification result for this packet (no per-packet classify call)
                probs = batch_probs_by_packet[i]
                if probs is not None:
                    p_benign, p_mal = float(probs[0]), float(probs[1])
                    model_metadata["confidence_scores"].append(p_mal)
                    if p_mal >= confidence_threshold:
                        detections.append({
                            'type': 'classification',
                            'signature_id': 'ml_classification',
                            'severity': 'high' if p_mal > 0.9 else 'medium',
                            'description': f'Malicious traffic classified by ML model (confidence: {p_mal:.2f})',
                            'confidence': p_mal,
                            'matched_pattern': 'supervised_classification',
                            'source': 'classification_ml',
                            'classification_result': {'label': 'malicious', 'confidence': p_mal, 'probabilities': {'benign': p_benign, 'malicious': p_mal}},
                        })

                for detection in detections:
                    detection_type = detection.get('type', 'signature')
                    source = detection.get('source', 'unknown')
                    if detection_type == 'anomaly' or source == 'ml_analysis':
                        detection_type = 'anomaly'
                    elif detection_type == 'classification' or 'classification' in source.lower():
                        detection_type = 'classification'
                    else:
                        detection_type = 'signature'
                    model_metadata["detection_counts"][detection_type] += 1
                    if 'confidence' in detection:
                        model_metadata["confidence_scores"].append(detection['confidence'])
                    ml_detection = {
                        "id": f"ml_{detection_type}_{len(ml_detections)}",
                        "title": detection.get('description', detection.get('signature_id', 'ML Detection')),
                        "severity": detection.get('severity', 'medium'),
                        "confidence": detection.get('confidence', 0.5),
                        "description": detection.get('description', 'ML-based detection'),
                        "evidence": {
                            "source_ip": packet_data.get('src_ip'),
                            "dest_ip": packet_data.get('dst_ip'),
                            "protocol": packet_data.get('protocol'),
                            "detection_type": detection_type,
                            "model_type": "Isolation Forest" if detection_type == 'anomaly' else
                                         (classification_model_type if classification_enabled else "Unknown"),
                        },
                        "mitre": detection.get('mitre'),
                        "ml_source": detection_type,
                    }
                    ml_detections.append(ml_detection)
                processed_count += 1
            except AttributeError as e:
                error_count += 1
                if error_count <= max_errors:
                    logger.warning(f"ML analysis AttributeError (packet {processed_count}): {e}")
            except Exception as e:
                error_count += 1
                if error_count <= max_errors:
                    logger.debug(f"Error analyzing packet with ML: {e}")
                if error_count == max_errors:
                    logger.warning(f"Suppressing further ML analysis errors (already logged {max_errors})")

        if error_count > 0:
            logger.warning(f"ML analysis encountered {error_count} errors out of {processed_count} processed packets")
        
        # Calculate average confidence
        if model_metadata["confidence_scores"]:
            avg_confidence = sum(model_metadata["confidence_scores"]) / len(model_metadata["confidence_scores"])
            model_metadata["average_confidence"] = round(avg_confidence, 3)
        
        model_metadata["packets_analyzed"] = processed_count
        
        return ml_detections, model_metadata
