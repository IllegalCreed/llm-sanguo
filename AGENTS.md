# AGENTS.md — 大模型三国志项目指南

本文件供 ZCode/AI 助手在新会话中快速接续工作。人类贡献者也可当作项目速览。

## 项目一句话

以《三国志14》全武将数值与 Artificial Analysis 模型评测为两大史源，给大模型立传排座的开源对照项目。

## 关键事实（新会话先读这个）

- **数据**：`data/sanguo14_officers.csv`（1180 武将，Nobuwiki 整理的 PK 版数据）；`data/aa_models_snapshot_2026-10-10.csv`（267 模型，快照日期即文件名）
- **方法论**：`docs/methodology.md`。核心规则——武力 ↔ Intelligence Index 为最高权重（0.7），折算公式 `武力 = round(II ÷ 榜首II × 100)`；智力 = 性价比（成本反比，权重 0.3）；统率/政治/魅力对应 agentic/对齐/调用量，暂无数据源；阵营典故仅作叙事
- **映射**：`mapping/mapping_v0.2.csv` 演义版 51 席（双套数值：游戏原版 + 模型折算）；`mapping/mapping_source.csv` 是人工维护源（只写关系与典故，数值由脚本联结）
- **脚本**：`scripts/enrich_mapping.py`（改 mapping_source.csv 后重跑）；`scripts/match.py --model "模型名"`（天命版自动匹配）
- **锚点验证**：Opus 5.5 ↔ 吕布 距离 0.000；GPT-6 Astra ↔ 颜良 0.004
- **阵营设定**：曹魏=美国闭源（OpenAI 为宗，Google/xAI 客将）；蜀汉=中国阵营（刘备=DeepSeek 生态）；东吴=开源联盟（孙权=Meta）；吕布军=Anthropic；汉献帝=NVIDIA/CUDA 彩蛋

## 已完成

- [x] 两份史源数据采集与清洗（2026-10-10）
- [x] 方法论成文、演义版 51 席、天命版自动匹配
- [x] GitHub 仓库建立与首次推送

## 下一步（按优先级）

1. **武将卡网页**（计划放 `docs/` 并挂 GitHub Pages）：读 `mapping/mapping_v0.2.csv`，每张卡 = 五维雷达图双轴对比（游戏原版 vs 模型折算）+ 列传典故。推荐纯静态（单 HTML + 内嵌数据），无构建依赖
2. AA 快照更新脚本：历史快照保留，对比可做"武将成长曲线"
3. 接入 OpenRouter 调用份额补全"魅力"维度；接入 AA Agentic/Coding 指数补全"统率"

## 注意事项

- 榜单数据有强时效性，涉及模型版本号的讨论先核对快照日期，别用训练语料里的旧版本号（本项目踩过坑：曾把 GPT-6 时代写成 o4）
- `data/` 下 `*_raw.*` 为原始导出留档，勿删
- 数据版权：三国志数值 © KOEI TECMO，评测 © Artificial Analysis，仅注明来源的非商业整理
