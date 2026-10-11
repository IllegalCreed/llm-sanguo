[English](README.en.md)

# 大模型三国志（LLM Sanguo）

[![在线站点](https://img.shields.io/badge/site-GitHub%20Pages-2a9d8f?style=flat-square)](https://illegalcreed.github.io/llm-sanguo/)
[![代码 MIT](https://img.shields.io/badge/code-MIT-1d3557?style=flat-square)](LICENSE)

**在线看：<https://illegalcreed.github.io/llm-sanguo/>**

> 人中吕布，马中赤兔，卡中 Blackwell。

它把 [Artificial Analysis](https://artificialanalysis.ai/leaderboards/models) 2026-10-10 的模型评测，和《三国志14 威力加强版》1180 名武将的五维放在一起，给大模型排座位：武力看智能指数，智力看性价比，主公位只坐厂家。

演义版现编排 **102 席**，做成一页美漫风武将卡。可以按阵营切换、搜索、排序；点开一位，能看到立绘（或姓氏头像）、游戏五维和模型基准两张雷达，以及两朝列传。页面是纯静态的，打开就能看。

## 怎么对上的

1. **武力 ↔ Intelligence Index**（权重 0.7）。以当次快照榜首为 100：`折算武力 = round(模型 II ÷ 榜首 II × 100)`。榜首是 Claude Opus 5.5，II **57.6**。
2. **智力 ↔ 性价比**（权重 0.3）。每任务成本越低，智力百分位越高。
3. 统率 / 政治 / 魅力对应 agentic、对齐、调用量。快照里还没有这些列，暂时人工写。
4. 阵营和典故只负责叙事、打破并列，不参与打分。主公位写公司（曹操 = OpenAI，刘备 = 幻方量化，孙权 = Meta，袁绍 = Anthropic），模型只坐武将或诸侯位。

天命版用百分位距离自动匹配：`score = 0.7 × |II 百分位 − 武力百分位| + 0.3 × |性价比百分位 − 智力百分位|`，越小越像。站点展示的 102 席是演义版：阵营优先，强度仍受上面的公式约束。两套结果允许不一样。

站点上标了星的八组数值锚点，都来自现行演义表 `mapping/mapping_v0.5.csv`（折算武力 : 游戏原版武力）：

| 模型 | 武将 | 折算 : 原版 |
|---|---|---|
| Claude Opus 5.5 | 吕布 | 100 : 100 |
| Claude Fable 5.1 | 文丑 | 93 : 94 |
| GPT-6 Astra | 曹彰 | 91 : 90 |
| Claude Opus 5 | 高顺 | 88 : 86 |
| GPT-5.6 Sol | 文聘 | 82 : 82 |
| Claude Haiku 5.5 | 曹性 | 75 : 74 |
| GPT-4 | 荀彧 | 12 : 14 |
| Olmo 3.1 32B Think | 顾雍 | 12 : 18 |

GPT-6 Astra 对曹彰，是折算武力 91 与原版 90 的重合。`mapping/suggestions_tianming.csv` 是更早一份整数分表格上的天命建议，里面 Astra 最近的是颜良；那张表不驱动现在这个页面。

## 站点一览

总览（桌面宽度）：

![总览：标题、统计与武将列表](docs/assets/overview.png)

群雄一页（袁绍 = Anthropic，35 席）：

![群雄阵营](docs/assets/faction-qun.png)

吕布 / Claude Opus 5.5 的详情：游戏五维雷达和模型基准雷达。

![吕布详情与双雷达](docs/assets/detail-lubu.png)

手机宽度（390）：

![手机宽度首页](docs/assets/mobile.png)

![手机宽度详情](docs/assets/mobile-detail.png)

阵营切换，再点开吕布：

![浏览动图](docs/assets/browse.gif)

## 快照口径

脚本和站点用的是清洗后的全库表 `data/aa_models_snapshot_2026-10-10.csv`：**697 个模型，其中 687 个有 Intelligence Index**。`data/aa_models_raw.tsv` 是更早的 leaderboard 表格导出，**267 行现役口径**，只留档，不参与现行折算。武将表 `data/sanguo14_officers.csv` 是 1180 人。

## 本地生成

Python 3，只用标准库，没有第三方依赖。

```bash
# 天命版：按当前快照给模型找最接近的武将（会重写 mapping/suggestions_tianming.csv）
python3 scripts/match.py --model "Claude Opus 5.5"

# 演义表：改完 mapping/mapping_source.csv 后重算数值
python3 scripts/enrich_mapping.py

# 展示页：mapping/mapping_v0.5.csv → docs/index.html
python3 scripts/build_site.py
```

生成后用浏览器打开 `docs/index.html`，或在 `docs/` 下起一个静态服务器。GitHub Pages 发布的就是这个目录。

## 目录

```
├── data/
│   ├── sanguo14_officers.csv                 # 1180 名武将，清洗后
│   ├── aa_models_snapshot_2026-10-10.csv     # 全库快照：697 模型 / 687 有分
│   ├── aa_models_raw.tsv                     # 表格导出留档：267 行现役口径
│   └── *_raw.*
├── docs/
│   ├── index.html                            # 展示页（build_site.py 生成）
│   ├── methodology.md                        # 映射方法论
│   ├── ROADMAP.md
│   ├── portraits/                            # 82 张立绘；其余 20 席用姓氏头像
│   └── assets/                               # 本 README 的截图
├── mapping/
│   ├── mapping_source.csv                    # 人工维护：只写关系与典故
│   ├── mapping_v0.2.csv … mapping_v0.4.csv   # 历史版本
│   ├── mapping_v0.5.csv                      # 现行演义版 102 席，站点数据源
│   └── suggestions_tianming.csv              # 天命版建议（旧表口径留档）
├── scripts/
│   ├── enrich_mapping.py                     # source → v0.5
│   ├── build_site.py                         # v0.5 → docs/index.html
│   ├── rebuild_snapshot.py                   # 重建 AA 快照
│   └── match.py                              # 天命版自动匹配
├── LICENSE                                   # MIT，只覆盖代码
├── NOTICE                                    # 数值与立绘的归属
└── AGENTS.md
```

武将名在数据文件里保持游戏原表的繁体。叙述用简体，二者是同一人。

## 路线图

已经做完的：两份史源、方法论、演义版 v0.5（102 席）、天命版脚本、美漫风单页。站点已挂在 GitHub Pages。

还没做的：

- 接入 AA Agentic / Coding 指数，补「统率」
- 接入 OpenRouter 调用份额，补「魅力」
- 保留历史快照，对比出武将的成长曲线

细节在 [docs/ROADMAP.md](docs/ROADMAP.md)，规则在 [docs/methodology.md](docs/methodology.md)。

## 数据、立绘与许可

[LICENSE](LICENSE) 是标准 MIT，**只覆盖本仓库的代码**（`scripts/` 与项目文档）。下面这些不在 MIT 里：

- 《三国志14》武将数值，以及 `docs/portraits/` 里的立绘，版权归 **© KOEI TECMO GAMES**，整理自 [Nobuwiki](https://www.nobuwiki.org/san/game_14/s14_01)
- 模型评测数字版权归 **Artificial Analysis**

本项目是注明来源的非商业对照，与光荣特库摩、Artificial Analysis 都没有隶属关系。权利人如需下架，请到本仓库开一个 [GitHub issue](https://github.com/IllegalCreed/llm-sanguo/issues)。完整说明见 [NOTICE](NOTICE)。

## 贡献

欢迎提 issue / PR：换将、补将、修数值、加典故都可以。规则只有一条——**先看数据，再谈演义**（改映射请引用两份史源，别拍脑袋）。
