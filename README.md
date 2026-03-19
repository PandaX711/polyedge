# PolyEdge — 基于 Polymarket 的体育竞猜分析与下注系统

## Context

用户希望构建一个体育竞猜分析和下注产品，利用 Polymarket 预测市场的公开 API 进行足球赛事分析和程序化下注。第一阶段覆盖欧洲五大联赛 + 欧冠，第二阶段重点面向 2026 世界杯（6.11-7.19，美加墨三国举办，48 队新赛制）。

产品定位：第一版做简单 Web 页面 + 规则策略引擎，后续迭代为完整 Web 平台。

---

## 一、产品概述

### 1.1 核心功能

| 模块 | V1（MVP） | V2（世界杯版） |
|------|-----------|----------------|
| 市场扫描 | 自动发现 Polymarket 上五大联赛/欧冠赛事市场 | 新增世界杯市场，支持小组赛/淘汰赛/冠军盘 |
| 三方赔率对比 | **三角对比**：Polymarket 隐含概率 vs 博彩公司赔率 vs AI 预测赔率，三方偏差可视化 | 实时赔率变动追踪 + 三方历史偏差趋势图 |
| AI 分析 | LLM 综合分析赛事基本面，输出独立的预测概率和赔率 | 多轮推理 + 赛前/赛中动态更新 |
| 策略信号 | 基于三方赔率偏差 + 规则策略生成 BUY/SELL 信号 | 增加世界杯专属策略（大赛特征） |
| 下注执行 | 手动确认后通过 CLOB API 下单 | 半自动模式：信号触发 → 通知确认 → 自动执行 |
| 仪表盘 | 持仓/PnL/活跃信号展示 | 历史回测报告 + 策略绩效对比 |

### 1.2 覆盖赛事

**第一阶段（2026.4 — 2026.6）**
- Premier League (EPL) — Polymarket ~39 个活跃市场
- La Liga — ~43 个活跃市场
- Serie A — ~40 个活跃市场
- Bundesliga — ~42 个活跃市场
- Ligue 1 — ~34 个活跃市场
- Champions League — ~72+ 个活跃市场

**第二阶段（2026.6 — 2026.7）**
- 2026 FIFA World Cup — 当前已有 $3.3 亿交易量的冠军盘 + 小组赛市场
- 48 队新赛制，12 个小组，预计会有大量新市场上线

---

## 二、规则策略设计

### 策略 1：三方赔率偏差分析（Triple Odds Divergence）

**原理**：同时对比三个独立概率来源，当多方形成共识且与 Polymarket 存在偏差时下注。三方数据互相校验，比单一对比更可靠。

```
三方概率来源：
  P_poly  = Polymarket YES_price              (市场预测)
  P_book  = 1 / pinnacle_odds (去 overround)  (博彩公司)
  P_ai    = Claude 分析输出的概率              (AI 预测)

共识偏差计算：
  book_ai_avg     = (P_book + P_ai) / 2       (博彩+AI 共识概率)
  consensus_delta = book_ai_avg - P_poly       (共识 vs Polymarket 偏差)
  book_ai_agree   = |P_book - P_ai| < 8%      (两方是否一致)

下注逻辑：
  IF consensus_delta > +5% AND book_ai_agree:
      → BUY YES（博彩+AI 共识认为 Polymarket 低估）
      → 置信度 = min(consensus_delta / 15%, 1.0)

  IF consensus_delta < -5% AND book_ai_agree:
      → BUY NO（博彩+AI 共识认为 Polymarket 高估）
      → 置信度 = min(|consensus_delta| / 15%, 1.0)

  IF NOT book_ai_agree:
      → NO BET（三方分歧大，不下注）

仓位大小：
  base_size * 置信度 * kelly_fraction
```

**可视化**：三方概率雷达图/柱状对比图，一眼看出哪方偏离

| 对比场景 | Polymarket | Pinnacle | AI 预测 | 信号 |
|---------|-----------|----------|---------|------|
| 共识做多 | 35% | 42% | 45% | BUY YES ✅ |
| 共识做空 | 60% | 48% | 50% | BUY NO ✅ |
| 三方分歧 | 40% | 35% | 50% | 不下注 ⚠️ |
| 无偏差   | 42% | 44% | 43% | 不下注 — |

