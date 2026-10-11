#!/usr/bin/env python3
"""从 mapping/mapping_v0.5.csv + 两份史源生成美漫风展示站 docs/index.html。

- 纯静态单页：数据内嵌为 JS 常量，无前端构建依赖，可直接挂 GitHub Pages
- 详情层：KOEI 立绘（docs/portraits/，nobuwiki 采集；无页面者用美漫姓氏头像）、
  游戏五维雷达 × 模型六维基准雷达（快照子分）、两朝列传（游戏生平字段 + 模型典故）
- 改完映射后重跑：python3 scripts/enrich_mapping.py && python3 scripts/build_site.py
"""
import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FACTION_META = [
    ("汉献帝朝廷", "#8d6e63", "天下与舞台 —— 基础设施与监管的暗流"),
    ("曹魏", "#1d3557", "美国闭源阵营 —— 曹操=OpenAI 为宗，Google/xAI 客将"),
    ("蜀汉", "#c1121f", "中国大模型阵营 —— 刘备=幻方量化（DeepSeek 生态）"),
    ("东吴", "#2a9d8f", "开源联盟 —— 孙权=Meta、鲁肃=HuggingFace 双主公"),
    ("群雄", "#6a4c93", "厂家诸侯会盟 —— 袁绍=Anthropic 领衔，多主公制"),
]
ANCHORS = {"呂布", "文聘", "文醜", "曹彰", "高順", "曹性", "荀彧", "顧雍"}

EFFORT_WORDS = {"max", "xhigh", "high", "medium", "low", "with", "fallback", "default"}


def _is_effort_token(tok):
    words = tok.lower().split()
    if not words:
        return False
    if all(w in EFFORT_WORDS for w in words):
        return True
    return words[-1] == "fallback" and len(words) > 1


def canonical_name(name):
    def clean(m):
        tokens = [t.strip() for t in m.group(1).split(",")]
        kept = [t for t in tokens if not _is_effort_token(t)]
        return "(" + ", ".join(kept) + ")" if kept else ""
    return re.sub(r"\(([^()]*)\)", clean, name).strip()


def load_officers():
    path = os.path.join(ROOT, "data", "sanguo14_officers.csv")
    with open(path, encoding="utf-8") as f:
        return {r["name"]: r for r in csv.DictReader(f)}


def load_snapshot_best():
    """快照按 canonical 名取 II 最高的行（与 enrich 同规则），供雷达取子分。"""
    path = os.path.join(ROOT, "data", "aa_models_snapshot_2026-10-10.csv")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    def fnum(s):
        s = (s or "").replace("*", "").replace("$", "")
        try:
            return float(s)
        except ValueError:
            return -1

    best = {}
    for r in rows:
        key = canonical_name(r["model"])
        if key not in best or fnum(r["intelligence_index"]) > fnum(best[key]["intelligence_index"]):
            best[key] = r
    return best


def game_bio(o):
    """三国侧列传：由游戏字段织成短传。"""
    if not o:
        return "天子不列武臣册——《三国志14》不收录帝王之数，其五维为史书阙载。"
    parts = []
    years = []
    if o.get("debut_year"):
        years.append(f"登场于{int(float(o['debut_year']))}年")
    if o.get("death_year"):
        years.append(f"卒于{int(float(o['death_year']))}年")
    if years:
        parts.append("，".join(years))
    if o.get("affiliation"):
        parts.append(f"登场势力「{o['affiliation']}」")
    if o.get("doctrine"):
        parts.append(f"主义「{o['doctrine']}」" + (f"，政策「{o['policy']}」(Lv{o['policy_lv']})" if o.get("policy") else ""))
    kin = []
    for label, key in [("父", "father"), ("母", "mother"), ("配偶", "spouse"), ("义兄弟", "sworn_brother")]:
        if o.get(key):
            kin.append(f"{label}{o[key]}")
    if kin:
        parts.append("亲族：" + "、".join(kin))
    parts.append(f"原版五维 统{o['leadership']}/武{o['warfare']}/智{o['intellect']}/政{o['politics']}/魅{o['charm']}，合计{o['total']}")
    return "；".join(parts) + "。"


