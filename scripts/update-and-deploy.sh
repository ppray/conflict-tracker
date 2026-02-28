#!/bin/bash
# Update and Deploy Script with Vercel Auto-Deploy
# 复用现有的 fetch-twitter-data.sh，然后自动提交、推送并部署到 Vercel

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

# 4. 手动触发 Vercel 部署
echo "Step 3: Triggering Vercel deployment..."
vercel deploy --prod --yes > /dev/null 2>&1

echo "✓ Deploy completed! Production updated."