**优势**：
- 三方交叉验证大幅降低假信号（单一来源偏差可能是噪声，三方共识是强信号）
- AI 提供了博彩公司无法捕捉的"软信息"维度
- 当博彩公司和 AI 意见分歧时自动回避，控制风险

**风险**：
- AI 概率本身需要校准（calibration），初期可能系统性偏高或偏低
- 三方全部一致的信号可能较少，交易频率低

### 策略 2：资金流 / 成交量异动（Volume Spike）

**原理**：监控 Polymarket 市场的交易量和价格变动速率，检测异常资金流入。

```
volume_ma  = 过去 24h 平均成交量
current_vol = 最近 1h 成交量

IF current_vol > volume_ma * 3 AND price_change > 5%:
    → 跟随方向 BUY（smart money 信号）
IF current_vol > volume_ma * 3 AND price_change < -5%:
    → 反向操作（可能是恐慌抛售，做均值回归）
```

**数据源**：Polymarket Gamma API (市场数据) + CLOB API (订单簿)
**优势**：利用 Polymarket 自身数据，不依赖外部 API
**风险**：体育市场可能因伤病/阵容公布等新闻导致合理的大幅波动

### 策略 3：赛前赔率收敛（Closing Line Value）

**原理**：追踪从赛前 48h 到开赛前的赔率变动趋势。研究表明，收盘线（开赛前最后赔率）是最准确的概率估计。如果某方向持续获得资金流入导致价格上升，提前跟进。

```
price_48h_ago = 48 小时前价格
price_current = 当前价格
trend         = (price_current - price_48h_ago) / price_48h_ago

IF trend > +8% AND 距离开赛 > 6h:
    → BUY（趋势跟踪，赶在收盘前）
IF 持仓中 AND 距离开赛 < 1h:
    → 如果仍有利润则持有到结算，否则平仓
```

**数据源**：Polymarket CLOB API 价格历史
**优势**：CLV（Closing Line Value）是衡量投注者水平的黄金标准
**风险**：需要持续采集价格数据建立历史库

### 策略 4：AI 大模型赛事分析（LLM Match Analyst）

**原理**：将赛事相关的结构化数据（球队战绩、伤停、近期状态、交锋记录、赔率变动）和非结构化信息（新闻、教练言论）输入 LLM，输出结构化的赛事预测。

**工作流程**：
```
1. 数据采集层 → 自动聚合每场比赛的上下文：
   - 两队近 5 场战绩 + 进失球
   - 关键伤停/停赛球员
   - 主客场战绩
   - 历史交锋记录（近 5 次）
   - Polymarket 当前赔率 + 主流博彩赔率
   - 联赛排名和积分情况

2. Prompt 工程 → 结构化 prompt 模板：
   """
   你是一位专业足球分析师。请分析以下比赛并给出预测。

   比赛：{home_team} vs {away_team}
   联赛：{league}，第 {round} 轮
   日期：{date}

   [主队数据]
   近 5 场：{home_recent_5}
   联赛排名：{home_rank}，积分：{home_points}
   主场战绩：{home_record}
   关键缺阵：{home_injuries}

   [客队数据]
   近 5 场：{away_recent_5}
   联赛排名：{away_rank}，积分：{away_points}
   客场战绩：{away_record}
   关键缺阵：{away_injuries}

   [历史交锋] 近 5 次：{h2h}

   [赔率]
   Polymarket: 主胜 {pm_home}% / 平 {pm_draw}% / 客胜 {pm_away}%
   Pinnacle:   主胜 {pin_home}% / 平 {pin_draw}% / 客胜 {pin_away}%

   请输出 JSON 格式：
   {
     "prediction": "HOME_WIN|DRAW|AWAY_WIN",
     "confidence": 0.0-1.0,
     "probabilities": {
       "home_win": 0.xx,
       "draw": 0.xx,
       "away_win": 0.xx
     },
     "implied_odds": {
       "home_win": x.xx,    // 1 / home_win_prob，AI 预测赔率
       "draw": x.xx,
       "away_win": x.xx
     },
     "vs_polymarket": {
       "most_undervalued": "HOME_WIN|DRAW|AWAY_WIN",
       "divergence_pct": x.x,
       "recommendation": "BUY_YES|BUY_NO|NO_BET"
     },
     "key_factors": ["factor1", "factor2", ...],
     "reasoning": "简要分析"
   }
   """

3. 三方对比 →
   AI 输出的概率直接作为三方赔率对比中的第三方数据源
   与 Polymarket 价格 + Pinnacle 赔率 一起输入策略 1（Triple Odds Divergence）
   当三方中两方以上形成共识且与第三方偏差 > 5% 时生成信号
```

