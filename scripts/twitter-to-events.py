#!/usr/bin/env python3
"""
Twitter to Events Converter for Conflict Tracker

Fetches conflict-related tweets using Bird CLI and converts them to event objects.
Merges with existing events.json, deduplicating by tweet ID.
Supports multi-language content generation (zh/en/ar).
"""

import json
import subprocess
import sys
import re
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Try to import translation library
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("Warning: deep-translator not installed. Install with: pip install deep-translator", file=sys.stderr)

# Supported languages
LANGUAGES = ['zh', 'en', 'ar']

# Configuration paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_FILE = SCRIPT_DIR / "config.json"
LOCATIONS_FILE = SCRIPT_DIR / "locations.json"
EVENTS_FILE = DATA_DIR / "events.json"

# Default configuration (used if config.json doesn't exist)
DEFAULT_CONFIG = {
    "keywords": [
        # Iran-Israel-US war focus
        "israel iran war", "iran israel attack", "us iran strike",
        "以色列 伊朗 战争", "美国 伊朗 打击", "美以 联合 空袭",
        "tel aviv missile", "tehran strike", "persian gulf carrier",

        # Gulf countries - attacks and statements
        "saudi attack", "uae strike", "qatar missile", "bahrain base",
        "kuwait threat", "oman airspace",
        "沙特 袭击", "阿联酋 被攻击", "卡塔尔 导弹", "巴林 基地",
        "科威特 威胁", "阿曼 领空",
        "gulf countries statement", "gcc stance",

        # Airspace closures
        "airspace closed", "no-fly zone", "flight ban", "airspace restriction",
        "禁飞", "领空 关闭", "关闭 领空", "空域 封锁",
        "空域 关闭 伊朗", "以色列 禁飞",

        # Strategic locations
        "hormuz blockade", "red sea interception", "persian gulf naval",
        "霍尔木兹 封锁", "红海 拦截", "波斯湾 航母",

        # Maritime warnings and naval alerts
        "vessel not allowed", "shipping warning", "maritime alert", "naval warning",
        "strait closed", "waterway closed", "transit banned", "shipping lane closed",
        "船只 禁止", "船舶 警告", "海峡 关闭", "航道 封锁",

        # Specific events
        "gulf country attacked", "gcc base strike", "middle east escalation",
        "海湾国家 被袭", "海湾 基地 打击",

        # Hashtags for real-time tracking
        "#IsraelIran", "#USIran", "#GulfWar", "IsraelIranWar"
    ],
    "accounts": [
        # Official/Government accounts (most authoritative)
        "IDF", "IsraelWarRoom", "IsraeliPM",

        # Mainstream media and professional journalists
        "TimesofIsrael", "TOIAlerts", "BarakRavid", "AJENews",

        # Think tanks and professional analysis
        "TheStudyofWar", "criticalthreats", "UANI",

        # High-credibility OSINT accounts
        "Osinttechnical", "sentdefender", "Osint613", "IntelCrab",

        # Maritime security & naval monitoring (for Hormuz/Red Sea blockade alerts)
        "UKMTO_Dubai", "IMB_Piracy", "NavalNews", "US5thFleet", "USNavalForcesCEN"
    ],
    "countryMapping": {
        "以色列": "israel",
        "israel": "israel",
        "iran": "iran",
        "伊朗": "iran",
        "usa": "usa",
        "美国": "usa",
        "yemen": "iran",
        "也门": "iran",
        "gaza": "israel",
        "加沙": "israel",
        "lebanon": "israel",
        "黎巴嫩": "israel",
        "syria": "iran",
        "叙利亚": "iran",
        "saudi": "usa",
        "沙特": "usa",
        "uae": "usa",
        "阿联酋": "usa"
    }
}

