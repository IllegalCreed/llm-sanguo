#!/usr/bin/env python3
"""江湖变迁报告：对比最近两份 AA 快照，输出席位威胁清单。

江湖变迁 = 模型↔武将对应关系的变化（模型不成长，数值只是诱因）。
本报告回答三件事：
  1. 王座是否易主（榜首换人 → 谁该接吕布位，人工裁决）
  2. 新进榜主流模型（II ≥ 45 未设席 → 候选席位弹药）
  3. 在席模型异动（II 变化 / 退库 → 该席是否需要换防）

用法: python3 scripts/drift_report.py   → 写 docs/DRIFT.md
"""
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enrich_mapping import canonical_name  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAINSTREAM_II = 45.0


def load(path):
    best = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        k = canonical_name(r["model"])
        try:
            ii = float(r["intelligence_index"].replace("*", ""))
        except ValueError:
            continue
        if ii > best.get(k, (-1, None))[0]:
            best[k] = (ii, r["model"])
    return best


def main():
    snaps = sorted(glob.glob(os.path.join(ROOT, "data", "aa_models_snapshot_*.csv")))
    if len(snaps) < 2:
        print("不足两份快照，无从对比")
        return
    old_p, new_p = snaps[-2], snaps[-1]
    old, new = load(old_p), load(new_p)
    d_old = os.path.basename(old_p).replace("aa_models_snapshot_", "").replace(".csv", "")
    d_new = os.path.basename(new_p).replace("aa_models_snapshot_", "").replace(".csv", "")

    seated = {canonical_name(r["model"]): r for r in
              csv.DictReader(open(os.path.join(ROOT, "mapping", "mapping_v0.8.csv"), encoding="utf-8"))
              if r["model"]}

    throne_old = max(old.items(), key=lambda kv: kv[1][0])
    throne_new = max(new.items(), key=lambda kv: kv[1][0])

    lines = [f"# 江湖变迁报告 {d_old} → {d_new}",
             "",
             "> 江湖变迁 = 对应关系的变化；模型不成长，数值变化只是诱因。",
             ""]

    lines += [f"## 王座（榜首 II）",
              f"- {d_old}: **{throne_old[1][1]}** (II {throne_old[1][0]:.1f})",
              f"- {d_new}: **{throne_new[1][1]}** (II {throne_new[1][0]:.1f})"]
    if throne_old[0] != throne_new[0]:
        lines += ["", f"⚠️ **王座易主警报**：吕布位现任 {throne_old[1][1]}，新王 {throne_new[1][1]}——是否禅让由人工裁决，改后登记 mapping/seat_history.csv"]
    lines.append("")

    newcomers = sorted(((v[0], v[1]) for k, v in new.items()
                        if k not in old and v[0] >= MAINSTREAM_II), reverse=True)
    lines += [f"## 新进榜主流模型（II ≥ {MAINSTREAM_II:.0f}，{len(newcomers)} 个）"]
    armed = [f"- {n} (II {ii:.1f}){' —— 未设席，候选席位弹药' if canonical_name(n) not in seated else ''}"
             for ii, n in newcomers]
    lines += (armed or ["- 无"])
    lines.append("")

    movers = []
    for k, r in seated.items():
        if k in old and k in new and old[k][0] != new[k][0]:
            movers.append(f"- {r['general']}：{r['model']} II {old[k][0]:.1f} → {new[k][0]:.1f}")
    gone = [f"- {r['general']}：{r['model']} 已退库（快照中消失）"
            for k, r in seated.items() if k in old and k not in new]
    lines += [f"## 在席模型异动"] + (movers or ["- II 无变化"]) + [""] + \
             [f"## 在席退库"] + (gone or ["- 无"]) + [""]

    out = os.path.join(ROOT, "docs", "DRIFT.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{d_old} → {d_new} 报告 -> docs/DRIFT.md")
    if throne_old[0] != throne_new[0]:
        print("⚠️ 王座易主：", throne_old[1][1], "→", throne_new[1][1])


if __name__ == "__main__":
    main()
