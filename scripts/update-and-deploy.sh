#!/bin/bash
# Update and Deploy Script
# 复用现有的 fetch-twitter-data.sh，然后自动提交和推送

set -e

PROJECT_DIR="/Users/guoruidong/conflict-tracker"
cd "$PROJECT_DIR"

echo "=== Update and Deploy - $(date) ==="

# 1. 使用安全的更新脚本获取数据
echo "Step 1: Fetching Twitter data (safe mode)..."
python3 ./scripts/safe-update.py

# 2. 检查是否有变化
if git diff --quiet data/events.json; then
    echo "No changes in events.json, exiting."
    exit 0
fi

# 3. 提交并推送
echo "Step 2: Committing and pushing..."
git add data/events.json
git commit -m "Update events data [skip ci]"
git push origin main

echo "✓ Deploy triggered! Vercel will update in ~30-60s"