# Default location mappings
DEFAULT_LOCATIONS = {
    "加沙": [31.5, 34.47],
    "加沙北部": [31.5, 34.47],
    "加沙南部": [31.3, 34.35],
    "加沙城": [31.5, 34.47],
    "特拉维夫": [32.08, 34.78],
    "耶路撒冷": [31.77, 35.22],
    "海法": [32.82, 34.98],
    "德黑兰": [35.69, 51.39],
    "霍尔木兹海峡": [26.56, 56.27],
    "红海": [20.0, 38.0],
    "黎巴嫩": [33.27, 35.20],
    "贝鲁特": [33.89, 35.49],
    "大马士革": [33.51, 36.29],
    "波斯湾": [27.0, 52.0],
    "约旦河西岸": [32.0, 35.2],
    "拉马拉": [31.95, 35.23],
    "汗尤尼斯": [31.34, 34.31],
    "拉法": [31.29, 34.25],
    "纳戈尔诺": [39.81, 46.76],
    "戈兰高地": [33.18, 35.73],
    "阿克萨": [31.78, 35.23],
    "伊拉克": [33.22, 43.68],
    "巴格达": [33.31, 44.36],
    "叙利亚": [34.80, 38.99],
    "也门": [15.55, 47.88],
    "萨那": [15.37, 47.61],
    "荷台达": [14.80, 42.95],
    "沙特": [23.89, 45.08],
    "利雅得": [24.71, 46.68],
    "阿联酋": [23.42, 53.85],
    "阿布扎比": [24.45, 54.38],
    "迪拜": [25.20, 55.27],
    "卡塔尔": [25.35, 51.18],
    "多哈": [25.29, 51.53],
    "科威特": [29.31, 47.48],
    "巴林": [26.06, 50.56],
    "阿曼": [21.47, 55.98],
    "马斯喀特": [23.59, 58.38],
    "土耳其": [38.96, 35.24],
    "安卡拉": [39.93, 32.85],
    "伊斯坦布尔": [41.01, 28.97],
    "约旦": [30.59, 36.24],
    "安曼": [31.95, 35.91],
    "埃及": [26.82, 30.80],
    "开罗": [30.04, 31.24],
    "塞浦路斯": [35.13, 33.43],
    "尼科西亚": [35.19, 33.38]
}

# Event type classification patterns
EVENT_TYPE_PATTERNS = {
    "strike": [
        r"空袭", r"打击", r"爆炸", r"袭击", r"攻击", r"轰炸",
        r"airstrike", r"strike", r"explosion", r"attack", r"bombing",
        r"rocket", r"missile", r"drone"
    ],
    "blockade": [
        r"封锁", r"拦截", r"扣押", r"登船",
        r"blockade", r"intercept", r"seiz[uo]re", r"boarding",
        # Maritime warning patterns - capture "warned" in naval/maritime context
        r"vessel.*not.*allowed", r"shipping.*warning", r"maritime.*alert", r"naval.*warning",
        r"ship.*banned", r"vessel.*banned", r"strait.*closed", r"waterway.*closed",
        r"vhf.*warning", r"shipping.*lane.*closed", r"passage.*denied", r"transit.*banned",
        # Chinese maritime warning patterns
        r"船只.*禁止", r"船舶.*警告", r"海峡.*关闭", r"航道.*封锁",
        r"通行.*禁止", r"航海.*警告"
    ],
    "airspace": [
        r"禁飞", r"封空", r"领空", r"防空",
        r"no-fly", r"airspace", r"air.?defen[cs]e"
    ],
    "intel": [
        r"情报", r"卫星", r"侦察", r"雷达", r"监听",
        r"intelligence", r"satellite", r"reconnaissance", r"radar"
    ],
    "diplomatic": [
        r"抗议", r"谈判", r"外交", r"声明", r"谴责", r"警告",
        r"protest", r"negotiat", r"diplomat", r"statement", r"condemn", r"warn"
    ]
}

