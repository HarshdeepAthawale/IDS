"""
PCAP upload and analysis routes.
Accepts single PCAP uploads, returns summaries and heuristic detections.
"""

import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Optional

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from models.db_models import pcap_analyses_collection, pcap_analysis_to_dict
from services.pcap_analyzer import PcapAnalyzer

logger = logging.getLogger(__name__)

pcap_bp = Blueprint("pcap", __name__)

pcap_analyzer: Optional[PcapAnalyzer] = None
packet_analyzer_instance = None
last_result = None


def init_pcap_services(config, packet_analyzer=None):
    """Initialize the PCAP analyzer with app config and optional PacketAnalyzer for ML."""
    global pcap_analyzer, packet_analyzer_instance
    packet_analyzer_instance = packet_analyzer
    pcap_analyzer = PcapAnalyzer(config, packet_analyzer=packet_analyzer)
    logger.info("PCAP analyzer initialized" + (" with ML models" if packet_analyzer else ""))


@pcap_bp.route("/api/pcap/analyze", methods=["POST"])
def analyze_pcap():
    """
    Analyze an uploaded PCAP.

    - Accepts multipart form-data with key `file` (required).
    - Optional form fields: `max_packets` (int).
    - Returns structured summary, detections, risk, and evidence.
    """
    global last_result

    try:
        if pcap_analyzer is None:
            return jsonify({"error": "PCAP analyzer not initialized"}), 500

        if "file" not in request.files:
            return jsonify({"error": "PCAP file is required under 'file' field"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Provided file has no filename"}), 400

        # Validate file extension
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in ['.pcap', '.pcapng']:
            return jsonify({
                "error": "Invalid file type",
                "details": f"File must be .pcap or .pcapng, got {file_ext}"
            }), 400

        # Validate file size (50MB limit)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                "error": "File too large",
                "details": f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds maximum allowed size (50MB)"
            }), 400

        if file_size == 0:
            return jsonify({
                "error": "Empty file",
                "details": "The uploaded file is empty"
            }), 400

        # Validate max_packets parameter
        max_packets = request.form.get("max_packets") or request.args.get("max_packets")
        packet_limit = None
        if max_packets:
            try:
                packet_limit = int(max_packets)
                if packet_limit <= 0:
                    return jsonify({
                        "error": "Invalid parameter",
                        "details": "max_packets must be a positive integer"
                    }), 400
                if packet_limit > 100000:
                    return jsonify({
                        "error": "Invalid parameter",
                        "details": "max_packets cannot exceed 100,000 for performance reasons"
                    }), 400
            except ValueError:
                return jsonify({
                    "error": "Invalid parameter",
                    "details": "max_packets must be a valid integer"
                }), 400

        # Validate PCAP file format (check magic bytes)
        file.seek(0)
        magic_bytes = file.read(4)
        file.seek(0)
        
        # PCAP magic numbers: 0xa1b2c3d4 (little-endian) or 0xd4c3b2a1 (big-endian)
        # PCAPNG magic: 0x0a0d0d0a
        valid_magic = (
            magic_bytes == b'\xd4\xc3\xb2\xa1' or  # PCAP little-endian
            magic_bytes == b'\xa1\xb2\xc3\xd4' or  # PCAP big-endian
            magic_bytes == b'\n\r\r\n'             # PCAPNG
        )
        
        if not valid_magic:
            logger.warning(f"File {filename} does not appear to be a valid PCAP file (magic bytes: {magic_bytes.hex()})")
            # Don't fail here, let Scapy try to parse it

        # Save file to temporary location
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                file.save(tmp.name)
                temp_path = tmp.name
        except OSError as e:
            logger.error(f"Failed to save temporary file: {e}")
            return jsonify({
                "error": "File I/O error",
                "details": f"Failed to save uploaded file: {str(e)}"
            }), 500

        # Analyze PCAP file
        try:
            logger.info(f"Starting PCAP analysis for {filename} ({file_size / (1024 * 1024):.2f} MB)")
            result = pcap_analyzer.analyze(temp_path, max_packets=packet_limit)
            result["metadata"]["filename"] = filename
            last_result = result

            # Persist to MongoDB if available
            if pcap_analyses_collection is not None:
                try:
                    doc = {
                        **result,
                        "filename": filename,
                        "created_at": datetime.now(timezone.utc),
                    }
                    pcap_analyses_collection.insert_one(doc)
                except Exception as db_err:
                    logger.warning("Failed to save PCAP analysis to DB: %s", db_err)

            logger.info(f"PCAP analysis completed successfully for {filename}")
            return jsonify(result)
        except ValueError as e:
            logger.error(f"PCAP parsing error for {filename}: {e}")
            return jsonify({
                "error": "PCAP parsing failed",
                "details": str(e),
                "suggestion": "Please ensure the file is a valid PCAP or PCAPNG file"
            }), 400
        except MemoryError as e:
            logger.error(f"Memory error analyzing {filename}: {e}")
            return jsonify({
                "error": "Memory error",
                "details": "File is too large to process. Try reducing max_packets or use a smaller file.",
                "file_size_mb": round(file_size / (1024 * 1024), 2)
            }), 500
        except OSError as e:
            logger.error(f"File I/O error analyzing {filename}: {e}")
            return jsonify({
                "error": "File I/O error",
                "details": f"Error reading PCAP file: {str(e)}"
            }), 500
        finally:
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except OSError as e:
                logger.warning(f"Temporary PCAP file could not be removed: {temp_path} ({e})")

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            "error": "Validation error",
            "details": str(e)
        }), 400
    except MemoryError as e:
        logger.error(f"Memory error: {e}")
        return jsonify({
            "error": "Memory error",
            "details": "Server ran out of memory processing the request. Try a smaller file or reduce max_packets."
        }), 500
    except OSError as e:
        logger.error(f"OS error: {e}")
        return jsonify({
            "error": "File system error",
            "details": str(e)
        }), 500
    except Exception as exc:
        logger.exception("Unexpected error analyzing PCAP: %s", exc)
        return jsonify({
            "error": "Failed to analyze PCAP",
            "details": str(exc),
            "type": type(exc).__name__
        }), 500