def load_data():
    officers = load_officers()
    best = load_snapshot_best()
    path = os.path.join(ROOT, "mapping", "mapping_v0.5.csv")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    data = []
    for r in rows:
        o = officers.get(r["general"])
        snap = best.get(canonical_name(r["model"]))

        def sub(key):
            v = (snap or {}).get(key)
            return int(float(v)) if v and v != "--" else None

        portrait = None
        p = os.path.join(ROOT, "docs", "portraits", f"{r['general']}.jpg")
        if os.path.exists(p):
            portrait = f"portraits/{r['general']}.jpg"

        data.append({
            "role": r["role"], "faction": r["faction"], "general": r["general"],
            "model": r["model"], "creator": r["creator"],
            "ii": r["aa_ii"], "dw": r["derived_warfare"],
            "cost": r["cost_per_task_usd"], "speed": r["median_tokens_per_s"],
            "war": r["game_warfare"], "total": r["game_total"],
            "note": r["note"], "anchor": r["general"] in ANCHORS,
            "portrait": portrait,
            "bio": game_bio(o),
            "g": [o["leadership"], o["warfare"], o["intellect"], o["politics"], o["charm"]] if o else None,
            "r6": {"hle": sub("hle"), "gpqa": sub("gpqa"), "scicode": sub("scicode"),
                   "mmmu": sub("mmmu_pro"), "tb": sub("terminalbench40"), "omni": sub("omniscience")},
        })
    return data


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大模型三国志 —— LLM SANGUO CHRONICLES</title>
<meta name="description" content="把 Artificial Analysis 模型评测和《三国志14》武将五维对照排座。武力 = 智能指数折算，智力 = 性价比。演义版 102 席，Claude Opus 5.5 对吕布（100:100）。">
<meta property="og:type" content="website">
<meta property="og:site_name" content="大模型三国志">
<meta property="og:title" content="大模型三国志 —— LLM Sanguo Chronicles">
<meta property="og:description" content="把 Artificial Analysis 模型评测和《三国志14》武将五维对照排座。武力 = 智能指数折算，智力 = 性价比。演义版 102 席，Claude Opus 5.5 对吕布（100:100）。">
<meta property="og:url" content="https://illegalcreed.github.io/llm-sanguo/">
<meta property="og:image" content="https://illegalcreed.github.io/llm-sanguo/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="大模型三国志 —— LLM Sanguo Chronicles">
<meta name="twitter:description" content="把 Artificial Analysis 模型评测和《三国志14》武将五维对照排座。武力 = 智能指数折算，智力 = 性价比。演义版 102 席。">
<meta name="twitter:image" content="https://illegalcreed.github.io/llm-sanguo/assets/og.png">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=ZCOOL+KuaiLe&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#141414; --paper:#f6ecd9; --cream:#fffaf0;
  --red:#d62828; --yellow:#ffb703; --blue:#1d3557; --teal:#2a9d8f; --purple:#6a4c93; --brown:#8d6e63;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'ZCOOL KuaiLe','PingFang SC','Microsoft YaHei',sans-serif;background:var(--paper);color:var(--ink);overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:radial-gradient(circle, rgba(20,20,20,.10) 1.2px, transparent 1.6px);background-size:9px 9px}
.bangers{font-family:'Bangers',cursive}
.wrap{position:relative;z-index:1;max-width:1280px;margin:0 auto;padding:24px 20px 80px}

.masthead{position:relative;text-align:center;padding:34px 10px 26px;border:5px solid var(--ink);background:var(--cream);
  box-shadow:10px 10px 0 var(--ink);margin-bottom:18px;overflow:hidden}
.masthead::after{content:'';position:absolute;inset:0;
  background:linear-gradient(115deg, transparent 49.6%, rgba(20,20,20,.05) 50%, transparent 50.4%)}
.topstrip{display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;font-size:13px;letter-spacing:2px;
  border-bottom:3px solid var(--ink);padding:0 90px 8px;margin-bottom:14px}
.topstrip .bangers{font-size:15px}
h1{font-size:clamp(44px,8vw,92px);line-height:.95;letter-spacing:6px;text-shadow:5px 5px 0 var(--yellow), 10px 10px 0 rgba(20,20,20,.18)}
h1 span{color:var(--red); -webkit-text-stroke:2px var(--ink)}
.subtitle{margin-top:10px;font-size:clamp(15px,2.4vw,22px);letter-spacing:4px}
.subtitle b{background:var(--ink);color:var(--yellow);padding:2px 10px;margin:0 6px}
.burst{position:absolute;display:flex;align-items:center;justify-content:center;text-align:center;background:var(--red);color:#fff;
  transform:rotate(-12deg);
  clip-path:polygon(50% 0%,61% 12%,75% 5%,79% 20%,95% 18%,90% 33%,100% 44%,88% 52%,95% 66%,79% 66%,77% 82%,63% 74%,50% 88%,37% 74%,23% 82%,21% 66%,5% 66%,12% 52%,0% 44%,10% 33%,5% 18%,21% 20%,25% 5%,39% 12%);
  font-size:15px;width:110px;height:110px;line-height:.9}
.burst b{font-family:'Bangers',cursive;font-size:26px;transform:rotate(6deg);text-shadow:2px 2px 0 rgba(0,0,0,.35)}
.burst.b1{top:-30px;left:-30px;background:var(--red)}
.burst.b2{bottom:-28px;right:-26px;background:var(--blue);transform:rotate(10deg)}
.statline{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin:22px 90px 6px}
.statline .chip{border:3px solid var(--ink);background:#fff;padding:6px 14px;font-size:15px;box-shadow:4px 4px 0 var(--ink);letter-spacing:1px}
.statline .chip b{font-family:'Bangers',cursive;font-size:20px;margin-right:6px;color:var(--red)}

.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;border:4px solid var(--ink);
  background:var(--yellow);box-shadow:7px 7px 0 var(--ink);padding:12px 14px;margin:26px 0 30px;position:sticky;top:10px;z-index:50}