**模型选择**：
- 首选 Claude API（Sonnet 4.6 性价比最优，~$3/M input tokens）
- 备选 GPT-4o / DeepSeek
- 每场分析成本约 $0.01-0.03（一次 prompt ~2K tokens）
- 每天五大联赛 ~10 场比赛，月成本 < $10

**优势**：
- 能整合非结构化信息（伤病新闻、教练战术变化等）
- 输出可解释的推理过程，辅助人工决策
- 可以捕捉规则策略难以量化的"软因素"（球队士气、关键赛事动机等）

**风险**：
- LLM 对体育预测没有真正的"专业能力"，本质是对输入数据的综合推理
- 容易产生过度自信的预测（需要校准 confidence 分数）
- 不应单独作为下注依据，必须与规则策略交叉验证

---

## 三、系统架构

```
┌─────────────────────────────────────────────────────┐
│                    React Frontend                    │
│  (Dashboard / Markets / Signals / AI Analysis / Portfolio) │
└──────────────────────┬──────────────────────────────┘
                       │ REST API + WebSocket
┌──────────────────────▼──────────────────────────────┐
│                 FastAPI Backend                       │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Market   │ │ Strategy │ │   AI    │ │Execution│  │
│  │ Scanner  │ │ Engine   │ │ Analyst │ │ Manager │  │
│  └────┬─────┘ └────┬─────┘ └────┬────┘ └────┬────┘  │
│       │             │            │            │       │
│  ┌────▼─────────────▼────────────▼────────────▼───┐  │
│  │            Data Layer (SQLite/PG)              │  │
│  │  markets | prices | signals | ai_reports | pos │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
     │                │                    │
┌────▼────┐    ┌──────▼──────┐      ┌──────▼──────┐
│Polymarket│    │  Odds APIs  │      │ Claude API  │
│CLOB+Gamma│    │(Odds API/   │      │ (Sonnet 4.6)│
│  API     │    │ fd.co.uk)   │      │             │
└─────────┘    └─────────────┘      └─────────────┘
```

### 3.1 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 后端 | Python 3.11 + FastAPI | 生态好，py-clob-client 官方 SDK |
| 前端 | React + Vite + TailwindCSS | 轻量，V1 只做几个页面 |
| 数据库 | SQLite (V1) → PostgreSQL (V2) | V1 无需复杂部署 |
| 任务调度 | APScheduler | 定时采集价格、运行策略 |
| AI 分析 | Anthropic SDK (Claude Sonnet 4.6) | 结构化赛事分析，$0.01/场 |
| Polymarket SDK | py-clob-client | 官方 Python SDK |
| 部署 | Docker + Railway / VPS | 简单一键部署 |

### 3.2 核心模块

**1. Market Scanner（市场扫描器）**
- 每 5 分钟调用 Gamma API 扫描足球相关市场
- 过滤条件：tag=soccer, 活跃市场, 流动性 > 阈值
- 存储市场元数据（condition_id, token_ids, 赛事信息）

**2. Price Collector（价格采集器）**
- 每 1 分钟采集关注市场的 mid price / bid-ask spread
- 存储时序价格数据，用于趋势分析和策略计算
- 通过 WebSocket 实时更新订单簿快照

**3. Odds Fetcher（外部赔率获取）**
- 调用 The Odds API 获取 Pinnacle/Bet365 赔率
- 赛事匹配：通过队名 + 日期模糊匹配 Polymarket 市场
- 计算去除 overround 的真实隐含概率

