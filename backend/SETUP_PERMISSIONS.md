# Packet Capture Permissions Setup Guide

This guide explains how to set up packet capture permissions for the IDS Backend to enable real network traffic analytics without requiring sudo privileges each time.

## Overview

The IDS Backend uses Scapy to capture network packets for real-time analysis. By default, packet capture requires elevated privileges (root/sudo) on Linux systems. This guide provides multiple approaches to enable packet capture permanently.

## Why Capabilities?

Linux capabilities allow granting specific privileges to executables without running them as root. This is more secure than running the entire backend with sudo.

**Required Capabilities:**
- `cap_net_raw`: Required for raw socket access (packet capture)
- `cap_net_admin`: Required for network interface operations

## Development Setup

### Option 1: Automated Setup (Recommended)

Use the provided setup script:

```bash
cd backend
chmod +x setup_permissions.sh
./setup_permissions.sh
```

The script will:
1. Detect your venv Python binary
2. Check current capabilities
3. Set required capabilities (requires sudo one time)
4. Verify the setup

### Option 2: Manual Setup

If you prefer to set capabilities manually:

```bash
# Find your Python binary
which python3  # or: which python

# Set capabilities (replace path with your Python binary)
sudo setcap cap_net_raw,cap_net_admin=eip /path/to/venv/bin/python3

# Verify capabilities
getcap /path/to/venv/bin/python3
```

Expected output:
```
/path/to/venv/bin/python3 = cap_net_raw,cap_net_admin=eip
```

### Option 3: Smart Startup Script

Use the `start.sh` wrapper script which automatically checks and sets up permissions:

```bash
cd backend
chmod +x start.sh
./start.sh
```

The script will:
1. Check if capabilities are set
2. Prompt to run setup if needed
3. Activate venv
4. Start the backend

## Production Setup

### Systemd Service (Recommended for Production)

For production deployments, use the provided systemd service file:

1. **Copy service file:**
   ```bash
   sudo cp backend/ids-backend.service /etc/systemd/system/
   ```

2. **Edit service file** to match your deployment:
   - Update `WorkingDirectory` to your backend path
   - Update `ExecStart` to your Python binary path
   - Update `User` and `Group` (create dedicated user if needed)
   - Adjust paths in `Environment` and `ReadWritePaths`

3. **Create dedicated user** (recommended):
   ```bash
   sudo useradd -r -s /bin/false ids-backend
   sudo mkdir -p /opt/ids/backend
   sudo chown -R ids-backend:ids-backend /opt/ids/backend
   ```

4. **Install service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ids-backend.service
   sudo systemctl start ids-backend.service
   ```

5. **Check status:**
   ```bash
   sudo systemctl status ids-backend.service
   sudo journalctl -u ids-backend.service -f
   ```

**Note:** The systemd service uses `AmbientCapabilities` which is more secure than setting capabilities on the Python binary. This is the recommended approach for production.

### Alternative: Capabilities on Python Binary

If you prefer to use capabilities on the Python binary in production:

```bash
# Set capabilities on production Python binary
sudo setcap cap_net_raw,cap_net_admin=eip /opt/ids/backend/venv/bin/python3

