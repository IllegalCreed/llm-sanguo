#!/usr/bin/env python3
"""从 mapping/mapping_v0.5.csv 生成美漫风格展示站 docs/index.html。

纯静态单页：数据内嵌为 JS 常量，无前端构建依赖，可直接挂 GitHub Pages。
改完映射后重跑本脚本即可同步（或先跑 enrich_mapping.py 再跑本脚本）。
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FACTION_META = [
    ("汉献帝朝廷", "#8d6e63", "天下与舞台 —— 基础设施与监管的暗流"),
    ("曹魏", "#1d3557", "美国闭源阵营 —— 曹操=OpenAI 为宗，Google/xAI 客将"),
    ("蜀汉", "#c1121f", "中国大模型阵营 —— 刘备=幻方量化（DeepSeek 生态）"),
    ("东吴", "#2a9d8f", "开源联盟 —— 孙权=Meta、鲁肃=HuggingFace 双主公"),
    ("群雄", "#6a4c93", "厂家诸侯会盟 —— 袁绍=Anthropic 领衔，多主公制"),
]
ANCHORS = {"呂布", "文聘", "文醜", "曹彰", "高順", "曹性", "荀彧", "顧雍"}
ROLE_LABEL = {"主公": "主公", "诸侯": "诸侯", "武将": "武将", "彩蛋": "彩蛋", "暗线": "暗线"}


def load_data():
    path = os.path.join(ROOT, "mapping", "mapping_v0.5.csv")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data = []
    for r in rows:
        data.append({
            "role": r["role"], "faction": r["faction"], "general": r["general"],
            "model": r["model"], "creator": r["creator"],
            "ii": r["aa_ii"], "dw": r["derived_warfare"],
            "cost": r["cost_per_task_usd"], "speed": r["median_tokens_per_s"],
            "war": r["game_warfare"], "total": r["game_total"],
            "note": r["note"],
            "anchor": r["general"] in ANCHORS,
        })
    return data


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大模型三国志 —— LLM SANGUO CHRONICLES</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=ZCOOL+KuaiLe&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#141414; --paper:#f6ecd9; --cream:#fffaf0;
  --red:#d62828; --yellow:#ffb703; --blue:#1d3557; --teal:#2a9d8f; --purple:#6a4c93; --brown:#8d6e63;
}
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:'ZCOOL KuaiLe','PingFang SC','Microsoft YaHei',sans-serif;
  background:var(--paper); color:var(--ink); overflow-x:hidden;
}
/* 网点纸（Ben-Day dots）*/
body::before{
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
  background-image:radial-gradient(circle, rgba(20,20,20,.10) 1.2px, transparent 1.6px);
  background-size:9px 9px;
}
.bangers{font-family:'Bangers',cursive}
.wrap{position:relative;z-index:1;max-width:1280px;margin:0 auto;padding:24px 20px 80px}

/* ===== 报头 ===== */
.masthead{position:relative;text-align:center;padding:34px 10px 26px;
  border:5px solid var(--ink); background:var(--cream);
  box-shadow:10px 10px 0 var(--ink); margin-bottom:18px; overflow:hidden}
.masthead::after{content:'';position:absolute;inset:0;
  background:linear-gradient(115deg, transparent 49.6%, rgba(20,20,20,.05) 50%, transparent 50.4%)}
.topstrip{display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;
  font-size:13px;letter-spacing:2px;border-bottom:3px solid var(--ink);padding:0 90px 8px;margin-bottom:14px}
.topstrip .bangers{font-size:15px}
h1{font-size:clamp(44px,8vw,92px);line-height:.95;letter-spacing:6px;
  text-shadow:5px 5px 0 var(--yellow), 10px 10px 0 rgba(20,20,20,.18)}
h1 span{color:var(--red); -webkit-text-stroke:2px var(--ink)}
.subtitle{margin-top:10px;font-size:clamp(15px,2.4vw,22px);letter-spacing:4px}
.subtitle b{background:var(--ink);color:var(--yellow);padding:2px 10px;margin:0 6px}
/* 爆炸字 */
.burst{position:absolute;display:flex;align-items:center;justify-content:center;text-align:center;
  background:var(--red);color:#fff;transform:rotate(-12deg);
  clip-path:polygon(50% 0%,61% 12%,75% 5%,79% 20%,95% 18%,90% 33%,100% 44%,88% 52%,95% 66%,79% 66%,77% 82%,63% 74%,50% 88%,37% 74%,23% 82%,21% 66%,5% 66%,12% 52%,0% 44%,10% 33%,5% 18%,21% 20%,25% 5%,39% 12%);
  box-shadow:none; font-size:15px; width:110px;height:110px; line-height:.9}
.burst b{font-family:'Bangers',cursive;font-size:26px;transform:rotate(6deg);text-shadow:2px 2px 0 rgba(0,0,0,.35)}
.burst.b1{top:-30px;left:-30px;background:var(--red)}
.burst.b2{bottom:-28px;right:-26px;background:var(--blue);transform:rotate(10deg)}
.statline{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin:22px 90px 6px}
.statline .chip{border:3px solid var(--ink);background:#fff;padding:6px 14px;font-size:15px;
  box-shadow:4px 4px 0 var(--ink); letter-spacing:1px}
.statline .chip b{font-family:'Bangers',cursive;font-size:20px;margin-right:6px;color:var(--red)}

/* ===== 工具条 ===== */
.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;
  border:4px solid var(--ink);background:var(--yellow);box-shadow:7px 7px 0 var(--ink);
  padding:12px 14px;margin:26px 0 30px; position:sticky;top:10px;z-index:50}
.tabs{display:flex;flex-wrap:wrap;gap:8px}
.tab{cursor:pointer;border:3px solid var(--ink);background:#fff;padding:7px 14px;font-size:16px;
  letter-spacing:2px;user-select:none;transition:transform .12s;position:relative;font-family:inherit}
.tab:hover{transform:translate(-2px,-2px);box-shadow:4px 4px 0 var(--ink)}
.tab.on{background:var(--ink);color:var(--yellow);box-shadow:4px 4px 0 rgba(20,20,20,.3)}
.tab .dot{display:inline-block;width:12px;height:12px;border:2px solid var(--ink);border-radius:50%;
  margin-right:6px;vertical-align:-1px}
.tab.on .dot{border-color:var(--yellow)}
.tools-right{display:flex;gap:8px;align-items:center}
.search{border:3px solid var(--ink);padding:7px 12px;font-size:15px;font-family:inherit;
  background:#fff;min-width:180px;outline:none}
.search:focus{box-shadow:4px 4px 0 var(--ink)}
.sortbtn{cursor:pointer;border:3px solid var(--ink);background:#fff;padding:7px 12px;
  font-size:15px;font-family:inherit;letter-spacing:1px}
.sortbtn:hover{box-shadow:4px 4px 0 var(--ink)}
.factionhead{display:none;margin:34px 0 14px;border:4px solid var(--ink);padding:10px 16px;
  background:var(--cream);box-shadow:6px 6px 0 var(--ink);align-items:baseline;gap:14px;flex-wrap:wrap}
.factionhead.show{display:flex}
.factionhead h2{font-size:26px;letter-spacing:3px}
.factionhead p{font-size:15px;opacity:.85}
.factionhead .stamp{margin-left:auto;font-family:'Bangers',cursive;font-size:14px;letter-spacing:1px;
  border:3px solid var(--ink);padding:3px 10px;transform:rotate(-2deg);background:#fff}

/* ===== 卡片网格 ===== */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(315px,1fr));gap:26px;margin-top:8px}
.panel{position:relative;border:4px solid var(--ink);background:var(--cream);
  box-shadow:9px 9px 0 var(--ink);padding:16px 16px 14px;transition:transform .15s,box-shadow .15s;
  display:flex;flex-direction:column;gap:10px}
.panel:nth-child(4n+1){transform:rotate(-.5deg)} .panel:nth-child(4n+3){transform:rotate(.5deg)}
.panel:hover{transform:translate(-4px,-4px) rotate(0deg)!important;box-shadow:14px 14px 0 var(--ink);z-index:5}
.panel .fbar{position:absolute;top:0;left:0;right:0;height:8px}
.phead{display:flex;align-items:flex-start;gap:10px;margin-top:6px}
.gname{font-size:30px;letter-spacing:3px;line-height:1.05;flex:1}
.gname small{display:block;font-size:13px;letter-spacing:2px;opacity:.65;margin-top:3px}
.badge{flex-shrink:0;border:3px solid var(--ink);font-size:13px;padding:3px 9px;letter-spacing:2px;
  background:#fff;transform:rotate(3deg);font-family:inherit}
.badge.主公{background:var(--yellow)} .badge.诸侯{background:#e0aaff} .badge.彩蛋{background:#ffd6e0}
.badge.暗线{background:var(--ink);color:#fff} .badge.武将{background:#fff}
.anchorstar{position:absolute;top:-16px;right:-14px;width:44px;height:44px;background:var(--red);
  color:#fff;display:flex;align-items:center;justify-content:center;transform:rotate(12deg);
  font-size:22px;clip-path:polygon(50% 0%,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%)}
.mrow{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.mchip{border:3px solid var(--ink);background:#fff;padding:4px 10px;font-size:15px;letter-spacing:1px;
  font-family:'Courier New',monospace;font-weight:bold;box-shadow:3px 3px 0 rgba(20,20,20,.25)}
.cchip{border:2px solid var(--ink);padding:3px 9px;font-size:13px;background:#eee;letter-spacing:1px}
.dead{font-size:13px;color:#7a5c3e;letter-spacing:1px}
/* 武力对比条 */
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
/* 列传旁白框 */
.caption{position:relative;border:3px solid var(--ink);background:var(--yellow);
  padding:10px 12px 9px;font-size:15px;line-height:1.55;letter-spacing:.5px;
  box-shadow:4px 4px 0 rgba(20,20,20,.35)}
.caption::before{content:'★ 列传';position:absolute;top:-13px;left:10px;background:var(--ink);
  color:#fff;font-size:12px;padding:2px 10px;letter-spacing:3px}
.footer{margin-top:60px;text-align:center;font-size:14px;letter-spacing:2px;line-height:2}
.footer .bangers{font-size:22px;color:var(--red)}
.empty{display:none;text-align:center;font-size:22px;letter-spacing:4px;padding:60px 0;border:4px dashed var(--ink);margin-top:20px}
@media (max-width:640px){ .burst{display:none} .toolbar{position:static} }
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
    方法论与完整数据见仓库 docs/ · 折算武力 = II ÷ 榜首57.6 × 100 · 锚点席带红星<br>
    <span style="opacity:.6">仅注明来源的非商业整理 · 三国志数值 © KOEI TECMO · 评测 © Artificial Analysis</span>
  </footer>
</div>

<script>
const FACTIONS = __FACTIONS__;
const DATA = __DATA__;
const INK='#141414';

const tabsEl=document.getElementById('tabs'), grid=document.getElementById('grid'),
      qEl=document.getElementById('q'), sortEl=document.getElementById('sortbtn'),
      fhEl=document.getElementById('factionhead'), emptyEl=document.getElementById('empty');
let faction='全部', sortMode='faction', keyword='';

const factionOrder = Object.fromEntries(FACTIONS.map((f,i)=>[f[0],i]));
const roleOrder={'主公':0,'暗线':1,'诸侯':2,'武将':3,'彩蛋':4};

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
  if(d.total) m.push(`<span>游戏五维合计 <b>${d.total}</b></span>`);
  if(!d.ii && d.role!=='主公') m.push(`<span>💀 退役/无页 —— 史书阙载</span>`);
  return m.length?`<div class="meta">${m.join('')}</div>`:'';
}

function card(d){
  const f=FACTIONS.find(x=>x[0]===d.faction)||['','#666',''];
  const anchor=d.anchor?'<div class="anchorstar">★</div>':'';
  const creator=d.creator?`<span class="cchip">${d.creator}</span>`:'';
  const dead=(!d.ii&&d.role!=='主公')?'<span class="dead">（已退场）</span>':'';
  return `<article class="panel">
    <div class="fbar" style="background:${f[1]}"></div>${anchor}
    <div class="phead">
      <div class="gname">${d.general}<small>${d.faction} · ${ROLE(d)}</small></div>
      <span class="badge ${d.role}">${ROLE(d)}</span>
    </div>
    <div class="mrow"><span class="mchip">${d.model}</span>${creator}${dead}</div>
    ${bars(d)}${meta(d)}
    <div class="caption">${d.note}</div>
  </article>`;
}
function ROLE(d){return ({'主公':'主公','诸侯':'诸侯','武将':'武将','彩蛋':'彩蛋','暗线':'暗线'})[d.role]||d.role}

function filtered(){
  let list=DATA.filter(d=>{
    if(faction!=='全部'&&d.faction!==faction) return false;
    if(keyword){
      const k=keyword.toLowerCase();
      if(!(d.general.toLowerCase().includes(k)||d.model.toLowerCase().includes(k)
        ||(d.creator||'').toLowerCase().includes(k)||d.note.toLowerCase().includes(k))) return false;
    }
    return true;
  });
  if(sortMode==='power'){
    list.sort((a,b)=>(parseInt(b.dw||0)-parseInt(a.dw||0))||(parseInt(b.war||0)-parseInt(a.war||0)));
  }else{
    list.sort((a,b)=>(factionOrder[a.faction]-factionOrder[b.faction])
      ||(roleOrder[a.role]-roleOrder[b.role])
      ||(parseInt(b.dw||0)-parseInt(a.dw||0)));
  }
  return list;
}

function render(){
  tabHTML();
  const list=filtered();
  grid.innerHTML=list.map(card).join('');
  const f=FACTIONS.find(x=>x[0]===faction);
  if(f){ fhEl.classList.add('show');
    document.getElementById('fh-name').textContent='【'+f[0]+'】';
    document.getElementById('fh-name').style.color=f[1];
    document.getElementById('fh-desc').textContent=f[2];
    document.getElementById('fh-count').textContent=list.length+' SEATS';
  } else fhEl.classList.remove('show');
  emptyEl.style.display=list.length?'none':'block';
}

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
    print(f"site built: {len(data)} seats -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
