#!/usr/bin/env python3
"""
Safe update script for events.json
Ensures no existing events are lost
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import shutil

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
EVENTS_FILE = DATA_DIR / "events.json"
BACKUP_DIR = DATA_DIR / "backups"

# Keywords to search
KEYWORDS = [
    "israel iran",
    "iran attack",
    "gulf war",
    "tel aviv missile",
    "tehran strike",
]

# Maximum tweets per keyword
MAX_TWEETS = 5

def create_backup():
    """Create a backup of the current events.json"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = BACKUP_DIR / f"events-{timestamp}.json"
    shutil.copy2(EVENTS_FILE, backup_file)
    print(f"✓ Backup created: {backup_file}")
    return backup_file

def search_tweets(query, count=10):
    """Search for tweets using bird CLI"""
    try:
        cmd = ["bird", "search", query, "-n", str(count), "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Error searching for {query}: {result.stderr}", file=__import__('sys').stderr)
            return []
    except subprocess.TimeoutExpired:
        print(f"Timeout searching for {query}", file=__import__('sys').stderr)
        return []
    except Exception as e:
        print(f"Error searching for {query}: {e}", file=__import__('sys').stderr)
        return []

def main():
    print("=== Safe Update Script ===")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Create backup first
    backup_file = create_backup()
    
    # Load existing events
    try:
        with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing_events = data.get("events", [])
            existing_tweet_ids = {event.get("tweetId") for event in existing_events}
        print(f"✓ Loaded {len(existing_events)} existing events")
    except Exception as e:
        print(f"✗ Error loading events: {e}", file=__import__('sys').stderr)
        return 1
    
    # Search for new tweets
    new_events = []
    for keyword in KEYWORDS:
        print(f"Searching: {keyword}")
        tweets = search_tweets(keyword, MAX_TWEETS)
        
        for tweet in tweets:
            tweet_id = tweet.get("id")
            if not tweet_id or tweet_id in existing_tweet_ids:
                continue
            
            # Create event object
            event = {
                "id": tweet_id,
                "type": "intel",
                "country": "israel",
                "title": tweet.get("text", "")[:100],
                "desc": tweet.get("text", ""),
                "location": [32.0, 35.0],
                "locationName": "以色列",
                "time": tweet.get("createdAt", datetime.now(timezone.utc).isoformat()),
                "source": f"@{tweet.get('author', {}).get('username', 'unknown')}",
                "tweetId": tweet_id,
                "url": f"https://twitter.com/{tweet.get('author', {}).get('username', 'unknown')}/status/{tweet_id}",
                "isNew": True,
                "translations": {
                    "zh": {
                        "title": tweet.get("text", "")[:100],
                        "desc": tweet.get("text", ""),
                        "locationName": "以色列"
                    }
                }
            }
            
            new_events.append(event)
            existing_tweet_ids.add(tweet_id)
    
    print(f"✓ Found {len(new_events)} new events")
    
    # CRITICAL: Keep ALL existing events, add new ones at the beginning
    all_events = new_events + existing_events
    
    # Update data
    data["events"] = all_events
    data["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    
    # Validate before saving
    if len(all_events) < len(existing_events):
        print(f"✗ ERROR: Event count decreased! {len(existing_events)} → {len(all_events)}", file=__import__('sys').stderr)
        print("This should never happen. Aborting save.", file=__import__('sys').stderr)
        return 1
    
    # Save to file
    try:
        with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ Updated {EVENTS_FILE}")
        print(f"✓ Total events: {len(all_events)} (+{len(new_events)} new)")
        print(f"✓ Backup: {backup_file}")
    except Exception as e:
        print(f"✗ Error saving events: {e}", file=__import__('sys').stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
