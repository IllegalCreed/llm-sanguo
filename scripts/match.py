#!/usr/bin/env python3
"""天命版自动匹配：按百分位加权距离为模型推荐武将。

score = 0.7 × |II百分位 − 武力百分位| + 0.3 × |性价比百分位 − 智力百分位|
性价比百分位 = 成本反比的百分位（越便宜百分位越高，对应"智力"越高）。

用法:
  python3 scripts/match.py --model "GPT-6 Astra (max)"
  python3 scripts/match.py --top 5 --min-total 300
"""
import argparse
import csv
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def percentile_ranks(values):
    """值 -> 群体内百分位（0~1），None 保留为 None。"""
    valid = sorted(v for v in values if v is not None)
    n = len(valid)
    out = []
    for v in values:
        if v is None:
            out.append(None)
        else:
            out.append(sum(1 for x in valid if x <= v) / n)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="查询单个模型（模糊匹配）")
    ap.add_argument("--top", type=int, default=5, help="每个模型输出的武将数")
    ap.add_argument("--min-total", type=float, default=250,
                    help="武将五维合计下限，过滤龙套（默认250，吕布合计270刚好入围）")
    args = ap.parse_args()

    # ---- 武将 ----
    with open(os.path.join(ROOT, "data", "sanguo14_officers.csv"), encoding="utf-8") as f:
        officers = [r for r in csv.DictReader(f)]
    officers = [r for r in officers if float(r["total"] or 0) >= args.min_total]
    war_pct = percentile_ranks([float(r["warfare"]) for r in officers])
    int_pct = percentile_ranks([float(r["intellect"]) for r in officers])

    # ---- 模型 ----
    snap = sorted(glob.glob(os.path.join(ROOT, "data", "aa_models_snapshot_*.csv")))[-1]
    with open(snap, encoding="utf-8") as f:
        models = [r for r in csv.DictReader(f)]

    def fnum(s):
        s = (s or "").strip().replace("$", "").replace("*", "")
        try:
            return float(s)
        except ValueError:
            return None

    ii = [fnum(r["intelligence_index"]) for r in models]
    cost = [fnum(r["cost_per_task_usd"]) for r in models]
    ii_pct = percentile_ranks(ii)
    # 便宜 -> 高性价比百分位
    cheap_pct = percentile_ranks([-c if c is not None else None for c in cost])

    scored = []
    for i, m in enumerate(models):
        if ii_pct[i] is None:
            continue
        scored.append({
            "model": m["model"], "creator": m["creator"],
            "ii": ii[i], "ii_pct": ii_pct[i], "cheap_pct": cheap_pct[i],
        })
    scored.sort(key=lambda x: -x["ii"])

    if args.model:
        key = args.model.lower()
        scored = [s for s in scored if key in s["model"].lower()]
        if not scored:
            raise SystemExit(f"no model matched: {args.model}")

    lines = []
    for s in scored:
        cands = []
        for j, o in enumerate(officers):
            d1 = abs(s["ii_pct"] - war_pct[j])
            d2 = abs((s["cheap_pct"] or 0) - int_pct[j]) if s["cheap_pct"] is not None else None
            score = 0.7 * d1 + (0.3 * d2 if d2 is not None else 0.15)
            cands.append((score, o["name"], o["warfare"], o["intellect"]))
        cands.sort()
        top = cands[: args.top]
        lines.append({
            "model": s["model"], "creator": s["creator"], "ii": s["ii"],
            "ii_percentile": round(s["ii_pct"], 3),
            "best_generals": "; ".join(
                f"{n}(武{w}/智{it}, 距离{sc:.3f})" for sc, n, w, it in top
            ),
        })

    out = os.path.join(ROOT, "mapping", "suggestions_tianming.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["model", "creator", "ii", "ii_percentile", "best_generals"])
        w.writeheader()
        w.writerows(lines)

    for line in lines[:20]:
        print(f"[{line['ii']:>5}] {line['model']:<45} -> {line['best_generals']}")
    print(f"... total {len(lines)} models -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
