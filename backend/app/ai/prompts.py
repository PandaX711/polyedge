MATCH_ANALYSIS_PROMPT = """你是一位专业足球分析师，同时具备预测市场交易经验。请分析以下比赛并给出预测。

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

[传统博彩赔率]
Pinnacle: 主胜 {pin_home}% / 平 {pin_draw}% / 客胜 {pin_away}%

[Polymarket 交易数据]
当前隐含概率: 主胜 {pm_home}% / 平 {pm_draw}% / 客胜 {pm_away}%
买卖价差: {pm_spread}
24h 价格变动: {pm_price_change}
近 1h 成交量: ${pm_volume_1h}
24h 平均成交量: ${pm_volume_avg}
成交量异常倍数: {pm_volume_ratio}x

分析要求：
1. 结合球队实力、近期状态和赔率数据给出你的独立概率判断
2. 你的 probabilities 三项之和必须等于 1.0
3. 特别关注 Polymarket 价格与 Pinnacle 的偏差，判断是否存在套利机会
4. 如果成交量异常（>3x），分析资金流向可能代表的含义

请输出 JSON 格式（不要包含 markdown 代码块标记）：
{{
  "prediction": "HOME_WIN|DRAW|AWAY_WIN",
  "confidence": 0.0-1.0,
  "probabilities": {{
    "home_win": 0.xx,
    "draw": 0.xx,
    "away_win": 0.xx
  }},
  "implied_odds": {{
    "home_win": x.xx,
    "draw": x.xx,
    "away_win": x.xx
  }},
  "vs_polymarket": {{
    "most_undervalued": "HOME_WIN|DRAW|AWAY_WIN",
    "divergence_pct": x.x,
    "recommendation": "BUY_YES|BUY_NO|NO_BET"
  }},
  "market_signals": {{
    "volume_anomaly": true|false,
    "smart_money_direction": "HOME|AWAY|DRAW|UNCLEAR",
    "spread_concern": true|false
  }},
  "key_factors": ["factor1", "factor2", "factor3"],
  "reasoning": "简要分析（包含市场信号解读）"
}}"""


WC_WINNER_ANALYSIS_PROMPT = """你是一位专业足球分析师和预测市场交易专家。请分析 2026 FIFA 世界杯夺冠形势。

赛事信息：2026 FIFA World Cup | 美国/加拿大/墨西哥 | 48 队
分析日期：{date}

[Polymarket 当前夺冠概率 (Top {top_n} 球队)]
{team_odds_table}

[Polymarket 市场数据]
总交易量: ${total_volume}
总流动性: ${total_liquidity}
概率总和: {prob_sum}% (理论应为 100%，差异反映市场溢价)

分析要求：
1. 基于你的足球知识，给出你认为最被低估和最被高估的 3 支球队
2. 你的概率调整必须有具体理由（教练变更、伤病、小组签运等）
3. 关注概率总和 - 如果远超 100%，说明市场溢价较高

请输出 JSON 格式（不要包含 markdown 代码块标记）：
{{
  "most_undervalued": [
    {{"team": "xxx", "polymarket_pct": x.x, "fair_pct": x.x, "edge_pct": x.x, "reason": "..."}}
  ],
  "most_overvalued": [
    {{"team": "xxx", "polymarket_pct": x.x, "fair_pct": x.x, "edge_pct": x.x, "reason": "..."}}
  ],
  "dark_horses": [
    {{"team": "xxx", "polymarket_pct": x.x, "fair_pct": x.x, "reason": "..."}}
  ],
  "top_recommendation": {{
    "team": "xxx",
    "action": "BUY_YES|BUY_NO",
    "edge_pct": x.x,
    "confidence": 0.0-1.0,
    "reasoning": "..."
  }},
  "market_overview": "整体市场分析"
}}"""