@pcap_bp.route("/api/pcap/last", methods=["GET"])
def get_last_result():
    """Return the last computed PCAP analysis (from DB if available, else in-memory)."""
    global last_result

    # Prefer latest from MongoDB
    if pcap_analyses_collection is not None:
        try:
            doc = pcap_analyses_collection.find_one(
                {},
                sort=[("created_at", -1)],
                projection={"_id": 1, "metadata": 1, "summary": 1, "detections": 1, "risk": 1, "evidence": 1, "filename": 1, "created_at": 1},
            )
            if doc is not None:
                out = pcap_analysis_to_dict(doc)
                meta = out.get("metadata") or {}
                meta["cached"] = True
                out["metadata"] = meta
                return jsonify(out)
        except Exception as e:
            logger.warning("Failed to read latest PCAP from DB: %s", e)

    if last_result:
        return jsonify({**last_result, "metadata": {**last_result.get("metadata", {}), "cached": True}})

    return jsonify({"error": "No previous analysis available. Please upload a PCAP file first."}), 404


@pcap_bp.route("/api/pcap/stats", methods=["GET"])
def get_pcap_detection_stats():
    """Return aggregated detection counts from all PCAP analyses (for dashboard/summary)."""
    global last_result

    total_detections = 0
    critical_detections = 0  # severity in ('critical', 'high')

    if pcap_analyses_collection is not None:
        try:
            cursor = pcap_analyses_collection.find(
                {},
                projection={"detections": 1},
            )
            for doc in cursor:
                detections = doc.get("detections") or []
                total_detections += len(detections)
                for d in detections:
                    sev = (d.get("severity") or "low").lower()
                    if sev in ("critical", "high"):
                        critical_detections += 1
        except Exception as e:
            logger.warning("Failed to aggregate PCAP stats from DB: %s", e)

    if total_detections == 0 and last_result:
        detections = last_result.get("detections") or []
        total_detections = len(detections)
        for d in detections:
            sev = (d.get("severity") or "low").lower()
            if sev in ("critical", "high"):
                critical_detections += 1

    return jsonify({
        "total_detections": total_detections,
        "critical_detections": critical_detections,
    })
