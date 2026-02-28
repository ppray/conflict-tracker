#!/bin/bash
#
# fetch-twitter-data.sh
#
# Shell wrapper for fetching Twitter data via Bird CLI.
# This script is intended to be run via cron for automated data updates.
#
# Usage:
#   ./scripts/fetch-twitter-data.sh
#
# Cron example (every 15 minutes):
#   */15 * * * * cd /path/to/conflict-tracker && ./scripts/fetch-twitter-data.sh >> logs/fetch.log 2>&1

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log file location
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/fetch.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Print timestamp
echo "=========================================="
echo "Twitter Data Fetch - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=========================================="

# Check if bird CLI is installed
if ! command -v bird &> /dev/null; then
    echo "ERROR: 'bird' CLI not found. Please install it first:"
    echo "  https://github.com/steipete/bird"
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found"
    exit 1
fi

# Change to project root directory
cd "$PROJECT_ROOT"

# Run the Python script
echo "Running twitter-to-events.py..."
python3 "$SCRIPT_DIR/twitter-to-events.py"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Fetch completed successfully"
else
    echo "✗ Fetch failed with exit code $EXIT_CODE"
fi

echo "=========================================="

exit $EXIT_CODE
