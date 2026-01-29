#!/bin/bash
# Smart startup wrapper that checks permissions and starts backend
# Automatically sets up capabilities if needed

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "IDS Backend - Smart Startup"
echo "==========================================${NC}"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${YELLOW}Warning: This script is designed for Linux systems.${NC}"
    echo "For Windows, run as Administrator instead."
    echo ""
fi

# Find Python binary in venv
PYTHON_BINARY=""
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

if [ -f "$VENV_PYTHON" ]; then
    PYTHON_BINARY="$VENV_PYTHON"
elif [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_BINARY="$SCRIPT_DIR/venv/bin/python"
else
    # Check for system Python
    SYSTEM_PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
    if [ -n "$SYSTEM_PYTHON" ]; then
        PYTHON_BINARY="$SYSTEM_PYTHON"
        echo -e "${YELLOW}⚠ Using system Python (venv not found)${NC}"
    else
        echo -e "${RED}✗ Python not found. Please install Python 3.${NC}"
        exit 1
    fi
fi

# Check if venv exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo -e "${GREEN}✓ Virtual environment found${NC}"
    # Activate venv
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo -e "${YELLOW}⚠ Virtual environment not found${NC}"
    echo "Run 'python3 -m venv venv' and 'pip install -r requirements.txt' first"
    read -p "Continue with system Python? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if capabilities are set (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v getcap &> /dev/null; then
    CURRENT_CAPS=$(getcap "$PYTHON_BINARY" 2>/dev/null || echo "")
    
    if [[ -z "$CURRENT_CAPS" ]] || [[ "$CURRENT_CAPS" != *"cap_net_raw"* ]] || [[ "$CURRENT_CAPS" != *"cap_net_admin"* ]]; then
        echo -e "${YELLOW}⚠ Packet capture capabilities not set${NC}"
        echo ""
        echo "To enable packet capture without sudo, you need to set capabilities."
        echo ""
        read -p "Run setup_permissions.sh now? (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            if [ -f "$SCRIPT_DIR/setup_permissions.sh" ]; then
                echo ""
                echo "Running setup_permissions.sh..."
                bash "$SCRIPT_DIR/setup_permissions.sh"
                echo ""
                
                # Re-check capabilities
                CURRENT_CAPS=$(getcap "$PYTHON_BINARY" 2>/dev/null || echo "")
                if [[ "$CURRENT_CAPS" == *"cap_net_raw"* ]] && [[ "$CURRENT_CAPS" == *"cap_net_admin"* ]]; then
                    echo -e "${GREEN}✓ Capabilities set successfully!${NC}"
                else
                    echo -e "${YELLOW}⚠ Capabilities setup may have failed. Continuing anyway...${NC}"
                    echo "Packet capture may require sudo privileges."
                fi
            else
                echo -e "${RED}✗ setup_permissions.sh not found${NC}"
                echo "You can set capabilities manually:"
                echo "  sudo setcap cap_net_raw,cap_net_admin=eip $PYTHON_BINARY"
            fi
        else
            echo -e "${YELLOW}Continuing without capabilities...${NC}"
            echo "Packet capture will require sudo privileges."
            echo "You can set capabilities later with: ./setup_permissions.sh"
        fi
        echo ""
    else
        echo -e "${GREEN}✓ Packet capture capabilities verified${NC}"
    fi
fi

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    if [ -f "$SCRIPT_DIR/env.example" ]; then
        echo -e "${YELLOW}⚠ .env file not found${NC}"
        echo "Copying env.example to .env..."
        cp "$SCRIPT_DIR/env.example" "$SCRIPT_DIR/.env"
        echo -e "${GREEN}✓ Created .env file from template${NC}"
        echo -e "${YELLOW}Please edit .env with your configuration before continuing${NC}"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠ .env file not found (no env.example template either)${NC}"
    fi
fi

# Check for required dependencies
echo "Checking dependencies..."
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Flask not found. Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Starting IDS Backend..."
echo "==========================================${NC}"
echo ""

# Get configuration from environment or use defaults
FLASK_ENV=${FLASK_ENV:-development}
FLASK_HOST=${FLASK_HOST:-0.0.0.0}
FLASK_PORT=${FLASK_PORT:-3002}

echo "Configuration:"
echo "  Environment: $FLASK_ENV"
echo "  Host: $FLASK_HOST"
echo "  Port: $FLASK_PORT"
echo ""

# Export environment variables
export FLASK_ENV=$FLASK_ENV
export FLASK_HOST=$FLASK_HOST
export FLASK_PORT=$FLASK_PORT

# Start the backend
echo -e "${BLUE}Starting backend server...${NC}"
echo ""

exec python app.py
