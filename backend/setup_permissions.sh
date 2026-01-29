#!/bin/bash
# Automatically sets capabilities for packet capture on venv Python
# This allows packet capture without sudo after initial setup

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "IDS Backend - Permission Setup Script"
echo "=========================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${YELLOW}Warning: This script is designed for Linux systems.${NC}"
    echo "For Windows, run as Administrator instead."
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Find Python binary in venv
PYTHON_BINARY=""
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

if [ -f "$VENV_PYTHON" ] || [ -L "$VENV_PYTHON" ]; then
    PYTHON_BINARY="$VENV_PYTHON"
    echo -e "${GREEN}✓ Found venv Python: $PYTHON_BINARY${NC}"
elif [ -f "$SCRIPT_DIR/venv/bin/python" ] || [ -L "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_BINARY="$SCRIPT_DIR/venv/bin/python"
    echo -e "${GREEN}✓ Found venv Python: $PYTHON_BINARY${NC}"
else
    # Check for system Python
    SYSTEM_PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
    if [ -n "$SYSTEM_PYTHON" ]; then
        echo -e "${YELLOW}⚠ Venv Python not found at $VENV_PYTHON${NC}"
        echo "Found system Python: $SYSTEM_PYTHON"
        read -p "Use system Python? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            PYTHON_BINARY="$SYSTEM_PYTHON"
        else
            echo -e "${RED}✗ Please create a virtual environment first:${NC}"
            echo "  python3 -m venv venv"
            echo "  source venv/bin/activate"
            echo "  pip install -r requirements.txt"
            exit 1
        fi
    else
        echo -e "${RED}✗ Python not found. Please install Python 3.${NC}"
        exit 1
    fi
fi

# Check if Python binary is a symlink and resolve to actual binary
ACTUAL_PYTHON_BINARY=""
if [ -L "$PYTHON_BINARY" ]; then
    # Resolve symlink to actual binary
    ACTUAL_PYTHON_BINARY=$(readlink -f "$PYTHON_BINARY" 2>/dev/null || realpath "$PYTHON_BINARY" 2>/dev/null)
    if [ -n "$ACTUAL_PYTHON_BINARY" ] && [ -f "$ACTUAL_PYTHON_BINARY" ]; then
        echo -e "${YELLOW}⚠ Python binary is a symlink${NC}"
        echo "  Symlink: $PYTHON_BINARY"
        echo "  Actual binary: $ACTUAL_PYTHON_BINARY"
        echo ""
        echo "Capabilities must be set on the actual binary (not the symlink)."
        echo -e "${YELLOW}Note: This will affect all Python scripts using this Python version.${NC}"
        echo ""
        read -p "Set capabilities on actual binary? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo -e "${YELLOW}Cancelled. Capabilities not set.${NC}"
            echo ""
            echo "Alternative: Use systemd service with AmbientCapabilities (recommended for production):"
            echo "  See SETUP_PERMISSIONS.md for details"
            exit 0
        fi
        PYTHON_BINARY="$ACTUAL_PYTHON_BINARY"
    else
        echo -e "${RED}✗ Could not resolve symlink to actual binary${NC}"
        exit 1
    fi
fi

echo ""
echo "Python binary: $PYTHON_BINARY"

# Check if setcap command exists
if ! command -v setcap &> /dev/null; then
    echo -e "${RED}✗ setcap command not found.${NC}"
    echo "Install libcap2-bin package:"
    echo "  sudo apt-get install libcap2-bin"
    exit 1
fi

# Check current capabilities
echo ""
echo "Checking current capabilities..."
CURRENT_CAPS=$(getcap "$PYTHON_BINARY" 2>/dev/null || echo "")

if [ -n "$CURRENT_CAPS" ]; then
    echo "Current capabilities: $CURRENT_CAPS"
    # Check if required capabilities are already set
    if [[ "$CURRENT_CAPS" == *"cap_net_raw"* ]] && [[ "$CURRENT_CAPS" == *"cap_net_admin"* ]]; then
        echo -e "${GREEN}✓ Required capabilities are already set!${NC}"
        echo ""
        read -p "Reset capabilities anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Capabilities unchanged."
            exit 0
        fi
    fi
else
    echo "No capabilities currently set."
fi

# Set capabilities
echo ""
echo "Setting capabilities for packet capture..."
echo "This requires sudo privileges."

if sudo setcap cap_net_raw,cap_net_admin=eip "$PYTHON_BINARY"; then
    echo -e "${GREEN}✓ Capabilities set successfully!${NC}"
    echo ""
    
    # Verify capabilities
    VERIFIED_CAPS=$(getcap "$PYTHON_BINARY" 2>/dev/null || echo "")
    echo "Verified capabilities: $VERIFIED_CAPS"
    echo ""
    
    if [[ "$VERIFIED_CAPS" == *"cap_net_raw"* ]] && [[ "$VERIFIED_CAPS" == *"cap_net_admin"* ]]; then
        echo -e "${GREEN}✓ Verification successful!${NC}"
        echo ""
        echo "=========================================="
        echo "Setup complete!"
        echo "=========================================="
        echo ""
        echo "You can now run the backend without sudo:"
        echo "  python app.py"
        echo ""
        echo "Or use the start.sh wrapper:"
        echo "  ./start.sh"
        echo ""
        echo -e "${YELLOW}Note: If you update Python or recreate the venv,${NC}"
        echo -e "${YELLOW}you'll need to run this script again.${NC}"
        if [ -L "$VENV_PYTHON" ] || [ -L "$SCRIPT_DIR/venv/bin/python" ]; then
            echo ""
            echo -e "${YELLOW}Important: Capabilities were set on the system Python binary${NC}"
            echo -e "${YELLOW}(since venv uses a symlink). This affects all Python scripts${NC}"
            echo -e "${YELLOW}using this Python version.${NC}"
        fi
    else
        echo -e "${RED}✗ Verification failed. Capabilities may not be set correctly.${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Failed to set capabilities.${NC}"
    echo ""
    echo "Possible reasons:"
    echo "  1. Insufficient sudo privileges"
    echo "  2. File system doesn't support capabilities (e.g., FAT32)"
    echo "  3. setcap utility not working properly"
    echo ""
    echo "Alternative: Run backend with sudo (less secure):"
    echo "  sudo python app.py"
    exit 1
fi
