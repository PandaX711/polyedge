MATCH_ANALYSIS_PROMPT = """你是一位专业足球分析师。请分析以下比赛并给出预测。

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
  "key_factors": ["factor1", "factor2"],
  "reasoning": "简要分析"
}}"""