# Verify
getcap /opt/ids/backend/venv/bin/python3
```

## Verification

After setting up permissions, verify packet capture works:

1. **Start the backend:**
   ```bash
   python app.py
   # or
   ./start.sh
   ```

2. **Check logs** for packet capture status:
   ```
   ✅ Packet sniffer started successfully!
   📡 Scapy packet capture is now active - collecting logs
   ```

3. **Verify health endpoint:**
   ```bash
   curl http://localhost:3002/api/health
   ```

   Check that `packet_sniffer` status is `running` and `capture_healthy` is `true`.

4. **Monitor packet capture:**
   - Check `/api/stats/traffic` endpoint for packet counts
   - Verify `total_packets` is increasing
   - Check that `packet_rate` is greater than 0 if there's network traffic

## Troubleshooting

### Issue: "Permission denied" errors

**Symptom:** Backend starts but packet capture fails with permission errors.

**Solutions:**
1. Verify capabilities are set:
   ```bash
   getcap /path/to/python3
   ```
   Should show: `cap_net_raw,cap_net_admin=eip`

2. Check Python binary path matches what's being used:
   ```bash
   which python3
   # Compare with getcap path
   ```

3. Re-run setup script:
   ```bash
   ./setup_permissions.sh
   ```

4. For venv, ensure you're using the venv Python:
   ```bash
   source venv/bin/activate
   which python  # Should point to venv/bin/python
   ```

### Issue: Capabilities lost after venv update

**Symptom:** Capabilities work initially but stop working after updating Python or recreating venv.

**Solution:** Re-run setup script after any venv changes:
```bash
./setup_permissions.sh
```

### Issue: File system doesn't support capabilities

**Symptom:** `setcap` fails with "Operation not supported" or similar error.

**Common causes:**
- FAT32/NTFS file systems don't support capabilities
- Mounted file system without proper options

**Solutions:**
1. Use a Linux-native file system (ext4, xfs, etc.)
2. Ensure the file system is mounted with proper options
3. Alternative: Use systemd service with AmbientCapabilities

### Issue: Systemd service doesn't have permissions

**Symptom:** Service starts but packet capture fails.

**Solutions:**
1. Verify `AmbientCapabilities` in service file:
   ```ini
   AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN
   ```

2. Check service status:
   ```bash
   sudo systemctl status ids-backend.service
   ```

3. Check logs:
   ```bash
   sudo journalctl -u ids-backend.service -n 100
   ```

4. Ensure user has proper permissions:
   ```bash
   sudo -u ids-backend getcap /opt/ids/backend/venv/bin/python3
   ```

### Issue: Backend runs but no packets captured

**Symptom:** Backend starts successfully but `total_packets` stays at 0.

**Possible causes:**
1. No network traffic on the interface
2. Wrong interface selected
3. Capabilities set but not effective

**Solutions:**
1. Verify interface is correct:
   ```bash
   # Check available interfaces
   ip link show
   # or
   ifconfig
   ```

2. Check backend logs for interface selection:
   ```
   Auto-selected interface: eth0
   ```

3. Test with network traffic:
   ```bash
   # Generate some traffic
   curl http://example.com
   # Or ping something
   ping 8.8.8.8
   ```

4. Verify capabilities are working:
   ```bash
   python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP); print('OK')"
   ```
   If this fails with "Permission denied", capabilities aren't working.

### Issue: "Invalid file" error when setting capabilities

**Symptom:** `setcap` fails with "Invalid file for capability operation".

**Cause:** The Python binary is a symlink. `setcap` cannot operate on symlinks.

**Solution:** The updated `setup_permissions.sh` script automatically detects symlinks and resolves them to the actual binary. When you run the script:

1. It detects the symlink
2. Resolves to the actual binary (e.g., `/usr/bin/python3.14`)
3. Warns you that this affects all Python scripts using that Python version
4. Sets capabilities on the actual binary

**Note:** Setting capabilities on the system Python binary affects all Python scripts using that version. This is generally safe but be aware of the security implications.

**Alternative:** Use systemd service with `AmbientCapabilities` (recommended for production) to avoid this issue.

### Issue: Capabilities verification fails

**Symptom:** `getcap` shows capabilities but packet capture still fails.

**Solutions:**
1. Ensure capabilities are set correctly:
   ```bash
   sudo setcap cap_net_raw,cap_net_admin=eip /path/to/python3
   ```

2. Verify using correct Python binary:
   ```bash
   source venv/bin/activate
   which python
   getcap $(which python)
   ```

3. Check for AppArmor/SELinux restrictions:
   ```bash
   # AppArmor
   sudo aa-status
   
   # SELinux
   sudo getenforce
   ```

4. Test with simple packet capture:
   ```python
   from scapy.all import sniff
   print("Starting capture test...")
   packets = sniff(count=1, timeout=5)
   print(f"Captured {len(packets)} packets")
   ```

## Security Considerations

### Development
- Capabilities on venv Python binary are acceptable for development
- Avoid running entire backend with sudo

### Production
- **Recommended:** Use systemd service with `AmbientCapabilities`
- Create dedicated user with minimal privileges
- Use `NoNewPrivileges=true` to prevent privilege escalation
- Set proper file system permissions

### Best Practices
1. **Minimal privileges:** Only grant required capabilities
2. **Dedicated user:** Run backend as non-root user
3. **Audit regularly:** Check capabilities are set correctly
4. **Monitor logs:** Watch for permission-related errors

## Alternative Approaches

### Docker with Capabilities

If using Docker, you can grant capabilities to the container:

```dockerfile
# Dockerfile
FROM python:3.9
# ... setup code ...
RUN setcap cap_net_raw,cap_net_admin=eip /usr/local/bin/python3.9
```

Or use `--cap-add` when running:
```bash
docker run --cap-add=NET_RAW --cap-add=NET_ADMIN ...
```

### Separate Capture Daemon

For high-security environments, consider running a separate packet capture daemon with elevated privileges and communicating via IPC. This is more complex but provides better security isolation.

## Additional Resources

- [Linux Capabilities Documentation](https://man7.org/linux/man-pages/man7/capabilities.7.html)
- [setcap man page](https://man7.org/linux/man-pages/man8/setcap.8.html)
- [Systemd Service Security](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Scapy Documentation](https://scapy.readthedocs.io/)

## Support

If you encounter issues not covered in this guide:

1. Check backend logs: `tail -f ids_backend.log`
2. Verify system configuration: `uname -a`, `lsb_release -a`
3. Review permission setup: `getcap /path/to/python3`
4. Test packet capture manually with Scapy
5. Check system security policies (AppArmor/SELinux)

For persistent issues, please create an issue with:
- System information (OS, Python version)
- Output of `getcap` command
- Backend logs
- Error messages