**4. Strategy Engine（策略引擎）**
- 每个策略实现统一接口：`evaluate(market, context) -> Signal`
- Signal 包含：方向(BUY_YES/BUY_NO)、置信度(0-1)、建议仓位
- 多策略信号聚合：加权投票

**5. Execution Manager（执行管理器）**
- V1：生成信号后推送到前端，用户手动确认后执行
- 通过 CLOB API 下单（GTC 限价单为主）
- 仓位管理：单市场最大仓位限制、总仓位限制

---

## 四、数据源方案

| 数据 | 推荐方案 | 备选 | 成本 |
|------|---------|------|------|
| Polymarket 市场 | Gamma API | — | 免费 |
| Polymarket 交易 | CLOB API + WebSocket | — | 免费 |
| 实时赔率 | The Odds API (免费 tier) | API-Football ($19/mo) | $0-19/mo |
| 历史赔率 | football-data.co.uk CSV | The Odds API 历史端点 | 免费 |
| 赛程/结果 | football-data.org (免费) | API-Football | 免费 |
| 球队统计 | FBref (免费爬取) | Understat (xG) | 免费 |
| 世界杯数据 | Sportmonks ($39/mo) | football-data.org | $0-39/mo |
| AI 分析 | Claude API (Sonnet 4.6) | GPT-4o / DeepSeek | ~$10/mo |

**V1 总成本：~$10/月**（免费数据源 + Claude API 按量付费）

---

## 五、Polymarket 技术要点

### 5.1 交易机制
- 基于 Polygon 链上结算，USDC.e 计价
- 使用 Gnosis 条件代币框架：每个市场一对 YES/NO 代币
- YES + NO 总价 = $1 USDC（获胜代币兑 $1，失败代币归零）

### 5.2 费用
- **大多数足球市场：0 手续费**
- Serie A 和 NCAAB 有费用：最高 0.44% (50% 概率时)
- Maker 有 25% 手续费返还
- 建议策略以 GTC 限价单为主（做 Maker 而非 Taker）

### 5.3 API 限制
- 下单：50/秒 burst，3000/10min sustained
- 查询订单簿：300/10s
- 查询价格：100/10s
- 对于非高频策略完全足够

### 5.4 认证
- L1 (EIP-712)：私钥签名获取凭证
- L2 (HMAC-SHA256)：后续交易请求使用派生的 API Key
- 需要 Polygon 上的 USDC.e 作为资金

---

## 六、可行性分析

### 6.1 技术可行性 ✅

| 方面 | 评估 |
|------|------|
| API 可用性 | Polymarket 有完善的 CLOB + Gamma API，官方 Python SDK |
| 数据获取 | 足球数据源丰富，免费选项多 |
| 市场覆盖 | 五大联赛 + 欧冠 + 世界杯在 Polymarket 上都有充足市场 |
| 开发周期 | V1 MVP 预估 2-3 周可完成（后端 + 简单前端） |

### 6.2 策略可行性 ⚠️

| 方面 | 评估 |
|------|------|
| 赔率偏差策略 | **中等可行**。Polymarket 流动性不如传统博彩公司，存在定价效率差距可被利用。但偏差可能迅速收敛 |
| 成交量异动策略 | **可行性较低**。体育市场不如政治/加密市场活跃，信号可能稀少 |
| CLV 策略 | **较有前景**。学术研究已证实 CLV 是有效的盈利指标，关键在于足够早地捕捉趋势 |
| 整体 edge | Polymarket 体育市场效率低于 Pinnacle 等顶级博彩公司，**存在 alpha 空间但不大**。年化收益率预期 5-15%（扣除资金成本后） |

### 6.3 商业可行性 ⚠️