# Country-specific fallback coordinates
COUNTRY_COORDINATES = {
    "israel": [32.0, 35.0],
    "iran": [32.0, 53.0],
    "usa": [28.5, 45.0],  # US forces in Middle East
    "saudi": [24.0, 45.0],
    "uae": [24.0, 54.0],
    "yemen": [15.5, 48.0],
    "syria": [35.0, 38.0],
    "lebanon": [34.0, 36.0],
    "turkey": [39.0, 35.0],
    "iraq": [33.0, 44.0],
    "jordan": [31.0, 36.0],
    "egypt": [27.0, 30.0]
}

# News categorization patterns
NEWS_CATEGORIES = {
    "military": [
        r"strike", r"attack", r"military", r"空袭", r"攻击",
        r"war", r"conflict", r"battle", r"warfare", r"战斗", r"战争",
        r"missile", r"drone", r"rocket", r"导弹", r"无人机", r"火箭"
    ],
    "diplomatic": [
        r"talks", r"summit", r"meeting", r"谈判", r"会议",
        r"diplomat", r"diplomacy", r"agreement", r"treaty", r"外交", r"协议",
        r"condemn", r"protest", r"warning", r"谴责", r"抗议", r"警告"
    ],
    "humanitarian": [
        r"aid", r"refugee", r"casualty", r"援助", r"难民",
        r"humanitarian", r"crisis", r"displacement", r"人道主义", r"伤亡"
    ]
}

# Middle East relevance keywords
ME_KEYWORDS = [
    "israel", "iran", "gaza", "hamas", "hezbollah",
    "以色列", "伊朗", "加沙", "哈马斯", "真主党",
    "middle east", "中东", "syria", "叙利亚",
    "yemen", "也门", "red sea", "红海",
    "hormuz", "霍尔木兹", "lebanon", "黎巴嫩",
    "palestine", "巴勒斯坦", "west bank", "约旦河西岸",
    "tel aviv", "特拉维夫", "jerusalem", "耶路撒冷",
    "tehran", "德黑兰", "gulf", "海湾", "波斯湾"
]


def load_json_file(filepath, default):
    """Load JSON file, returning default if file doesn't exist."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def translate_text(text, target_lang, source_lang='auto'):
    """Translate text to target language using deep-translator."""
    if not TRANSLATION_AVAILABLE:
        return None

    try:
        # Map language codes to deep-translator format
        lang_map = {
            'zh': 'zh-CN',
            'en': 'en',
            'ar': 'ar'
        }

        if target_lang not in lang_map:
            return None

        translator = GoogleTranslator(source=source_lang, target=lang_map[target_lang])
        # Limit text length to avoid API issues
        if len(text) > 500:
            text = text[:500] + "..."
        return translator.translate(text)
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
        print("  ⚠ Translation not available, using original text for all languages")
        return translated

    print("  🌐 Translating content...")

    # Detect if original is Chinese, English, or Arabic
    original_lang = 'en'
    if any(ord(c) > 127 and not ('\u0600' <= c <= '\u06FF') for c in title):
        # Contains non-ASCII, non-Arabic characters - likely Chinese
        original_lang = 'zh'
    elif any('\u0600' <= c <= '\u06FF' for c in title):
        # Contains Arabic characters
        original_lang = 'ar'

    # Translate to other languages
    for target_lang in LANGUAGES:
        if target_lang == original_lang:
            continue  # Skip original language

        # Translate title
        title_trans = translate_text(title, target_lang, source_lang='auto')
        if title_trans:
            translated[target_lang]['title'] = title_trans

        # Translate description (truncate if too long)
        desc_short = desc[:200] + "..." if len(desc) > 200 else desc
        desc_trans = translate_text(desc_short, target_lang, source_lang='auto')
        if desc_trans:
            translated[target_lang]['desc'] = desc_trans

        # Translate location name
        if location_name:
            loc_trans = translate_text(location_name, target_lang, source_lang='auto')
            if loc_trans:
                translated[target_lang]['locationName'] = loc_trans

    print(f"    ✓ Translations complete for {len([l for l in LANGUAGES if l != original_lang])} languages")
    return translated


def save_json_file(filepath, data):
    """Save data to JSON file with pretty formatting."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def classify_event_type(text):
    """Classify tweet text into an event type based on keywords."""
    text_lower = text.lower()

    # Check each type's patterns
    for event_type, patterns in EVENT_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return event_type

    # Default to intel if no match
    return "intel"


