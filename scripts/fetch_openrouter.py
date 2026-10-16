#!/usr/bin/env python3
"""抓取 OpenRouter 模型调用榜（魅力维度数据源）。

用法: python3 scripts/fetch_openrouter.py
端点: https://openrouter.ai/api/frontend/v1/rankings/models （公开，按天按模型）
输出: data/openrouter_rankings_<最新日期>.json —— 全期 rankingMetricValue 按模型聚合
      （模型魅力 = 份额 ÷ 榜首份额 × 100，折算口径与其余维度同构）
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://openrouter.ai/api/frontend/v1/rankings/models"


def main():
    raw = subprocess.run(["curl", "-s", "--max-time", "60", URL],
                         capture_output=True, text=True).stdout
    data = json.loads(raw)["data"]

    agg, dates = {}, set()
    for r in data:
        dates.add(r["date"][:10])
        agg[r["model_permaslug"]] = agg.get(r["model_permaslug"], 0) + (r.get("rankingMetricValue") or 0)

    latest = max(dates).replace("-", "")
    out = {
        "source": URL,
        "window": [min(dates), max(dates)],
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "models": agg,
    }
    path = os.path.join(ROOT, "data", f"openrouter_rankings_{latest}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"{len(agg)} models, window {out['window'][0]}~{out['window'][1]} -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
