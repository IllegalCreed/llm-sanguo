#!/bin/bash
# 一键江湖更新：抓快照 + 抓调用榜 + 重算映射 + 重建站点 + 变迁报告
# 用法: ./scripts/pipeline.sh   （GitHub Actions 每周一自动跑，见 .github/workflows/）
set -euo pipefail
cd "$(dirname "$0")/.."

DATE=$(date +%Y-%m-%d)
echo "== 1/5 抓 AA 快照（$DATE）=="
curl -s --max-time 90 -o /tmp/leaderboard.html "https://artificialanalysis.ai/leaderboards/models"
python3 scripts/rebuild_snapshot.py --leaderboard /tmp/leaderboard.html "data/aa_models_snapshot_${DATE}.csv"

echo "== 2/5 抓 OpenRouter 调用榜 =="
python3 scripts/fetch_openrouter.py || echo "(跳过：OpenRouter 拉取失败)"

echo "== 3/5 重算映射（数值自动流动，席位不动）=="
python3 scripts/enrich_mapping.py

echo "== 4/5 重建站点 =="
python3 scripts/build_site.py

echo "== 5/5 江湖变迁报告 =="
python3 scripts/drift_report.py

echo "完成。席位易主需人工裁决：改 mapping_source.csv → 重跑 enrich+build → 登记 seat_history.csv"
