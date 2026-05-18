#!/bin/bash
# Check if system has enough disk space for Docker build

set -e

echo "=== Docker Build Disk Space Checker ==="
echo ""

# Check available disk space
echo "Checking available disk space..."
df -h | grep -E "Filesystem|/$" || df -h | head -2

echo ""
echo "Docker disk usage:"
docker system df 2>/dev/null || echo "Docker not running or not installed"

echo ""
echo "=== Requirements ==="
echo "CPU mode (default):  40GB+ free disk space"
echo "GPU mode (optional): 70GB+ free disk space"
echo ""

# Extract available space (works on Linux and macOS)
if command -v df &> /dev/null; then
    # Get available space in GB for root filesystem
    AVAILABLE_GB=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
    
    if [ -z "$AVAILABLE_GB" ]; then
        # macOS format
        AVAILABLE_GB=$(df -g / | tail -1 | awk '{print $4}')
    fi
    
    echo "=== Current Status ==="
    echo "Available space: ${AVAILABLE_GB}GB"
    echo ""
    
    if [ "$AVAILABLE_GB" -lt 40 ]; then
        echo "❌ WARNING: Insufficient disk space!"
        echo "You have ${AVAILABLE_GB}GB but need at least 40GB for CPU mode."
        echo ""
        echo "Solutions:"
        echo "1. Free up disk space on your system"
        echo "2. Clean up Docker resources:"
        echo "   docker system prune -a -f"
        echo "   docker builder prune -a -f"
        echo ""
        echo "For detailed troubleshooting, see: DOCKER_DISK_SPACE.md"
        exit 1
    elif [ "$AVAILABLE_GB" -lt 70 ]; then
        echo "✅ Sufficient space for CPU mode (${AVAILABLE_GB}GB >= 40GB)"
        echo "⚠️  Insufficient space for GPU mode (need 70GB+)"
        echo ""
        echo "You can build CPU mode with: docker-compose build chandra-api"
    else
        echo "✅ Sufficient space for both CPU and GPU modes (${AVAILABLE_GB}GB >= 70GB)"
        echo ""
        echo "You can build with: docker-compose build"
    fi
else
    echo "⚠️  Cannot determine available disk space automatically."
    echo "Please manually check that you have at least 40GB free."
fi

echo ""
echo "To proceed with build:"
echo "  docker-compose build"
