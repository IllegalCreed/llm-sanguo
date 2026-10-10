#!/usr/bin/env python3
"""联结 mapping_source.csv 与两份史源数据，生成 mapping_v0.5.csv。

- 游戏原版五维：data/sanguo14_officers.csv（按武将名精确匹配，繁体）
- 模型评测：data/aa_models_snapshot_*.csv（取最新一份快照）
- 主公位 = 厂家/机构位，只写公司名，不落具体模型，永不参与联结
- 武将/诸侯位 = 具体模型位（模型退役与否写进 note，不设"已故"角色——严格说
  来三国武将都已作古）。模型名书写规范：不带推理档位后缀
  （max/xhigh/high/medium/low、with fallback 一律省略）。联结时按去档位
  后的基名聚合快照中同基名的各档位行，统一取 II 最高的那一档；
  版本日期（如 "(0902)"）、特供版（如 "(Daybreak Blue)"）、变体
  （如 "(non-reasoning)"）等非档位括注属于名字本身，保留参与匹配
- 折算武力 = round(II ÷ 榜首II × 100)
"""
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
MAPPING = os.path.join(ROOT, "mapping")

# 推理档位词：括注里只由这些词组成时视为档位后缀，聚合时剔除
EFFORT_WORDS = {"max", "xhigh", "high", "medium", "low", "with", "fallback", "default"}
EFFORT_RANK = {"max": 5, "xhigh": 4, "high": 3, "medium": 2, "low": 1}

# 代表厂商/平台/生态而非具体模型的席位（主公位由 role 判定，此处只列
# 非主公的公司/机构位），不参与联结，数值留空
NON_MODEL_MARKS = ("生态", "虚位")
NON_MODEL_NAMES = {"Microsoft", "NVIDIA", "FTC/反垄断", "ElevenLabs"}

# 天子不列武臣册：三国志14不收录皇帝，漢獻帝无游戏五维是有意为之
NON_OFFICER_NAMES = {"漢獻帝"}


def _is_effort_token(tok):
    words = tok.lower().split()
    if not words:
        return False
    # 纯档位词（max/xhigh/…/with fallback/default fallback）
    if all(w in EFFORT_WORDS for w in words):
        return True
    # 回退目标限定（如 "Opus 4.8 Fallback"）
    return words[-1] == "fallback" and len(words) > 1


def canonical_name(name):
    """去掉括注中的推理档位词，其余括注（版本日期/特供版/变体）保留。"""
    def clean(m):
        tokens = [t.strip() for t in m.group(1).split(",")]
        kept = [t for t in tokens if not _is_effort_token(t)]
        return "(" + ", ".join(kept) + ")" if kept else ""
    return re.sub(r"\(([^()]*)\)", clean, name).strip()


def effort_rank(name):
    rank = 0
    for group in re.findall(r"\(([^()]*)\)", name):
        for tok in group.split(","):
            for word in tok.strip().lower().split():
                rank = max(rank, EFFORT_RANK.get(word, 0))
    return rank


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
    index = {}
    for r in rows:
        ii = fnum(r["intelligence_index"])
        rec = {
            "model": r["model"], "creator": r["creator"], "ii": ii,
            "derived_warfare": round(ii / top_ii * 100) if ii else "",
            "cost": fnum(r["cost_per_task_usd"]),
            "speed": fnum(r["median_tokens_per_s"]),
        }
        key = canonical_name(r["model"])
        best = index.get(key)
        # 同基名多档位时取 II 最高者（并列时取档位更高者）
        if best is None or ((rec["ii"] or -1), effort_rank(r["model"])) > \
                ((best["ii"] or -1), effort_rank(best["model"])):
            index[key] = rec
    return index, os.path.basename(path), top_ii


def is_non_model(name):
    return name in NON_MODEL_NAMES or any(m in name for m in NON_MODEL_MARKS)


def main():
    officers = load_officers()
    index, snapshot, top_ii = load_models()
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
        m = None
        if r["model"] and r["role"] != "主公" and not is_non_model(r["model"]):
            m = index.get(canonical_name(r["model"]))
            if not m and r["role"] != "彩蛋":
                missing_model.append(r["model"])
        if not g and r["general"] not in NON_OFFICER_NAMES:
            missing_officer.append(r["general"])
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

    dst = os.path.join(MAPPING, "mapping_v0.5.csv")
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(out_rows)

    print(f"snapshot: {snapshot} (top II = {top_ii})")
    print(f"rows written: {len(out_rows)} -> {os.path.relpath(dst, ROOT)}")
    if missing_officer:
        print("!! officers not found in sanguo14 data:", missing_officer)
    if missing_model:
        print("!! models not matched in AA snapshot (retired/named differently):")
        for m in missing_model:
            print("   -", m)


if __name__ == "__main__":
    main()