.tabs{display:flex;flex-wrap:wrap;gap:8px}
.tab{cursor:pointer;border:3px solid var(--ink);background:#fff;padding:7px 14px;font-size:16px;letter-spacing:2px;user-select:none;transition:transform .12s;position:relative;font-family:inherit}
.tab:hover{transform:translate(-2px,-2px);box-shadow:4px 4px 0 var(--ink)}
.tab.on{background:var(--ink);color:var(--yellow);box-shadow:4px 4px 0 rgba(20,20,20,.3)}
.tab .dot{display:inline-block;width:12px;height:12px;border:2px solid var(--ink);border-radius:50%;margin-right:6px;vertical-align:-1px}
.tab.on .dot{border-color:var(--yellow)}
.tools-right{display:flex;gap:8px;align-items:center}
.search{border:3px solid var(--ink);padding:7px 12px;font-size:15px;font-family:inherit;background:#fff;min-width:180px;outline:none}
.search:focus{box-shadow:4px 4px 0 var(--ink)}
.sortbtn{cursor:pointer;border:3px solid var(--ink);background:#fff;padding:7px 12px;font-size:15px;font-family:inherit;letter-spacing:1px}
.sortbtn:hover{box-shadow:4px 4px 0 var(--ink)}
.factionhead{display:none;margin:34px 0 14px;border:4px solid var(--ink);padding:10px 16px;background:var(--cream);
  box-shadow:6px 6px 0 var(--ink);align-items:baseline;gap:14px;flex-wrap:wrap}
.factionhead.show{display:flex}
.factionhead h2{font-size:26px;letter-spacing:3px}
.factionhead p{font-size:15px;opacity:.85}
.factionhead .stamp{margin-left:auto;font-family:'Bangers',cursive;font-size:14px;letter-spacing:1px;border:3px solid var(--ink);padding:3px 10px;transform:rotate(-2deg);background:#fff}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(315px,1fr));gap:26px;margin-top:8px}
.panel{position:relative;border:4px solid var(--ink);background:var(--cream);box-shadow:9px 9px 0 var(--ink);
  padding:16px 16px 14px;transition:transform .15s,box-shadow .15s;display:flex;flex-direction:column;gap:10px;cursor:pointer}
.panel:nth-child(4n+1){transform:rotate(-.5deg)} .panel:nth-child(4n+3){transform:rotate(.5deg)}
.panel:hover{transform:translate(-4px,-4px) rotate(0deg)!important;box-shadow:14px 14px 0 var(--ink);z-index:5}
.panel .fbar{position:absolute;top:0;left:0;right:0;height:8px}
.phead{display:flex;align-items:flex-start;gap:10px;margin-top:6px}
.gname{font-size:30px;letter-spacing:3px;line-height:1.05;flex:1}
.gname small{display:block;font-size:13px;letter-spacing:2px;opacity:.65;margin-top:3px}
.badge{flex-shrink:0;border:3px solid var(--ink);font-size:13px;padding:3px 9px;letter-spacing:2px;background:#fff;transform:rotate(3deg);font-family:inherit}
.badge.主公{background:var(--yellow)} .badge.诸侯{background:#e0aaff} .badge.彩蛋{background:#ffd6e0}
.badge.暗线{background:var(--ink);color:#fff} .badge.武将{background:#fff}
.anchorstar{position:absolute;top:-16px;right:-14px;width:44px;height:44px;background:var(--red);color:#fff;display:flex;align-items:center;justify-content:center;transform:rotate(12deg);font-size:22px;
  clip-path:polygon(50% 0%,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%)}
.mrow{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.mchip{border:3px solid var(--ink);background:#fff;padding:4px 10px;font-size:15px;letter-spacing:1px;font-family:'Courier New',monospace;font-weight:bold;box-shadow:3px 3px 0 rgba(20,20,20,.25)}
.cchip{border:2px solid var(--ink);padding:3px 9px;font-size:13px;background:#eee;letter-spacing:1px}
.dead{font-size:13px;color:#7a5c3e;letter-spacing:1px}
.duel{border:3px solid var(--ink);background:#fff;padding:9px 10px 7px}
.duel .dtitle{font-size:13px;letter-spacing:2px;margin-bottom:7px;display:flex;justify-content:space-between}
.duel .dtitle b{font-family:'Bangers',cursive;font-size:15px;color:var(--red);letter-spacing:1px}
.brow{display:grid;grid-template-columns:52px 1fr 34px;gap:8px;align-items:center;font-size:13px;margin-bottom:5px}
.brow:last-child{margin-bottom:0}
.brow .lab{letter-spacing:2px;opacity:.8}
.btrack{height:16px;border:2px solid var(--ink);background:repeating-linear-gradient(45deg,#f2f2f2,#f2f2f2 6px,#e6e6e6 6px,#e6e6e6 12px);position:relative}
.bfill{position:absolute;top:0;left:0;bottom:0}
.bfill.game{background:var(--red)} .bfill.model{background:var(--ink)}
.brow .val{font-family:'Bangers',cursive;font-size:18px;text-align:right}
.meta{display:flex;flex-wrap:wrap;gap:6px}
.meta span{border:2px solid var(--ink);background:#fff;font-size:12.5px;padding:3px 8px;letter-spacing:1px}
.meta span b{font-family:'Bangers',cursive;font-size:14px}
.caption{position:relative;border:3px solid var(--ink);background:var(--yellow);padding:10px 12px 9px;font-size:15px;line-height:1.55;letter-spacing:.5px;box-shadow:4px 4px 0 rgba(20,20,20,.35)}
.caption::before{content:'★ 列传';position:absolute;top:-13px;left:10px;background:var(--ink);color:#fff;font-size:12px;padding:2px 10px;letter-spacing:3px}
.viewhint{align-self:center;font-size:12px;letter-spacing:2px;opacity:.55;border-top:2px dashed rgba(20,20,20,.3);padding-top:6px}
.footer{margin-top:60px;text-align:center;font-size:14px;letter-spacing:2px;line-height:2}
.footer .bangers{font-size:22px;color:var(--red)}
.empty{display:none;text-align:center;font-size:22px;letter-spacing:4px;padding:60px 0;border:4px dashed var(--ink);margin-top:20px}
@media (max-width:640px){
  .burst{display:none}
  .toolbar{position:static}
  .topstrip{padding-left:10px;padding-right:10px}
  .statline{margin-left:0;margin-right:0}
  .tools-right{width:100%}
  .search{min-width:0;flex:1;width:0}
}

/* ===== 详情层 ===== */
#overlay{display:none;position:fixed;inset:0;z-index:100;overflow-y:auto;background:rgba(20,20,20,.55);padding:26px 14px}
#overlay.open{display:block}
.sheet{position:relative;max-width:1080px;margin:0 auto;background:var(--paper);border:5px solid var(--ink);box-shadow:14px 14px 0 rgba(0,0,0,.45);padding:26px 26px 30px}
.sheet::before{content:'';position:absolute;inset:0;pointer-events:none;
  background-image:radial-gradient(circle, rgba(20,20,20,.07) 1.2px, transparent 1.6px);background-size:9px 9px}
.dhead{display:flex;gap:22px;flex-wrap:wrap;position:relative;z-index:1}
.dportrait{width:180px;flex-shrink:0}
.dportrait img{width:180px;height:auto;display:block;border:4px solid var(--ink);box-shadow:6px 6px 0 var(--ink);background:#fff}
.avatar-burst{width:180px;height:216px;display:flex;align-items:center;justify-content:center;position:relative;
  border:4px solid var(--ink);box-shadow:6px 6px 0 var(--ink);background:var(--yellow)}
.avatar-burst .bigchar{font-size:96px;letter-spacing:0;text-shadow:4px 4px 0 rgba(20,20,20,.2);z-index:2;transform:rotate(-6deg)}
.avatar-burst .starbg{position:absolute;inset:8px;
  clip-path:polygon(50% 0%,61% 12%,75% 5%,79% 20%,95% 18%,90% 33%,100% 44%,88% 52%,95% 66%,79% 66%,77% 82%,63% 74%,50% 88%,37% 74%,23% 82%,21% 66%,5% 66%,12% 52%,0% 44%,10% 33%,5% 18%,21% 20%,25% 5%,39% 12%)}
.dtitle{flex:1;min-width:260px}
.dtitle .fac{font-size:15px;letter-spacing:3px;opacity:.75}
.dtitle h2{font-size:clamp(40px,6vw,64px);letter-spacing:6px;line-height:1;margin:2px 0 8px}
.dtitle .badges{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.dchips{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.dstats{display:flex;gap:8px;flex-wrap:wrap}
.dstats span{border:3px solid var(--ink);background:#fff;padding:5px 12px;font-size:14px;letter-spacing:1px;box-shadow:3px 3px 0 rgba(20,20,20,.25)}
.dstats span b{font-family:'Bangers',cursive;font-size:17px;margin:0 3px;color:var(--red)}
.dclose{position:absolute;top:-18px;right:-16px;width:52px;height:52px;background:var(--red);color:#fff;border:4px solid var(--ink);font-size:22px;cursor:pointer;z-index:3;display:flex;align-items:center;justify-content:center;font-family:'Bangers',cursive;
  clip-path:polygon(50% 0%,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%)}
.dclose:hover{transform:scale(1.1) rotate(8deg)}
.duelsection{display:flex;gap:22px;flex-wrap:wrap;margin:24px 0 8px;position:relative;z-index:1}
.radarbox{flex:1;min-width:300px;border:4px solid var(--ink);background:radial-gradient(circle, rgba(20,20,20,.08) 1.2px, transparent 1.7px) 0 0/9px 9px, var(--cream);box-shadow:7px 7px 0 var(--ink);padding:12px 12px 6px;text-align:center}
.radarbox h3{font-size:17px;letter-spacing:3px;margin-bottom:4px}
.radarbox .sub{font-size:12px;letter-spacing:2px;opacity:.6;margin-bottom:6px}
.bios{display:flex;gap:22px;flex-wrap:wrap;margin-top:20px;position:relative;z-index:1}
.bio{flex:1;min-width:300px;border:4px solid var(--ink);padding:14px 14px 12px;box-shadow:7px 7px 0 rgba(20,20,20,.3);font-size:15.5px;line-height:1.75;letter-spacing:.5px}
.bio.san{background:var(--cream)}
.bio.llm{background:var(--yellow)}
.bio h3{font-size:17px;letter-spacing:3px;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.bio h3 .tag{font-size:11px;letter-spacing:2px;background:var(--ink);color:#fff;padding:2px 8px}
.dnav{display:flex;justify-content:space-between;gap:10px;margin-top:22px;position:relative;z-index:1}
.dnav button{font-family:inherit;cursor:pointer;border:4px solid var(--ink);background:#fff;padding:9px 18px;font-size:16px;letter-spacing:2px;box-shadow:5px 5px 0 var(--ink)}
.dnav button:hover{transform:translate(-2px,-2px)}
.dnav .pos{font-family:'Bangers',cursive;font-size:20px;align-self:center;letter-spacing:2px}
</style>
</head>
<body>
<div class="wrap">

  <header class="masthead">
    <div class="burst b1"><b>POW!</b></div>
    <div class="burst b2"><b>102<br>将</b></div>
    <div class="topstrip">
      <span>★ ARTIFICIAL ANALYSIS 快照 2026-10-10</span>
      <span class="bangers">LLM SANGUO CHRONICLES · VOL.5</span>
      <span>三国志14 全武将数值 ★ 697 模型全库 ★</span>
    </div>
    <h1>大模型<span>三国志</span></h1>
    <div class="subtitle">给大模型<b>立传</b>排座的开源对照实验 —— 武力 = 智能指数<b>折算</b>，主公 = <b>厂家</b>，模型皆为武将</div>
    <div class="statline">
      <span class="chip"><b>102</b>武将席位</span>
      <span class="chip"><b>15</b>主公厂家</span>
      <span class="chip"><b>8</b>数值锚点</span>
      <span class="chip"><b>76</b>席有评测数据</span>
      <span class="chip"><b>697</b>模型全库快照</span>
    </div>
  </header>

  <div class="toolbar">
    <div class="tabs" id="tabs"></div>
    <div class="tools-right">
      <input class="search" id="q" placeholder="搜武将 / 模型 / 厂商…">
      <button class="sortbtn" id="sortbtn">⚔ 按折算武力排序</button>
    </div>
  </div>

  <div class="factionhead" id="factionhead">
    <h2 id="fh-name"></h2><p id="fh-desc"></p><span class="stamp" id="fh-count"></span>
  </div>

  <div class="grid" id="grid"></div>
  <div class="empty" id="empty">查无此人 —— 史书阙载！</div>

  <footer class="footer">
    <div class="bangers">— THE END? NOT YET! —</div>
    数据：三国志14 威力加强版（Nobuwiki 整理）× Artificial Analysis（2026-10-10 快照）<br>
    立绘采自 Nobuwiki（© KOEI TECMO），无页面者以本站手绘风头像代之 · 方法论与完整数据见仓库 docs/<br>
    <span style="opacity:.6">MIT 只覆盖代码。三国志数值与立绘 © KOEI TECMO（整理自 Nobuwiki）· 评测 © Artificial Analysis · 权利人请到仓库开 issue 要求下架</span>
  </footer>
</div>

<div id="overlay"><div class="sheet" id="sheet"></div></div>

<script>
const FACTIONS = __FACTIONS__;
const DATA = __DATA__;

const tabsEl=document.getElementById('tabs'), grid=document.getElementById('grid'),
      qEl=document.getElementById('q'), sortEl=document.getElementById('sortbtn'),
      fhEl=document.getElementById('factionhead'), emptyEl=document.getElementById('empty'),
      overlayEl=document.getElementById('overlay'), sheetEl=document.getElementById('sheet');
let faction='全部', sortMode='faction', keyword='', curList=[], curIdx=-1;

const factionOrder = Object.fromEntries(FACTIONS.map((f,i)=>[f[0],i]));
const roleOrder={'主公':0,'暗线':1,'诸侯':2,'武将':3,'彩蛋':4};
const ROLES={'主公':'主公','诸侯':'诸侯','武将':'武将','彩蛋':'彩蛋','暗线':'暗线'};

function tabHTML(){
  const all=[['全部',null],...FACTIONS.map(f=>[f[0],f[1]])];
  tabsEl.innerHTML=all.map(([name,color])=>{
    const dot=color?`<span class="dot" style="background:${color}"></span>`:'<span class="dot" style="background:conic-gradient(#8d6e63,#1d3557,#c1121f,#2a9d8f,#6a4c93)"></span>';
    return `<button class="tab ${faction===name?'on':''}" data-f="${name}">${dot}${name}</button>`;
  }).join('');
  tabsEl.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{faction=t.dataset.f;render();});
}

function bars(d){
  const game=parseInt(d.war||0), model=parseInt(d.dw||0);
  if(!game&&!model&&!d.total) return '';
  const gp=game?Math.min(100,game):0, mp=model?Math.min(100,model):0;
  return `<div class="duel">
    <div class="dtitle"><span>单挑实力条</span><b>VS</b></div>
    <div class="brow"><span class="lab">原版武力</span><div class="btrack"><div class="bfill game" style="width:${gp}%"></div></div><span class="val">${game||'—'}</span></div>
    <div class="brow"><span class="lab">折算武力</span><div class="btrack"><div class="bfill model" style="width:${mp}%"></div></div><span class="val">${model||'—'}</span></div>
  </div>`;
}

function meta(d){
  const m=[];
  if(d.ii) m.push(`<span>II <b>${d.ii}</b></span>`);
  if(d.cost) m.push(`<span><b>$${d.cost}</b>/任务</span>`);
  if(d.speed) m.push(`<span><b>${d.speed}</b> t/s</span>`);
  if(d.total) m.push(`<span>五维合计 <b>${d.total}</b></span>`);
  if(!d.ii && d.role!=='主公') m.push(`<span>💀 史书阙载</span>`);
  return m.length?`<div class="meta">${m.join('')}</div>`:'';
}

function card(d, i){
  const f=FACTIONS.find(x=>x[0]===d.faction)||['','#666',''];
  const anchor=d.anchor?'<div class="anchorstar">★</div>':'';
  const creator=d.creator?`<span class="cchip">${d.creator}</span>`:'';
  const dead=(!d.ii&&d.role!=='主公')?'<span class="dead">（已退场）</span>':'';
  return `<article class="panel" data-i="${i}">
    <div class="fbar" style="background:${f[1]}"></div>${anchor}
    <div class="phead">
      <div class="gname">${d.general}<small>${d.faction} · ${ROLES[d.role]||d.role}</small></div>
      <span class="badge ${d.role}">${ROLES[d.role]||d.role}</span>
    </div>
    <div class="mrow"><span class="mchip">${d.model}</span>${creator}${dead}</div>
    ${bars(d)}${meta(d)}
    <div class="caption">${d.note}</div>
    <div class="viewhint">▸ 点击展开详情：立绘 · 双雷达 · 两朝列传</div>
  </article>`;
}

function filtered(){
  let list=DATA.map((d,i)=>({d,i})).filter(({d})=>{
    if(faction!=='全部'&&d.faction!==faction) return false;
    if(keyword){
      const k=keyword.toLowerCase();
      if(!(d.general.toLowerCase().includes(k)||d.model.toLowerCase().includes(k)
        ||(d.creator||'').toLowerCase().includes(k)||d.note.toLowerCase().includes(k))) return false;
    }
    return true;
  });
  if(sortMode==='power'){
    list.sort((a,b)=>(parseInt(b.d.dw||0)-parseInt(a.d.dw||0))||(parseInt(b.d.war||0)-parseInt(a.d.war||0)));
  }else{
    list.sort((a,b)=>(factionOrder[a.d.faction]-factionOrder[b.d.faction])
      ||(roleOrder[a.d.role]-roleOrder[b.d.role])
      ||(parseInt(b.d.dw||0)-parseInt(a.d.dw||0)));
  }
  return list;
}

function render(){
  tabHTML();
  curList=filtered();
  grid.innerHTML=curList.map(({d,i})=>card(d,i)).join('');
  grid.querySelectorAll('.panel').forEach(p=>p.onclick=()=>openDetail(parseInt(p.dataset.i)));
  const f=FACTIONS.find(x=>x[0]===faction);
  if(f){ fhEl.classList.add('show');
    document.getElementById('fh-name').textContent='【'+f[0]+'】';
    document.getElementById('fh-name').style.color=f[1];
    document.getElementById('fh-desc').textContent=f[2];
    document.getElementById('fh-count').textContent=curList.length+' SEATS';
  } else fhEl.classList.remove('show');
  emptyEl.style.display=curList.length?'none':'block';
}

/* ===== SVG 雷达（美漫版：网点填充/手绘抖线/硬阴影/MAX爆炸章） ===== */
let RADAR_SEQ=0;
function radarSVG(axes, color, sub){
  const uid='r'+(++RADAR_SEQ);
  const n=axes.length, cx=180, cy=140, R=105;
  const pt=(k,r)=>{const a=-Math.PI/2+k*2*Math.PI/n;return [cx+r*Math.cos(a),cy+r*Math.sin(a)];};
  const P=(k,r)=>pt(k,r).map(v=>v.toFixed(1)).join(',');
  let s=`<svg viewBox="0 0 360 300" style="width:100%;max-width:380px">`;
  s+=`<defs>
    <pattern id="dots-${uid}" width="7.5" height="7.5" patternUnits="userSpaceOnUse" patternTransform="rotate(8)">
      <circle cx="2.2" cy="2.2" r="1.7" fill="${color}" opacity=".5"/></pattern>
    <filter id="rough-${uid}" x="-8%" y="-8%" width="116%" height="116%">
      <feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="2" seed="${RADAR_SEQ*13+3}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="3.2"/></filter>
    <filter id="rough2-${uid}" x="-8%" y="-8%" width="116%" height="116%">
      <feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves="1" seed="${RADAR_SEQ*7+5}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="2.2"/></filter>
  </defs>`;
  // 网格环 + 轴线（手绘抖动）
  s+=`<g filter="url(#rough-${uid})">`;
  for(let ring=1;ring<=5;ring++){
    const r=R*ring/5;
    const pts=axes.map((_,k)=>P(k,r)).join(' ');
    s+=`<polygon points="${pts}" fill="none" stroke="#141414" stroke-width="${ring===5?3.4:1.6}" opacity="${ring===5?.95:.3}" stroke-linejoin="round"/>`;
  }
  axes.forEach((ax,k)=>{
    const [x,y]=pt(k,R);
    s+=`<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#141414" stroke-width="1.6" opacity=".3"/>`;
  });
  s+=`</g>`;
  const poly=axes.map((ax,k)=>{
    const v=ax.val==null?0:Math.max(0,Math.min(100,ax.val))/100*R;
    return pt(k,v);
  });
  const polyStr=poly.map(p=>p.map(v=>v.toFixed(1)).join(',')).join(' ');
  // 数据多边形：黑色硬阴影错位 + 浅底色 + 网点填充 + 粗描边（抖动）
  s+=`<g filter="url(#rough2-${uid})">
    <polygon points="${polyStr}" transform="translate(5,5)" fill="#141414"/>
    <polygon points="${polyStr}" fill="${color}" opacity=".18"/>
    <polygon points="${polyStr}" fill="url(#dots-${uid})"/>
    <polygon points="${polyStr}" fill="none" stroke="#141414" stroke-width="4" stroke-linejoin="round"/>
  </g>`;
  // 标签与数值
  axes.forEach((ax,k)=>{
    const [lx,ly]=pt(k,R+26);
    const anchorTxt = lx<cx-10?'end':(lx>cx+10?'start':'middle');
    s+=`<text x="${lx.toFixed(1)}" y="${(ly+5).toFixed(1)}" text-anchor="${anchorTxt}" font-size="14" font-family="'ZCOOL KuaiLe',sans-serif" fill="#141414" style="paint-order:stroke;stroke:#fffaf0;stroke-width:3.5px;stroke-linejoin:round" transform="rotate(${k%2? 2.5 : -2.5} ${lx.toFixed(1)} ${(ly+5).toFixed(1)})">${ax.label}</text>`;
  });
  poly.forEach((p,k)=>{
    const ax=axes[k];
    if(ax.val==null){
      const [dx,dy]=pt(k,R*0.55);
      s+=`<g transform="translate(${dx.toFixed(1)},${dy.toFixed(1)}) rotate(${k%2?-8:8})">
        <rect x="-30" y="-11" width="60" height="22" fill="#fff" stroke="#141414" stroke-width="2.5"/>
        <text text-anchor="middle" y="5" font-family="'Bangers',cursive" font-size="14" font-weight="bold" fill="#8a7a5c" style="paint-order:stroke;stroke:#fff;stroke-width:2px;stroke-linejoin:round">NO DATA!</text></g>`;
      return;
    }
    const vv=Math.max(0,Math.min(100,ax.val));
    const vx2=+p[0], vy2=+p[1];
    s+=`<circle cx="${vx2.toFixed(1)}" cy="${vy2.toFixed(1)}" r="5.5" fill="#fff" stroke="#141414" stroke-width="2.5"/>`;
    // 数值布局（几何验证）：高值(≥45)在顶点内侧径向 16+偶奇10px；低值在顶点外侧 +18px
    let tp;
    if(vv>=45){ tp = pt(k, vv/100*R - (16+(k%2)*10)); }
    else      { tp = pt(k, vv/100*R + 18); }
    s+=`<text x="${tp[0].toFixed(1)}" y="${(tp[1]+5).toFixed(1)}" text-anchor="middle" font-family="'Bangers',cursive" font-size="22" font-weight="bold" fill="#fff" style="paint-order:stroke;stroke:#141414;stroke-width:4px;stroke-linejoin:round">${ax.val}</text>`;
    // MAX 章不占轴位：在顶点处沿轴的垂直方向偏移 33px（偶奇定侧），落入两轴之间的空白
    if(ax.val>=90){
      const th=-Math.PI/2+k*2*Math.PI/n;
      const px=(k%2? -Math.sin(th): Math.sin(th))*33, py=(k%2? Math.cos(th): -Math.cos(th))*33;
      s+=`<g transform="translate(${(vx2+px).toFixed(1)},${(vy2+py).toFixed(1)}) rotate(${k%2?14:-12}) scale(1.15)">
        <polygon points="0,-16 4,-5 16,-8 7,0 14,9 3,5 0,16 -4,5 -14,9 -7,0 -16,-8 -4,-5" fill="#ffb703" stroke="#141414" stroke-width="2.5"/>
        <text text-anchor="middle" y="4.5" font-family="'Bangers',cursive" font-size="13" font-weight="bold" fill="#141414" style="paint-order:stroke;stroke:#fff;stroke-width:2.5px;stroke-linejoin:round">MAX!</text></g>`;
    }
  });
  s+=`<text x="180" y="294" text-anchor="middle" font-size="12" letter-spacing="2" fill="#141414" opacity=".6">${sub}</text></svg>`;
  return s;
}

/* ===== 详情层 ===== */
function int0(v){return v==null?null:parseInt(v);}
function openDetail(idx){
  const pos=curList.findIndex(x=>x.i===idx);
  if(pos<0) return;
  curIdx=pos;
  const d=DATA[idx];
  const f=FACTIONS.find(x=>x[0]===d.faction)||['','#666',''];
  const portrait=d.portrait
    ?`<img src="${d.portrait}" alt="${d.general}">`
    :`<div class="avatar-burst"><div class="starbg" style="background:${f[1]}77"></div><span class="bigchar">${d.general[0]}</span></div>`;
  const game5=[
    {label:'统率',val:int0(d.g&&d.g[0])},{label:'武力',val:int0(d.g&&d.g[1])},
    {label:'智力',val:int0(d.g&&d.g[2])},{label:'政治',val:int0(d.g&&d.g[3])},
    {label:'魅力',val:int0(d.g&&d.g[4])},
  ];
  const r6=d.r6||{};
  const model6=[
    {label:'HLE推理',val:r6.hle},{label:'GPQA科学',val:r6.gpqa},
    {label:'SciCode代码',val:r6.scicode},{label:'MMMU多模态',val:r6.mmmu},
    {label:'Tbench智能体',val:r6.tb},{label:'知识',val:r6.omni},
  ];
  const has6=Object.values(r6).some(v=>v!=null);
  const stats=[];
  if(d.ii) stats.push(`<span>II<b>${d.ii}</b></span>`);
  if(d.dw) stats.push(`<span>折算武力<b>${d.dw}</b></span>`);
  if(d.cost) stats.push(`<span>成本<b>$${d.cost}</b>/任务</span>`);
  if(d.speed) stats.push(`<span>速度<b>${d.speed}</b>t/s</span>`);
  if(!d.ii&&d.role!=='主公') stats.push(`<span><b>已退场</b>·史书阙载</span>`);
  sheetEl.innerHTML=`
    <button class="dclose" id="dclose">✕</button>
    <div class="dhead">
      <div class="dportrait">${portrait}</div>
      <div class="dtitle">
        <div class="fac">【${d.faction}】 · ${ROLES[d.role]||d.role}${d.anchor?' · ★ 数值锚点':''}</div>
        <h2>${d.general}</h2>
        <div class="badges"><span class="badge ${d.role}">${ROLES[d.role]||d.role}</span>
          ${d.anchor?'<span class="badge 主公">★ 锚点</span>':''}</div>
        <div class="dchips"><span class="mchip">${d.model}</span>${d.creator?`<span class="cchip">${d.creator}</span>`:''}</div>
        <div class="dstats">${stats.join('')||'<span>厂家机构位 · 不列单挑之数</span>'}</div>
      </div>
    </div>
    <div class="duelsection">
      <div class="radarbox"><h3>《三国志14》五维</h3><div class="sub">游戏原版数值 · 满值100</div>
        ${d.g?radarSVG(game5, '#d62828', 'GAME STATS · SAN14'):'<div style="padding:60px 0;font-size:18px;letter-spacing:3px">天子不列武臣册</div>'}</div>
      <div class="radarbox"><h3>《大模型》六维</h3><div class="sub">AA 基准子分 · 百分比</div>
        ${has6?radarSVG(model6, '#1d3557', 'BENCHMARK SCANS · AA SNAPSHOT'):'<div style="padding:60px 0;font-size:18px;letter-spacing:3px">已退场 · 无评测记录</div>'}</div>
    </div>
    <div class="bios">
      <div class="bio san"><h3>《三国志》本传 <span class="tag">GAME LORE</span></h3><p>${d.bio}</p></div>
      <div class="bio llm"><h3>《大模型纪》列传 <span class="tag">AI CHRONICLE</span></h3><p>${d.note}</p></div>
    </div>
    <div class="dnav">
      <button id="dprev">◀ 上一位</button>
      <span class="pos">${curIdx+1} / ${curList.length}</span>
      <button id="dnext">下一位 ▶</button>
    </div>`;
  document.getElementById('dclose').onclick=closeDetail;
  document.getElementById('dprev').onclick=()=>{curIdx=(curIdx-1+curList.length)%curList.length;openDetail(curList[curIdx].i);};
  document.getElementById('dnext').onclick=()=>{curIdx=(curIdx+1)%curList.length;openDetail(curList[curIdx].i);};
  overlayEl.classList.add('open');
  overlayEl.scrollTop=0;
  document.body.style.overflow='hidden';
}
function closeDetail(){overlayEl.classList.remove('open');document.body.style.overflow='';}
overlayEl.addEventListener('click',e=>{if(e.target===overlayEl)closeDetail();});
document.addEventListener('keydown',e=>{
  if(!overlayEl.classList.contains('open'))return;
  if(e.key==='Escape')closeDetail();
  if(e.key==='ArrowLeft'&&curIdx>=0){curIdx=(curIdx-1+curList.length)%curList.length;openDetail(curList[curIdx].i);}
  if(e.key==='ArrowRight'&&curIdx>=0){curIdx=(curIdx+1)%curList.length;openDetail(curList[curIdx].i);}
});

qEl.oninput=e=>{keyword=e.target.value.trim();render()};
sortEl.onclick=()=>{sortMode=sortMode==='faction'?'power':'faction';
  sortEl.textContent=sortMode==='faction'?'⚔ 按折算武力排序':'🚩 按阵营排序';render()};
render();
</script>
</body>
</html>
"""


def main():
    data = load_data()
    html = (TEMPLATE
            .replace("__FACTIONS__", json.dumps(FACTION_META, ensure_ascii=False))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    out = os.path.join(ROOT, "docs", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    portraits = sum(1 for d in data if d["portrait"])
    print(f"site built: {len(data)} seats ({portraits} with portraits) -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
