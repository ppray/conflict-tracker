#!/bin/bash
#
# fetch-trending.sh
#
# Shell wrapper for fetching trending news via Bird CLI.
# Updates only the ticker texts in events.json without modifying events.
#
# Usage:
#   ./scripts/fetch-trending.sh
#
# Cron example (every hour):
#   0 * * * * cd /path/to/conflict-tracker && ./scripts/fetch-trending.sh >> logs/trending.log 2>&1

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log file location
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/trending.log"
EVENTS_FILE="$PROJECT_ROOT/data/events.json"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Print timestamp
echo "=========================================="
echo "Trending News Fetch - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=========================================="

# Check if bird CLI is installed
if ! command -v bird &> /dev/null; then
    echo "ERROR: 'bird' CLI not found. Please install it first:"
    echo "  https://github.com/steipete/bird"
    exit 1
fi

# Check if events.json exists
if [ ! -f "$EVENTS_FILE" ]; then
    echo "ERROR: events.json not found at $EVENTS_FILE"
    exit 1
fi

# Fetch trending news
echo "Fetching trending news..."
TICKER_ITEMS=$(bird news -n 10 --json 2>/dev/null | python3 -c "
import json, sys
items = []
for line in sys.stdin:
    if line.strip():
        try:
            data = json.loads(line)
            text = data.get('text') or data.get('title', '')
            if text:
                items.append('⚡ ' + text[:100])
        except json.JSONDecodeError:
            continue

# Create ticker array
print(json.dumps(items))
")

if [ -z "$TICKER_ITEMS" ]; then
    echo "Warning: No trending items fetched"
    TICKER_ITEMS='[]'
fi

# Update events.json with new ticker texts
echo "Updating ticker texts..."
python3 - <<EOF
import json

# Load existing data
with open('$EVENTS_FILE', 'r') as f:
    data = json.load(f)

# Update ticker texts
ticker_items = $TICKER_ITEMS
data['tickerTexts'] = ticker_items

# Save back
with open('$EVENTS_FILE', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✓ Updated {len(ticker_items)} ticker items")
EOF

echo "✓ Trending fetch completed"
echo "=========================================="

exit 0
