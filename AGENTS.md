# AGENTS.md — 大模型三国志项目指南

本文件供 ZCode/AI 助手在新会话中快速接续工作。人类贡献者也可当作项目速览。

## 项目一句话

以《三国志14》全武将数值与 Artificial Analysis 模型评测为两大史源，给大模型立传排座的开源对照项目。

## 关键事实（新会话先读这个）

- **数据**：`data/sanguo14_officers.csv`（1180 武将，Nobuwiki 整理的 PK 版数据）；AA 快照按抓取日留档（`data/aa_models_snapshot_*.csv`，现行 2026-10-16 版 703 模型/693 有分，2026-10-10 版 697 为首份），文件名=抓取日期，enrich 与站点自动取最新；**模型不成长**——已发布模型 II 不变，跨快照的折算值变化全部来自环境：榜首基准通胀、新秀进榜、降价、调用份额迁移。**江湖变迁=席位易主（对应关系变化），非数值、非成长**：席位调整人工裁决并登记 `mapping/seat_history.csv`（详情页展示易主记录），数值流动由管线自动完成
- **方法论**：`docs/methodology.md`。核心规则——武力 ↔ Intelligence Index 为最高权重（0.7），折算公式 `武力 = round(II ÷ 榜首II × 100)`；智力 = 性价比（成本反比，权重 0.3）；统率/政治/魅力对应 agentic/对齐/调用量，暂无数据源；阵营典故仅作叙事；模型名不带推理档位后缀（max/xhigh 等），数值统一取最高档；折算统率 = agentic 四子分均值÷榜首×100，折算智力 = (1−成本百分位)×100，折算魅力 = OpenRouter 调用份额÷榜首×100（fetch_openrouter.py 抓取），折算政治 = ifbench与不幻觉率均值÷榜首×100
- **映射**：`mapping/mapping_v0.8.csv` 演义版 103 席（武力/统率/智力/魅力/政治五维全折算）（双套数值：游戏原版 + 模型折算）；`mapping/mapping_source.csv` 是人工维护源（只写关系与典故，数值由脚本联结）。铁律：主公位=厂家机构位只写公司名（曹操=OpenAI、刘备=幻方量化、孙权=Meta），模型只坐武将/诸侯位（退役与否写进 note，不设"已故"角色）；血缘武将同厂商；模型名不带推理档位后缀、数值取最高档
- **脚本**：`scripts/enrich_mapping.py`（改 mapping_source.csv 后重跑，产出 v0.8）；`scripts/fetch_openrouter.py`（抓 OpenRouter 调用榜，魅力维度数据源）；`scripts/build_site.py`（v0.5 → 美漫风展示站 `docs/index.html`，改完映射记得重跑）；`scripts/rebuild_snapshot.py`（快照重建，--leaderboard 单页全库为首选）；`scripts/match.py --model "模型名"`（天命版自动匹配）；`scripts/pipeline.sh`（江湖周更一键管线，GitHub Action 每周自动）；`scripts/drift_report.py`（王座易主/新秀警报 → docs/DRIFT.md）
- **锚点验证**：Opus 5.5 ↔ 吕布 100:100；GPT-5.6 Sol ↔ 文聘 82:82；Fable 5.1 ↔ 文醜 93:94；GPT-6 Astra ↔ 曹彰 91:90；Opus 5 ↔ 高順 88:86；Claude Haiku 5.5 ↔ 曹性 75:74；GPT-4 ↔ 荀彧 12:14；Olmo ↔ 顧雍 12:18；MiMo 政 67 ↔ 姜維 政 67
- **阵营设定**：曹魏=美国闭源（曹操=OpenAI，Google/xAI 客将）；蜀汉=中国阵营（刘备=幻方量化 DeepSeek 生态）；东吴=开源联盟（孙权=Meta、鲁肃=HuggingFace 平台位双主公）；群雄=厂家诸侯会盟、多主公制——袁绍=Anthropic 领衔（Claude 系五代家将尽归其门下），董卓=Microsoft（Bing 暴政）、何进=IBM、袁术=Inflection、刘表=Google、刘璋=Cohere、公孙瓒=Aleph Alpha、陶谦=Stability、张鲁=01.AI、孟获=Amazon，吕布军、黄巾、南中均已并入群雄；汉献帝=NVIDIA、司马懿=Microsoft 暗线、王允=FTC。客将不得越本家仕敌营（Anthropic 模型只在袁绍营）

## 路线图

进度与待办见 `docs/ROADMAP.md`。本文件只保留长期事实，不记临时进度。

## 注意事项

- 榜单数据有强时效性，涉及模型版本号的讨论先核对快照日期，别用训练语料里的旧版本号（本项目踩过坑：曾把 GPT-6 时代写成 o4）
- AA 核对的正确姿势（勿再猜 slug/手拼行）：首选 `curl https://artificialanalysis.ai/leaderboards/models` 一页拿到全库（`rebuild_snapshot.py --leaderboard` 解析内嵌 `models` 数组，含 creator 与全部指标）；备选 sitemap 逐页模式（`--pages`）；补录行 source 指向模型页。`data/aa_models_raw.tsv` 是 leaderboard **表格导出留档**（267 行现役口径），保持原貌、不参与折算；清洗后的 `data/aa_models_snapshot_2026-10-10.csv` 才是全库（697 模型、687 有分）。退役模型有页有分，但不在那 267 行表格里。补录只进清洗后的 CSV
- 武将名沿用游戏数据的繁体写法（孫權=孙权同一人），叙述文本用简体即可，勿改数据侧繁体名
- 漢獻帝不在三国志14武将册（游戏不收录皇帝），其五维为空是有意设定，勿当缺失修
- `data/` 下 `*_raw.*` 为原始导出留档，勿删
- `docs/portraits/` 为 102 席武将立绘（Nobuwiki 武将页采集，© KOEI TECMO，82 张；无页面的 20 席由站点生成美漫姓氏头像），来源与版权口径同数值数据
- 数据版权：三国志数值 © KOEI TECMO，评测 © Artificial Analysis，仅注明来源的非商业整理
