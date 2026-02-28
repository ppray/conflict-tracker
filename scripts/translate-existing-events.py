#!/usr/bin/env python3
"""
Translation补全脚本 - 为现有事件添加缺失的 en/ar 翻译

读取 data/events.json，为缺少英文/阿拉伯文翻译的事件补充翻译。
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("Error: deep-translator not installed. Run: pip install deep-translator", file=sys.stderr)
    sys.exit(1)

# Configuration paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
EVENTS_FILE = DATA_DIR / "events.json"
BACKUP_FILE = DATA_DIR / f"events-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

# Rate limiting (Google Translate free tier has limits)
TRANSLATE_DELAY = 1.0  # Seconds between translations
BATCH_SIZE = 50  # Process in batches to allow manual continuation


def detect_language(text):
    """Simple language detection for Chinese, English, Arabic."""
    if not text:
        return 'auto'

    # Check for Arabic characters
    if any('\u0600' <= c <= '\u06FF' for c in text):
        return 'ar'

    # Check for Chinese characters (non-ASCII, non-Arabic)
    if any(ord(c) > 127 for c in text):
        return 'zh-CN'  # Use zh-CN for Google Translate

    return 'en'


def translate_text(text, target_lang, source_lang='auto'):
    """Translate text with error handling."""
    try:
        lang_map = {
            'zh': 'zh-CN',
            'en': 'en',
            'ar': 'ar'
        }

        if target_lang not in lang_map:
            return None

        translator = GoogleTranslator(source=source_lang, target=lang_map[target_lang])

        # Limit text length
        if len(text) > 500:
            text = text[:500] + "..."

        result = translator.translate(text)
        time.sleep(TRANSLATE_DELAY)  # Rate limiting
        return result
    except Exception as e:
        print(f"  ⚠ Translation failed: {e}", file=sys.stderr)
        return None


def complete_translations(event, verbose=False):
    """Complete missing translations for an event."""
    trans = event.get('translations', {})

    # Use direct fields as fallback for translation source
    source_title = event.get('title', '')
    source_desc = event.get('desc', '')
    source_location = event.get('locationName', '')

    # If we have zh translation, use it as source
    if 'zh' in trans and trans['zh'].get('title'):
        source_title = trans['zh']['title']
        source_desc = trans['zh'].get('desc', source_desc)
        source_location = trans['zh'].get('locationName', source_location)

    # Use auto-detection for source language (Google Translate handles this well)
    source_lang = 'auto'

    changes = []

    # Complete missing translations
    for target_lang in ['en', 'ar']:
        if target_lang not in trans:
            trans[target_lang] = {}

        # Translate title if missing
        if not trans[target_lang].get('title') and source_title:
            if verbose:
                print(f"    Translating title to {target_lang}...")
            title_trans = translate_text(source_title, target_lang, source_lang)
            if title_trans:
                trans[target_lang]['title'] = title_trans
                changes.append(f"{target_lang}.title")

        # Translate desc if missing
        if not trans[target_lang].get('desc') and source_desc:
            desc_short = source_desc[:200] + "..." if len(source_desc) > 200 else source_desc
            if verbose:
                print(f"    Translating desc to {target_lang}...")
            desc_trans = translate_text(desc_short, target_lang, source_lang)
            if desc_trans:
                trans[target_lang]['desc'] = desc_trans
                changes.append(f"{target_lang}.desc")

        # Translate locationName if missing
        if not trans[target_lang].get('locationName') and source_location:
            if verbose:
                print(f"    Translating location to {target_lang}...")
            loc_trans = translate_text(source_location, target_lang, source_lang)
            if loc_trans:
                trans[target_lang]['locationName'] = loc_trans
                changes.append(f"{target_lang}.locationName")

    # Update event translations
    event['translations'] = trans
    return changes


def main():
    """Main entry point."""
    print("=" * 60)
    print("Translation补全脚本 - Existing Events Translation补全")
    print("=" * 60)
    print()

    # Load existing events
    print(f"Loading events from {EVENTS_FILE}...")
    try:
        with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {EVENTS_FILE} not found!", file=sys.stderr)
        return 1

    events = data.get('events', [])
    print(f"Loaded {len(events)} events")
    print()

    # Backup original file
    print(f"Creating backup: {BACKUP_FILE.name}")
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print()

    # Analyze what needs translation
    missing_en = 0
    missing_ar = 0
    missing_both = 0

    for event in events:
        trans = event.get('translations', {})
        has_en = 'en' in trans and trans['en'].get('title')
        has_ar = 'ar' in trans and trans['ar'].get('title')

        if not has_en and not has_ar:
            missing_both += 1
        elif not has_en:
            missing_en += 1
        elif not has_ar:
            missing_ar += 1

    print("Translation status:")
    complete = len(events) - missing_both - missing_en - missing_ar
    print(f"  Complete (zh+en+ar): {complete}")
    print(f"  Missing en: {missing_en}")
    print(f"  Missing ar: {missing_ar}")
    print(f"  Missing both: {missing_both}")
    print()

    if missing_both + missing_en + missing_ar == 0:
        print("✓ All events already have complete translations!")
        return 0

    # Ask for confirmation
    total_to_translate = missing_en + missing_ar
    print(f"This will translate approximately {total_to_translate} missing fields.")
    print(f"Estimated time: {total_to_translate * TRANSLATE_DELAY / 60:.1f} minutes")
    print()

    response = input("Continue? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return 0

    print()
    print("Starting translation...")
    print("-" * 40)

    # Process events
    completed_count = 0
    total_changes = 0

    for i, event in enumerate(events):
        trans = event.get('translations', {})
        has_en = 'en' in trans and trans['en'].get('title')
        has_ar = 'ar' in trans and trans['ar'].get('title')

        if has_en and has_ar:
            continue

        print(f"[{i+1}/{len(events)}] Event ID: {event.get('id', 'unknown')}")

        changes = complete_translations(event, verbose=False)

        if changes:
            completed_count += 1
            total_changes += len(changes)
            print(f"    ✓ Added {len(changes)} translations: {', '.join(changes[:3])}{'...' if len(changes) > 3 else ''}")

        # Progress update every 10 events
        if (i + 1) % 10 == 0:
            print(f"    Progress: {i+1}/{len(events)} events processed")
            print()

    print()
    print("=" * 40)
    print("Translation complete!")
    print(f"  Events updated: {completed_count}")
    print(f"  Total translations added: {total_changes}")
    print()

    # Save updated events
    print(f"Saving updated events to {EVENTS_FILE}...")
    data['lastUpdated'] = datetime.now().isoformat()

    with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✓ Saved!")
    print()
    print(f"Backup saved to: {BACKUP_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
