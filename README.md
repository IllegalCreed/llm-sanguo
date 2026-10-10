# 大模型三国志（LLM Sanguo）

以《三国志14》全武将数值与 [Artificial Analysis](https://artificialanalysis.ai/leaderboards/models) 模型评测为两大"史源"，把当今 AI 大模型与三国武将一一对应的开源对照项目。

> 人中吕布，马中赤兔，卡中 Blackwell。

## 这是什么

- 《三国志14 威力加强版》全 **1180 名武将**的五维数值（统率/武力/智力/政治/魅力）——数据来自 [Nobuwiki「三國志14 威力加強版」全武將數據一覽](https://www.nobuwiki.org/san/game_14/s14_01)
- Artificial Analysis 榜单 **267 个模型**的评测快照（Intelligence Index / 单任务成本 / 速度 / 延迟）——抓取于 2026-10-10
- 一套带权重的映射方法论：**武力 ↔ 模型智力（Intelligence Index）为最高权重主轴**，其余数值维度次之，阵营与生平典故仅作最低权重的叙事调味
- 自动匹配脚本：按百分位加权距离，为任意模型推荐最匹配的武将（"天命版"纯强度匹配），与人工编排的"演义版"（阵营优先、强度约束）并行

## 目录结构

```
├── data/
│   ├── sanguo14_officers.csv              # 三国志14全武将五维数据（清洗后）
│   ├── aa_models_snapshot_2026-10-10.csv  # AA 模型评测快照（清洗后）
│   └── *_raw.*                            # 原始导出留档
├── docs/
│   └── methodology.md                     # 映射方法论与权重规则
├── mapping/
│   ├── mapping_source.csv                 # 人工维护的映射源（只写关系与典故）
│   ├── mapping_v0.2.csv                   # 脚本联结后的完整映射（双套数值）
│   └── suggestions_tianming.csv           # 天命版自动匹配建议
└── scripts/
    ├── enrich_mapping.py                  # 联结两份数据，生成 mapping_v0.2.csv
    └── match.py                           # 加权百分位自动匹配
```

## 快速开始

```bash
# 为某个模型找最像的武将（天命版：纯强度百分位匹配）
python3 scripts/match.py --model "Claude Opus 5.5 (max with fallback)"

# 查看全部自动匹配建议
python3 scripts/match.py --top 5

# 重新生成映射表（改动 mapping_source.csv 后）
python3 scripts/enrich_mapping.py
```

## 核心规则（详见 docs/methodology.md）

1. **武力 = Intelligence Index 折算**，以当世第一（吕布 = 快照中 II 最高的模型）为 100 基准：
   `折算武力 = round(模型II / 榜首II × 100)`
2. **智力 = 性价比**（每任务成本的反比）——谋士以计破力，模型以性价比破算力军备
3. 统率 / 政治 / 魅力 对应 agentic 能力 / 指令遵循与对齐 / 调用量与生态口碑，目前快照未含这些列，暂由人工评估，路线图中接入
4. **阵营与典故（曹魏=美国闭源、蜀汉=中国阵营、东吴=开源联盟等）权重最低**，只用于打破并列与叙事

两个锚点验证（天命版自动算出，详见 `mapping/suggestions_tianming.csv`）：

- **Claude Opus 5.5 (max) ↔ 吕布：距离 0.000**——II 百分位与武力百分位双双第一，且都以"贵、性价比低"著称（吕布原版政治 13 魅力 36；Opus 每任务 $5.98）
- **GPT-6 Astra (max) ↔ 颜良：距离 0.004**——武力顶级而"第一"地位屡遭争议（OpenAI 自称最强 vs AA 榜首另有其人），许田围猎的剧本是数据自动写出来的

## 数据来源与致谢

| 数据 | 来源 | 采集方式 |
|---|---|---|
| 三国志14全武将数值 | [Nobuwiki](https://www.nobuwiki.org/san/game_14/s14_01)（光荣特库摩游戏数据整理） | 浏览器渲染导出 |
| 模型评测快照 | [Artificial Analysis](https://artificialanalysis.ai/leaderboards/models) | 浏览器渲染导出，快照日期 2026-10-10 |

《三国志》相关版权归 © KOEI TECMO GAMES 所有；评测数据版权归 Artificial Analysis 所有。本项目仅作技术社区娱乐性类比与数据整理，不用于商业用途。

## 路线图

- [ ] 武将卡网页：五维雷达图 + 模型折算值 + 列传典故
- [ ] 接入 AA Agentic / Coding 指数，补全"统率"维度
- [ ] 接入 OpenRouter 调用份额，补全"魅力"维度
- [ ] AA 快照定期更新脚本（历史快照对比 = 武将的"成长曲线"）

## 贡献

欢迎提 issue / PR：换将、补将、修数值、加典故都可以。规则只有一条——**先看数据，再谈演义**（改映射请引用两份史源数据，别拍脑袋）。
