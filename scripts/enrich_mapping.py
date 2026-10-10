#!/usr/bin/env python3
"""联结 mapping_source.csv 与两份史源数据，生成 mapping_v0.2.csv。

- 游戏原版五维：data/sanguo14_officers.csv（按武将名精确匹配，繁体）
- 模型评测：data/aa_models_snapshot_2026-10-10.csv（按模型名精确→前缀→包含匹配）
- 折算武力 = round(II / 榜首II * 100)
"""
import csv
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
MAPPING = os.path.join(ROOT, "mapping")


def load_officers():
    path = os.path.join(DATA, "sanguo14_officers.csv")
    with open(path, encoding="utf-8") as f:
        return {r["name"]: r for r in csv.DictReader(f)}


def load_models():
    paths = sorted(glob.glob(os.path.join(DATA, "aa_models_snapshot_*.csv")))
    if not paths:
        sys.exit("no aa snapshot found")
    path = paths[-1]
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    def fnum(s):
        s = (s or "").strip().replace("$", "").replace("*", "")
        try:
            return float(s)
        except ValueError:
            return None

    top_ii = max((fnum(r["intelligence_index"]) or 0) for r in rows)
    out = []
    for r in rows:
        ii = fnum(r["intelligence_index"])
        cost = fnum(r["cost_per_task_usd"])
        speed = fnum(r["median_tokens_per_s"])
        out.append({
            "model": r["model"], "creator": r["creator"], "ii": ii,
            "derived_warfare": round(ii / top_ii * 100) if ii else "",
            "cost": cost, "speed": speed,
        })
    by_name = {m["model"]: m for m in out}
    return by_name, os.path.basename(path), top_ii


def match_model(name, by_name):
    if not name:
        return None
    if name in by_name:
        return by_name[name]
    low = name.lower()
    # 去掉推理档位后缀再试前缀，如 "Claude Sonnet 5.5 (max)" -> "claude sonnet 5.5"
    base = low.rsplit("(", 1)[0].strip()
    for m in by_name.values():
        if m["model"].lower().startswith(low + " ("):
            return m
    for m in by_name.values():
        if m["model"].lower().startswith(base):
            return m
    for m in by_name.values():  # 包含匹配
        if low in m["model"].lower():
            return m
    return None


def main():
    officers = load_officers()
    by_name, snapshot, top_ii = load_models()
    src = os.path.join(MAPPING, "mapping_source.csv")
    with open(src, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    header = [
        "role", "faction", "general", "model", "creator", "aa_ii",
        "derived_warfare", "cost_per_task_usd", "median_tokens_per_s",
        "game_leadership", "game_warfare", "game_intellect",
        "game_politics", "game_charm", "game_total", "note",
    ]
    out_rows, missing_officer, missing_model = [], [], []
    for r in rows:
        g = officers.get(r["general"])
        m = match_model(r["model"], by_name)
        if not g:
            missing_officer.append(r["general"])
        if not m and r["model"] and "生态" not in r["model"] and "虚位" not in r["model"]:
            missing_model.append(r["model"])
        out_rows.append({
            "role": r["role"], "faction": r["faction"],
            "general": r["general"], "model": r["model"],
            "creator": (m or {}).get("creator", ""),
            "aa_ii": (m or {}).get("ii", "") if m else "",
            "derived_warfare": (m or {}).get("derived_warfare", "") if m else "",
            "cost_per_task_usd": (m or {}).get("cost", "") if m else "",
            "median_tokens_per_s": (m or {}).get("speed", "") if m else "",
            "game_leadership": g["leadership"] if g else "",
            "game_warfare": g["warfare"] if g else "",
            "game_intellect": g["intellect"] if g else "",
            "game_politics": g["politics"] if g else "",
            "game_charm": g["charm"] if g else "",
            "game_total": g["total"] if g else "",
            "note": r["note"],
        })

    dst = os.path.join(MAPPING, "mapping_v0.2.csv")
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(out_rows)

    print(f"snapshot: {snapshot} (top II = {top_ii})")
    print(f"rows written: {len(out_rows)} -> {os.path.relpath(dst, ROOT)}")
    if missing_officer:
        print("!! officers not found in sanguo14 data:", missing_officer)
    if missing_model:
        print("!! models not matched in AA snapshot (retired/named differently):", missing_model)


if __name__ == "__main__":
    main()
