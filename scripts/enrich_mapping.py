#!/usr/bin/env python3
"""联结 mapping_source.csv 与两份史源数据，生成 mapping_v0.8.csv。

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
- 折算统率 = round(统率基准 ÷ 统率榜首 × 100)，统率基准 = analystAgent/apexAgents/
  itbenchSre/gdpval 四项 agentic 子分中非空项的均值（0-100）
- 折算智力 = round((1 − 成本百分位) × 100)，成本百分位取全库有成本模型的排名
  （越便宜越有计）
- 折算政治 = round(政治基准 ÷ 政治榜首 × 100)，政治基准 = ifbench（指令遵循）与
  omniscienceNonHallucination（不幻觉率）两项非空项的均值——听指令、不整活
- 折算魅力 = round(调用量份额 ÷ 榜首份额 × 100)，调用量取 OpenRouter
  rankings/models 端点全期 rankingMetricValue（data/openrouter_rankings_*.json，
  scripts/fetch_openrouter.py 抓取）；slug 三级匹配：去日期精确 → 前缀(≥6字符) →
  少量人工别名（命名词序/架构后缀差异）
"""
import bisect
import csv
import glob
import json
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
    costs = sorted(c for c in (fnum(r["cost_per_task_usd"]) for r in rows) if c is not None)

    def agentic(r):
        vals = [fnum(r[k]) for k in
                ("analyst_agent", "apex_agents", "itbench_sre", "gdpval")]
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals)) if vals else None

    def politics(r):
        # 政治基准 = 指令遵循(ifbench)与不幻觉率(nonhallucination)非空项均值
        vals = [fnum(r[k]) for k in ("ifbench", "nonhallucination")]
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals)) if vals else None

    index = {}
    for r in rows:
        ii = fnum(r["intelligence_index"])
        rec = {
            "model": r["model"], "creator": r["creator"], "ii": ii,
            "derived_warfare": round(ii / top_ii * 100) if ii else "",
            "cost": fnum(r["cost_per_task_usd"]),
            "speed": fnum(r["median_tokens_per_s"]),
            "leadership": agentic(r),
            "politics": politics(r),
        }
        key = canonical_name(r["model"])
        best = index.get(key)
        # 同基名多档位时取 II 最高者（并列时取档位更高者）
        if best is None or ((rec["ii"] or -1), effort_rank(r["model"])) > \
                ((best["ii"] or -1), effort_rank(best["model"])):
            index[key] = rec
    top_leadership = max((rec["leadership"] or 0) for rec in index.values()) or None
    top_politics = max((rec["politics"] or 0) for rec in index.values()) or None
    return index, os.path.basename(path), top_ii, top_leadership, top_politics, costs


# OpenRouter slug → AA 名的人工别名（词序/命名差异，匹配前先 norm）
OR_ALIAS = {
    "claude5fable": "claude-fable-5",
    "mistrallarge40": "mistral-large-4-preview",
}


def norm_slug(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load_charm():
    """读最新 OpenRouter 榜，返回 canonical名 → 魅力(0-100) 与榜首份额。"""
    import glob as _g
    paths = sorted(_g.glob(os.path.join(DATA, "openrouter_rankings_*.json")))
    if not paths:
        return {}, None
    blob = json.load(open(paths[-1], encoding="utf-8"))["models"]

    def strip_date(slug):
        m = re.match(r"^[a-z0-9.-]+/(.+)$", slug)
        name = m.group(1) if m else slug
        name = re.sub(r"-(\d{4}-?\d{2}-?\d{2})$", "", name)
        name = re.sub(r"-\d{8,}$", "", name)
        return name

    normed = {}
    for slug, v in blob.items():
        k = norm_slug(strip_date(slug))
        normed[k] = max(normed.get(k, 0), v)
    top = max(normed.values()) or None

    charm = {}
    for k, v in normed.items():
        charm[k] = round(v / top * 100)
    return charm, top


def is_non_model(name):
    return name in NON_MODEL_NAMES or any(m in name for m in NON_MODEL_MARKS)


def main():
    officers = load_officers()
    index, snapshot, top_ii, top_leadership, top_politics, costs = load_models()
    charm, charm_top = load_charm()

    def charm_for(model_name):
        """三级匹配：canonical 精确 → 前缀 → 别名。"""
        if not charm or charm_top is None:
            return ""
        cn = norm_slug(model_name)
        if cn in charm:
            return charm[cn]
        for k, v in charm.items():
            if len(cn) >= 6 and (k.startswith(cn) or cn.startswith(k)):
                return v
        alias = OR_ALIAS.get(cn)
        if alias:
            a = norm_slug(alias)
            if a in charm:
                return charm[a]
        return ""
    src = os.path.join(MAPPING, "mapping_source.csv")
    with open(src, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    header = [
        "role", "faction", "general", "model", "creator", "aa_ii",
        "derived_warfare", "derived_leadership", "derived_intellect",
        "derived_charm", "derived_politics",
        "cost_per_task_usd", "median_tokens_per_s",
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
            "derived_leadership": (
                round(m["leadership"] / top_leadership * 100)
                if m and m.get("leadership") and top_leadership else ""),
            "derived_intellect": (
                round((1 - bisect.bisect_left(costs, m["cost"]) / (len(costs) - 1)) * 100)
                if m and m.get("cost") is not None and len(costs) > 1 else ""),
            "derived_charm": charm_for(r["model"]) if r["model"] else "",
            "derived_politics": (
                round(m["politics"] / top_politics * 100)
                if m and m.get("politics") and top_politics else ""),
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

    dst = os.path.join(MAPPING, "mapping_v0.8.csv")
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
