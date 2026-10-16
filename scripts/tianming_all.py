#!/usr/bin/env python3
"""天命版全量映射：全部有分模型 ↔ 全体武将的自动分配。

方法论（docs/methodology.md 三、双轨映射）：
- 天命版 = 纯强度百分位匹配，无视阵营，不打典故
- score = 0.7 × |II 百分位 − 武力百分位| + 0.3 × |成本百分位 − 智力百分位|
- 一对一分配：模型按 II 降序贪心，每个模型取剩余武将中 score 最小者
  （成本缺失的模型只按 0.7 武力项匹配）

输出: mapping/tianming_full.csv（全量天命席，独立于演义版 110 席）
"""
import csv
import glob
import os
import sys
from bisect import bisect_left

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enrich_mapping import canonical_name  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pct_of(sorted_vals, v):
    """v 在有序值表中的百分位（0-100）。"""
    if len(sorted_vals) < 2:
        return 50.0
    return bisect_left(sorted_vals, v) / (len(sorted_vals) - 1) * 100


def main():
    snap = sorted(glob.glob(os.path.join(ROOT, "data", "aa_models_snapshot_*.csv")))[-1]
    best = {}
    for r in csv.DictReader(open(snap, encoding="utf-8")):
        try:
            ii = float(r["intelligence_index"].replace("*", ""))
        except ValueError:
            continue
        try:
            cost = float(r["cost_per_task_usd"].replace("$", ""))
        except ValueError:
            cost = None
        k = canonical_name(r["model"])
        if k not in best or ii > best[k][1]:
            best[k] = (r["model"], ii, cost, r["creator"] or "--")

    models = sorted(best.values(), key=lambda t: -t[1])
    ii_sorted = sorted(m[1] for m in models)
    cost_sorted = sorted(m[2] for m in models if m[2] is not None)

    # 乱入人物过滤：所属为空即 DLC/联动/模板人物（战国秦汉、水浒、日本战国、
    # 蒙元、银英传、莱莎工房、异族模板等 130 人），天命池只用真三国武将
    officers = []
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "sanguo14_officers.csv"), encoding="utf-8")):
        if not r["affiliation"].strip():
            continue
        try:
            officers.append((r["name"], int(r["warfare"]), int(r["intellect"]), r["affiliation"]))
        except (ValueError, KeyError):
            continue
    war_sorted = sorted(o[1] for o in officers)
    int_sorted = sorted(o[2] for o in officers)
    free = {o[0]: (o[0], o[1], o[2], o[3], pct_of(war_sorted, o[1]), pct_of(int_sorted, o[2]))
            for o in officers}

    rows = []
    for name, ii, cost, creator in models:
        ip = pct_of(ii_sorted, ii)
        cp = pct_of(cost_sorted, cost) if cost is not None else None
        pick, pick_score = None, None
        for o in free.values():
            s = 0.7 * abs(ip - o[4])
            if cp is not None:
                s += 0.3 * abs(cp - o[5])
            if pick_score is None or s < pick_score:
                pick, pick_score = o, s
        if pick is None:
            break
        del free[pick[0]]
        rows.append({"model": name, "creator": creator, "ii": ii,
                     "general": pick[0], "game_affiliation": pick[3],
                     "warfare": pick[1], "intellect": pick[2],
                     "score": round(pick_score, 4)})

    out = os.path.join(ROOT, "mapping", "tianming_full.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"天命全席: {len(rows)} 对（有分模型 {len(models)}，剩余空闲武将 {len(free)}）")
    print("Top8:")
    for r in rows[:8]:
        print(f"  {r['model']:36s} II {r['ii']:5.1f} ↔ {r['general']}（武{r['warfare']} {r['game_affiliation']}）score={r['score']}")
    tight = sum(1 for r in rows if r["score"] < 5)
    print(f"score<5 的天作之合: {tight}/{len(rows)}")


if __name__ == "__main__":
    main()
