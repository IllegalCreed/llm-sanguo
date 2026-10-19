#!/bin/bash
# 一键江湖更新：抓快照 + 抓调用榜 + 重算映射 + 重建站点 + 变迁报告
# 用法: ./scripts/pipeline.sh   （GitHub Actions 每周一自动跑，见 .github/workflows/）
set -euo pipefail
cd "$(dirname "$0")/.."

DATE=$(date +%Y-%m-%d)
echo "== 1/6 抓 AA 快照 ($DATE) =="
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
ok=0
for i in 1 2 3; do
  curl -s --compressed -A "$UA" --max-time 90 -o /tmp/leaderboard.html "https://artificialanalysis.ai/leaderboards/models"
  if python3 scripts/rebuild_snapshot.py --leaderboard /tmp/leaderboard.html "data/aa_models_snapshot_${DATE}.csv"; then ok=1; break; fi
  echo "第 $i 次抓取/解析失败，20s 后重试…"; sleep 20
done
if [ "$ok" != 1 ]; then
  echo "::warning::AA 快照抓取失败（疑似数据中心 IP 被反爬拦截），本轮跳过快照更新，沿用最新历史快照"
  rm -f "data/aa_models_snapshot_${DATE}.csv"
fi

echo "== 2/6 抓 OpenRouter 调用榜 =="
python3 scripts/fetch_openrouter.py || echo "(跳过：OpenRouter 拉取失败)"

echo "== 3/6 重算映射（数值自动流动，席位不动）=="
python3 scripts/enrich_mapping.py

echo "== 4/6 重建站点 =="
python3 scripts/build_site.py

echo "== 5/6 天命全席重排 =="
python3 scripts/tianming_all.py

echo "== 6/6 江湖变迁报告 =="
python3 scripts/drift_report.py

echo "完成。席位易主需人工裁决：改 mapping_source.csv → 重跑 enrich+build → 登记 seat_history.csv"
