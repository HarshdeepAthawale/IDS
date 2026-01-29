#!/usr/bin/env python3
"""Debug script: capture what is using port 27017. Writes NDJSON to .cursor/debug.log."""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = PROJECT_ROOT / ".cursor" / "debug.log"
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "pre-fix"


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, cwd=cwd or PROJECT_ROOT)
    return (r.stdout or "") + (r.stderr or "")


def write_log(hypothesis_id: str, message: str, data: dict):
    import time
    line = json.dumps({
        "timestamp": int(time.time() * 1000),
        "sessionId": "debug-session",
        "runId": RUN_ID,
        "hypothesisId": hypothesis_id,
        "location": "scripts/debug_port_27017.py",
        "message": message,
        "data": data,
    }) + "\n"
    with open(LOG_PATH, "a") as f:
        f.write(line)


def main():
    ss_out = run("ss -tlnp 2>/dev/null | grep 27017 || true")
    ss18_out = run("ss -tlnp 2>/dev/null | grep 27018 || true")
    lsof_out = run("lsof -i :27017 2>/dev/null || true")
    docker_out = run("docker ps -a --format '{{.Names}}\t{{.Ports}}' 2>/dev/null")
    docker_27017 = "\n".join(l for l in docker_out.splitlines() if "27017" in l or "27018" in l or "mongo" in l.lower())
    compose_ps = run("docker compose ps 2>/dev/null || true", cwd=PROJECT_ROOT) if RUN_ID == "post-fix" else ""

    write_log("H1", "ss -tlnp | grep 27017", {"output": ss_out.strip() or "(none)"})
    write_log("H5", "ss -tlnp | grep 27018 (post-fix)", {"output": ss18_out.strip() or "(none)"})
    write_log("H2", "lsof -i :27017", {"output": lsof_out.strip() or "(none)"})
    write_log("H2", "docker ps -a (mongodb/27017|27018)", {"output": docker_27017.strip() or "(none)", "full": docker_out.strip()})
    if RUN_ID == "post-fix" and compose_ps:
        write_log("H5", "docker compose ps", {"output": compose_ps.strip() or "(none)"})


if __name__ == "__main__":
    main()
