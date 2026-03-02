#!/usr/bin/env python3
"""
Safe update script for events.json
Ensures no existing events are lost
Supports multi-language content generation (zh/en/ar)
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import shutil

# Try to import translation library
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("Warning: deep-translator not installed. Install with: pip install deep-translator", file=sys.stderr)

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
EVENTS_FILE = DATA_DIR / "events.json"
BACKUP_DIR = DATA_DIR / "backups"

# Supported languages
LANGUAGES = ['zh', 'en', 'ar']

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

# Rate limiting for translation
TRANSLATE_DELAY = 1.0


def create_backup():
    """Create a backup of the current events.json"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = BACKUP_DIR / f"events-{timestamp}.json"
    shutil.copy2(EVENTS_FILE, backup_file)
    print(f"✓ Backup created: {backup_file}")
    return backup_file


def translate_text(text, target_lang, source_lang='auto'):
    """Translate text to target language using deep-translator."""
    if not TRANSLATION_AVAILABLE:
        return None

    try:
        lang_map = {
            'zh': 'zh-CN',
            'en': 'en',
            'ar': 'ar'
        }

        if target_lang not in lang_map:
            return None

        translator = GoogleTranslator(source=source_lang, target=lang_map[target_lang])
        if len(text) > 500:
            text = text[:500] + "..."
        result = translator.translate(text)
        time.sleep(TRANSLATE_DELAY)
        return result
    except Exception as e:
        print(f"Warning: Translation failed for {target_lang}: {e}", file=sys.stderr)
        return None


def create_translated_content(title, desc, location_name):
    """Create translated versions of content for all supported languages."""
    translated = {
        'zh': {'title': title, 'desc': desc, 'locationName': location_name},
        'en': {'title': title, 'desc': desc, 'locationName': location_name},
        'ar': {'title': title, 'desc': desc, 'locationName': location_name}
    }

    if not TRANSLATION_AVAILABLE:
        return translated

    # Detect original language
    original_lang = 'en'
    if any(ord(c) > 127 and not ('\u0600' <= c <= '\u06FF') for c in title):
        original_lang = 'zh'
    elif any('\u0600' <= c <= '\u06FF' for c in title):
        original_lang = 'ar'

    # Translate to other languages
    for target_lang in LANGUAGES:
        if target_lang == original_lang:
            continue

        title_trans = translate_text(title, target_lang, source_lang='auto')
        if title_trans:
            translated[target_lang]['title'] = title_trans

        desc_short = desc[:200] + "..." if len(desc) > 200 else desc
        desc_trans = translate_text(desc_short, target_lang, source_lang='auto')
        if desc_trans:
            translated[target_lang]['desc'] = desc_trans

        if location_name:
            loc_trans = translate_text(location_name, target_lang, source_lang='auto')
            if loc_trans:
                translated[target_lang]['locationName'] = loc_trans

    return translated


def search_tweets(query, count=10):
    """Search for tweets using bird CLI"""
    try:
        cmd = ["bird", "search", query, "-n", str(count), "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # Filter out warning lines
            json_lines = [line for line in result.stdout.split('\n')
                         if line.strip() and not line.strip().startswith('⚠️')]
            json_text = '\n'.join(json_lines)
            return json.loads(json_text) if json_text else []
        else:
            print(f"Error searching for {query}: {result.stderr}", file=sys.stderr)
            return []
    except subprocess.TimeoutExpired:
        print(f"Timeout searching for {query}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error searching for {query}: {e}", file=sys.stderr)
        return []


def main():
    print("=== Safe Update Script (Multi-language) ===")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Languages: {', '.join(LANGUAGES)}")
    print()

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
        print(f"✗ Error loading events: {e}", file=sys.stderr)
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

            text = tweet.get("text", "")
            author = tweet.get("author", {})
            username = author.get("username", "unknown")

            # Create translated content
            translated = create_translated_content(
                text[:100],
                text,
                "以色列"  # Default location name
            )

            # Create event object with multi-language support
            event = {
                "id": tweet_id,
                "type": "intel",
                "country": "israel",
                "title": translated['zh']['title'],  # Default to Chinese
                "desc": translated['zh']['desc'],
                "location": [32.0, 35.0],
                "locationName": translated['zh']['locationName'],
                "time": tweet.get("createdAt", datetime.now(timezone.utc).isoformat()),
                "source": f"@{username}",
                "tweetId": tweet_id,
                "url": f"https://twitter.com/{username}/status/{tweet_id}",
                "isNew": True,
                "translations": {
                    "zh": {
                        "title": translated['zh']['title'],
                        "desc": translated['zh']['desc'],
                        "locationName": translated['zh']['locationName']
                    },
                    "en": {
                        "title": translated['en']['title'],
                        "desc": translated['en']['desc'],
                        "locationName": translated['en']['locationName']
                    },
                    "ar": {
                        "title": translated['ar']['title'],
                        "desc": translated['ar']['desc'],
                        "locationName": translated['ar']['locationName']
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
        print(f"✗ ERROR: Event count decreased! {len(existing_events)} → {len(all_events)}", file=sys.stderr)
        print("This should never happen. Aborting save.", file=sys.stderr)
        return 1

    # Save to file
    try:
        with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ Updated {EVENTS_FILE}")
        print(f"✓ Total events: {len(all_events)} (+{len(new_events)} new)")
        print(f"✓ Backup: {backup_file}")
    except Exception as e:
        print(f"✗ Error saving events: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