def extract_location_from_text(text):
    """Extract location name from tweet text."""
    # Common location patterns
    locations = []

    # Check for known locations
    for loc_name in DEFAULT_LOCATIONS.keys():
        if loc_name in text:
            # Find the most specific location (longest match)
            locations.append((loc_name, len(loc_name)))

    if locations:
        # Return the longest matching location name
        locations.sort(key=lambda x: x[1], reverse=True)
        return locations[0][0]

    return None


def detect_country(text, config):
    """Detect country from text using keywords."""
    country_mapping = config.get("countryMapping", DEFAULT_CONFIG["countryMapping"])
    text_lower = text.lower()

    for keyword, country in country_mapping.items():
        if keyword.lower() in text_lower:
            return country

    return "iran"  # Default to Iran


def get_coordinates(location_name, country):
    """Get coordinates for a location name."""
    if location_name and location_name in DEFAULT_LOCATIONS:
        return DEFAULT_LOCATIONS[location_name]

    # Fallback to country coordinates
    if country in COUNTRY_COORDINATES:
        return COUNTRY_COORDINATES[country]

    # Ultimate fallback (Middle East center)
    return [28.0, 43.0]


def parse_tweet_to_event(tweet, config):
    """Parse a tweet object into an event object with multi-language support."""
    tweet_id = tweet.get("id") or tweet.get("id_str") or str(hash(tweet.get("text", "")))
    text = tweet.get("text") or tweet.get("full_text", "")

    # Handle both old and new Bird CLI formats
    author = tweet.get("author") or tweet.get("user") or {}
    username = author.get("username") or author.get("screen_name") or "unknown"
    created_at = tweet.get("createdAt") or tweet.get("created_at", "")

    # Parse timestamp
    try:
        # Handle various timestamp formats
        if isinstance(created_at, str):
            # Try ISO format first
            if "T" in created_at:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                # Try Twitter format (e.g., "Wed Oct 05 18:23:00 +0000 2022")
                dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        else:
            dt = datetime.now(timezone.utc)
    except (ValueError, TypeError):
        dt = datetime.now(timezone.utc)

    # Classify event type
    event_type = classify_event_type(text)

    # Detect country
    country = detect_country(text, config)

    # Extract location
    location_name = extract_location_from_text(text)
    coordinates = get_coordinates(location_name, country)

    # Create title (first 50 chars, truncated at word boundary)
    title = text[:50].strip()
    if len(text) > 50:
        last_space = title.rfind(' ')
        if last_space > 30:
            title = title[:last_space] + "..."

    # Create URL
    url = f"https://twitter.com/{username}/status/{tweet_id}"

    # Create translated content
    translated = create_translated_content(
        title,
        text,
        location_name or (country.upper() if country else "MIDDLE EAST")
    )

    return {
        "id": tweet_id,
        "type": event_type,
        "country": country,
        "title": translated['zh']['title'],  # Default to Chinese for backward compatibility
        "desc": translated['zh']['desc'],
        "location": coordinates,
        "locationName": translated['zh']['locationName'],
        "time": dt.isoformat(),
        "source": f"@{username}",
        "tweetId": tweet_id,
        "url": url,
        "isNew": False,  # Will be set by frontend
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


def run_bird_search(query, count=10):
    """Run bird CLI search command."""
    try:
        cmd = ["bird", "search", query, "-n", str(count), "--json"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and result.stdout:
            try:
                # Filter out warning lines (those starting with ⚠️)
                json_lines = [line for line in result.stdout.split('\n')
                             if line.strip() and not line.strip().startswith('⚠️')]
                json_text = '\n'.join(json_lines)

                # Bird returns a JSON array
                tweets = json.loads(json_text)
                return tweets if isinstance(tweets, list) else [tweets]
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON for '{query}': {e}", file=sys.stderr)
                return []

        return []
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"Warning: Bird CLI search failed for '{query}': {e}", file=sys.stderr)
        return []


def run_bird_user_tweets(username, count=5):
    """Run bird CLI user-tweets command."""
    try:
        cmd = ["bird", "user-tweets", f"@{username}", "-n", str(count), "--json"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and result.stdout:
            try:
                # Filter out warning lines
                json_lines = [line for line in result.stdout.split('\n')
                             if line.strip() and not line.strip().startswith('⚠️')]
                json_text = '\n'.join(json_lines)

                tweets = json.loads(json_text)
                return tweets if isinstance(tweets, list) else [tweets]
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON for '@{username}': {e}", file=sys.stderr)
                return []

        return []
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"Warning: Bird CLI user-tweets failed for '@{username}': {e}", file=sys.stderr)
        return []


def run_bird_news(count=5):
    """Run bird CLI news command for trending topics."""
    try:
        cmd = ["bird", "news", "-n", str(count), "--json"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and result.stdout:
            try:
                # Filter out warning lines
                json_lines = [line for line in result.stdout.split('\n')
                             if line.strip() and not line.strip().startswith('⚠️')]
                json_text = '\n'.join(json_lines)

                news_items = json.loads(json_text)
                return news_items if isinstance(news_items, list) else [news_items]
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse news JSON: {e}", file=sys.stderr)
                return []

        return []
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"Warning: Bird CLI news failed: {e}", file=sys.stderr)
        return []


def merge_events(existing_events, new_events, max_events=100):
    """Merge new events with existing events, deduplicating by tweet ID."""
    # Create a set of existing tweet IDs
    existing_tweet_ids = {e.get("tweetId", e.get("id")) for e in existing_events}

    # Filter out duplicates
    unique_new_events = [
        e for e in new_events
        if e.get("tweetId", e.get("id")) not in existing_tweet_ids
    ]

    # Merge and sort by time (most recent first)
    all_events = existing_events + unique_new_events
    all_events.sort(key=lambda e: e.get("time", ""), reverse=True)

    # Limit to max_events
    return all_events[:max_events]


def is_news_relevant(news_item):
    """Check if news item is relevant to Middle East conflicts."""
    text = (news_item.get("text") or news_item.get("title", "")).lower()
    return any(keyword.lower() in text for keyword in ME_KEYWORDS)


def deduplicate_news(news_items, existing_news=None):
    """Remove duplicate or very similar news items."""
    if existing_news is None:
        existing_news = []

    seen = set()
    unique_items = []

    # Add existing news keys to seen set
    for item in existing_news:
        text = item.get("text") or item.get("title", "")
        key = text[:50].lower()
        seen.add(key)

    for item in news_items:
        text = item.get("text") or item.get("title", "")
        # Simple dedup: first 50 chars match
        key = text[:50].lower()
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    return unique_items


def categorize_news(news_item):
    """Categorize news item by type."""
    text = (news_item.get("text") or news_item.get("title", "")).lower()

    for category, patterns in NEWS_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return category

    return "general"


def normalize_news_item(raw_item):
    """Normalize a news item from various sources into standard format."""
    text = raw_item.get("text") or raw_item.get("title", "")

    # Extract source (try multiple fields)
    author = raw_item.get("author") or raw_item.get("user") or {}
    source = author.get("username") or author.get("screen_name") or raw_item.get("source", "Unknown")

    # Parse timestamp
    created_at = raw_item.get("createdAt") or raw_item.get("created_at") or raw_item.get("time", "")
    try:
        if isinstance(created_at, str):
            if "T" in created_at:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        else:
            dt = datetime.now(timezone.utc)
    except (ValueError, TypeError):
        dt = datetime.now(timezone.utc)

    # Generate ID
    item_id = raw_item.get("id") or f"news_{hash(text)}"

    return {
        "id": item_id,
        "title": text[:100] + "..." if len(text) > 100 else text,
        "text": text,
        "category": categorize_news(raw_item),
        "source": f"@{source}" if not source.startswith("@") else source,
        "time": dt.isoformat(),
        "url": raw_item.get("url", "")
    }


def create_ticker_texts(news_items, tweets):
    """Create ticker texts from news and tweets with multi-language support and deduplication."""
    ticker_texts = {
        'zh': [],
        'en': [],
        'ar': []
    }

    # Track seen content to avoid duplicates (using first 40 chars as key)
    seen_keys = set()

    def add_ticker_item(text, author=None):
        """Add ticker item if not duplicate."""
        # Create deduplication key (first 40 chars, lowercase, stripped)
        key = text[:40].lower().strip()
        # Remove URLs for better dedup
        key = re.sub(r'https?://\S+', '', key)
        # Remove extra whitespace
        key = ' '.join(key.split())

        if key in seen_keys or len(key) < 10:
            return False

        seen_keys.add(key)

        # Format ticker text
        if author:
            formatted = f"⚡ @{author}: {text[:80]}"
        else:
            formatted = f"⚡ {text[:100]}"

        ticker_texts['zh'].append(formatted)
        ticker_texts['en'].append(formatted)
        ticker_texts['ar'].append(formatted)
        return True

    # Add news items (filtered for relevance)
    for item in news_items[:15]:
        text = item.get("text") or item.get("title", "")
        if text and is_news_relevant(item):
            add_ticker_item(text)

    # Add recent tweets as ticker items
    for tweet in tweets[:10]:
        text = tweet.get("text") or tweet.get("full_text", "")
        if text:
            # Handle both 'author' and 'user' fields
            author = tweet.get("author") or tweet.get("user") or {}
            username = author.get("username") or author.get("screen_name", "unknown")
            add_ticker_item(text, username)

    # Limit to 15 unique items per language (reduced from 20)
    return {
        'zh': ticker_texts['zh'][:15],
        'en': ticker_texts['en'][:15],
        'ar': ticker_texts['ar'][:15]
    }


def create_templates(events):
    """Generate event templates from recent events for auto-refresh simulation with multi-language support."""
    # Select diverse events from different types and countries
    templates = {
        'zh': [],
        'en': [],
        'ar': []
    }
    seen_combinations = set()

    for event in events:
        # Create a unique key for type+country combination
        key = (event.get("type"), event.get("country"))
        if key in seen_combinations:
            continue
        seen_combinations.add(key)

        # Get translations or fall back to original text
        translations = event.get("translations", {})

        # Build complete template with all translations
        base_template = {
            "type": event.get("type"),
            "country": event.get("country"),
            "location": event.get("location"),
            "source": event.get("source", "Unknown"),
            "url": event.get("url", ""),  # Add URL field
            "tweetId": event.get("tweetId", ""),  # Add tweetId
            "translations": {}  # Full translations object
        }

        # Build translations for all languages
        for lang in LANGUAGES:
            lang_trans = translations.get(lang, {})
            base_template["translations"][lang] = {
                "title": lang_trans.get("title", event.get("title", "")),
                "desc": lang_trans.get("desc", event.get("desc", "")),
                "locationName": lang_trans.get("locationName", event.get("locationName", ""))
            }

            # Also add language-specific template list for backward compatibility
            templates[lang].append({
                "type": event.get("type"),
                "country": event.get("country"),
                "location": event.get("location"),
                "source": event.get("source", "Unknown"),
                "url": event.get("url", ""),
                "tweetId": event.get("tweetId", ""),
                "title": lang_trans.get("title", event.get("title", "")),
                "desc": lang_trans.get("desc", event.get("desc", "")),
                "locationName": lang_trans.get("locationName", event.get("locationName", "")),
                "translations": base_template["translations"]  # Include full translations
            })

        # Limit to 10 templates to keep variety
        if len(templates['zh']) >= 10:
            break

    return templates


def main():
    """Main entry point."""
    print(f"Conflict Tracker - Twitter Data Fetcher")
    print(f"=" * 50)

    # Load configuration
    config = load_json_file(CONFIG_FILE, DEFAULT_CONFIG)

    # Load existing events
    existing_data = load_json_file(EVENTS_FILE, {"events": [], "templates": [], "tickerTexts": [], "news": []})
    existing_events = existing_data.get("events", [])
    existing_templates = existing_data.get("templates", [])
    existing_news = existing_data.get("news", [])

    print(f"Loaded {len(existing_events)} existing events")

    # Fetch tweets from keyword searches
    all_tweets = []
    keywords = config.get("keywords", DEFAULT_CONFIG["keywords"])

    print(f"\nSearching {len(keywords)} keywords...")
    for keyword in keywords[:5]:  # Limit to 5 searches to avoid rate limits
        print(f"  - Searching: {keyword}")
        tweets = run_bird_search(keyword, count=5)
        all_tweets.extend(tweets)

    # Fetch from monitored accounts
    accounts = config.get("accounts", DEFAULT_CONFIG["accounts"])
    print(f"\nFetching from {len(accounts)} accounts...")
    for account in accounts[:3]:  # Limit to 3 accounts
        print(f"  - @{account}")
        tweets = run_bird_user_tweets(account, count=3)
        all_tweets.extend(tweets)

    # Fetch trending news (increased from 5 to 20)
    print(f"\nFetching trending news...")
    raw_news = run_bird_news(count=20)
    print(f"  Found {len(raw_news)} raw news items")

    # Filter for relevance
    relevant_news = [item for item in raw_news if is_news_relevant(item)]
    print(f"  {len(relevant_news)} relevant to Middle East")

    # Deduplicate with existing news
    unique_news = deduplicate_news(relevant_news, existing_news)
    print(f"  {len(unique_news)} after deduplication")

    # Normalize news items
    news_items = [normalize_news_item(item) for item in unique_news]

    print(f"\nTotal tweets fetched: {len(all_tweets)}")

    if not all_tweets:
        print("No tweets fetched. Keeping existing data unchanged.")
        return 0

    # Convert tweets to events
    new_events = []
    for tweet in all_tweets:
        try:
            event = parse_tweet_to_event(tweet, config)
            new_events.append(event)
        except Exception as e:
            print(f"Warning: Failed to parse tweet: {e}", file=sys.stderr)
            continue

    print(f"Successfully parsed {len(new_events)} events")

    # Merge with existing events
    merged_events = merge_events(existing_events, new_events)

    print(f"Total events after merge: {len(merged_events)}")

    # Create ticker texts
    ticker_texts = create_ticker_texts(news_items, all_tweets)

    # Create templates from merged events for auto-refresh simulation
    templates = create_templates(merged_events)

    # Merge news with existing (keep most recent 100)
    all_news = existing_news + news_items
    all_news.sort(key=lambda n: n.get("time", ""), reverse=True)
    merged_news = all_news[:100]

    # Save to events.json with multi-language structure
    output_data = {
        "events": merged_events,
        "templates": templates,
        "tickerTexts": ticker_texts,
        "news": merged_news,
        "languages": LANGUAGES,
        "lastUpdated": datetime.now(timezone.utc).isoformat()
    }

    save_json_file(EVENTS_FILE, output_data)

    print(f"\nSaved to {EVENTS_FILE}")
    print(f"  - Events: {len(merged_events)}")
    print(f"  - Templates: {len(templates['zh'])} per language")
    print(f"  - Ticker items: {len(ticker_texts['zh'])} per language")
    print(f"  - News items: {len(merged_news)}")
    print(f"  - Languages: {', '.join(LANGUAGES)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