| 方面 | 评估 |
|------|------|
| 市场规模 | Polymarket 体育市场 ~1,485 个活跃足球市场，世界杯冠军盘 $3.3 亿量 |
| 流动性 | 头部赛事（EPL/UCL/世界杯）流动性尚可，小联赛市场可能滑点大 |
| 竞争 | 目前 Polymarket 体育领域的量化竞争者不多，但正在增加 |
| 监管 | Polymarket 已获 CFTC 批准，合法合规。但需注意所在地区法律 |
| 资金门槛 | 最低 $500-1000 USDC 即可开始；建议 $5000+ 以覆盖手续费和分散风险 |

### 6.4 风险因素

1. **流动性风险**：小市场买卖价差大，实际成交价可能偏离信号价
2. **赛事匹配风险**：Polymarket 市场名称与外部数据源的赛事匹配可能不精确
3. **结算风险**：Polymarket 结算依赖 UMA 预言机，极端情况下可能有争议
4. **资金效率**：资金锁定在 Polygon 上直到结算，世界杯长线投注资金周转慢
5. **监管风险**：需确认自身所在司法管辖区是否允许使用 Polymarket

---

## 七、开发路线图

### Phase 1: MVP（2 周）
- [ ] 项目脚手架：FastAPI + React + SQLite
- [ ] Polymarket 市场扫描（Gamma API 集成）
- [ ] 价格采集与存储（定时任务）
- [ ] 赔率偏差策略 V1（对接 The Odds API）
- [ ] AI 赛事分析模块（Claude API 集成 + Prompt 模板）
- [ ] 简单 Web 仪表盘（市场列表 + 信号 + AI 分析报告展示）
- [ ] 手动下注确认流程

### Phase 2: 策略增强（2 周）
- [ ] 成交量异动策略
- [ ] CLV 趋势策略
- [ ] AI 分析与规则策略融合信号系统
- [ ] 历史赔率回测框架
- [ ] 仓位管理和风控模块
- [ ] 通知系统（Telegram/Discord bot）

### Phase 3: 世界杯版（2026.5 — 2026.6）
- [ ] 世界杯市场专属扫描和展示
- [ ] 大赛策略调整（48 队新赛制适配）
- [ ] 小组赛 → 淘汰赛的动态概率模型
- [ ] 半自动下注模式
- [ ] 完整 Web 平台 UI

### Phase 4: 迭代优化（2026.7+）
- [ ] ML 模型集成（xG + ELO 特征）
- [ ] 更多赛事覆盖
- [ ] 多用户支持 + 权限系统
- [ ] 策略绩效分析面板

---

## 八、项目结构（V1）

```
polyedge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── market.py
│   │   │   ├── price.py
│   │   │   ├── signal.py
│   │   │   └── position.py
│   │   ├── services/
│   │   │   ├── polymarket.py    # Gamma + CLOB API 封装
│   │   │   ├── odds_fetcher.py  # 外部赔率获取
│   │   │   └── scheduler.py     # 定时任务
│   │   ├── ai/
│   │   │   ├── analyst.py       # LLM 赛事分析核心
│   │   │   ├── prompts.py       # Prompt 模板
│   │   │   └── data_assembler.py # 赛事上下文数据组装
│   │   ├── strategies/
│   │   │   ├── base.py          # 策略基类
│   │   │   ├── odds_divergence.py
│   │   │   ├── volume_spike.py
│   │   │   ├── clv_trend.py
│   │   │   └── ai_signal.py     # AI 分析信号转换
│   │   ├── execution/
│   │   │   └── order_manager.py # 下单管理
│   │   └── api/
│   │       ├── markets.py       # 市场相关接口
│   │       ├── signals.py       # 信号相关接口
│   │       └── portfolio.py     # 持仓相关接口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # 主仪表盘
│   │   │   ├── Markets.tsx      # 市场列表
│   │   │   ├── Analysis.tsx     # AI 分析报告
│   │   │   └── Signals.tsx      # 信号列表
│   │   ├── components/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

---

## 九、验证方式

1. **功能验证**：启动 dev server，确认市场扫描、价格采集、信号生成全链路通畅
2. **策略验证**：用 football-data.co.uk 历史数据回测赔率偏差策略，计算 ROI 和胜率
3. **交易验证**：先在 Polymarket testnet 验证下单流程，再切换 mainnet 小额测试
4. **前端验证**：preview tools 检查仪表盘展示和交互
