
import os
import json
from openai import OpenAI


class AIAnalyzer:

    def __init__(self):

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def analyze(self, row, fundamentals=None, news=None):
        """
        综合技术面 + 基本面 + 新闻情绪，给出最终建议
        """

        # 基本面信息
        fund_info = ""
        if fundamentals:
            fund_info = f"""
基本面数据:
- 行业: {fundamentals.get('sector', 'N/A')} / {fundamentals.get('industry', 'N/A')}
- 市值: {fundamentals.get('market_cap', 'N/A')}
- 本益比(PE): {fundamentals.get('pe_ratio', 'N/A')}
- 营收成长: {fundamentals.get('revenue_growth', 'N/A')}
- 利润率: {fundamentals.get('profit_margin', 'N/A')}
- 负债比: {fundamentals.get('debt_to_equity', 'N/A')}
- 估值判断: {fundamentals.get('valuation', 'N/A')}
- 成长性: {fundamentals.get('growth', 'N/A')}
- 财务健康: {fundamentals.get('health', 'N/A')}
"""

        # 新闻信息
        news_info = ""
        if news:
            news_info = f"""
新闻/情绪:
- 情绪: {news.get('sentiment', 'N/A')}
- 关键事件: {news.get('key_events', 'N/A')}
- 风险因素: {news.get('risk_factors', 'N/A')}
- 上涨催化剂: {news.get('catalyst', 'N/A')}
- 新闻评分: {news.get('news_score', 'N/A')}/10
"""

        prompt = f"""你是一位专业但说话简单易懂的股票分析师。
请综合「技术面 + 基本面 + 新闻情绪」三方面，给出最终建议。

股票: {row['Symbol']}
现价: ${row['Close']}

技术面数据:
- 综合评分: {row['Score']}/100
- 趋势: {row.get('Trend', 'N/A')}
- 动能: {row.get('Momentum', 'N/A')}
- 是否突破: {row.get('Breakout', 'N/A')}
{fund_info}
{news_info}

请用 JSON 格式回答：

{{
    "rating": "Strong Buy / Buy / Hold / Sell / Strong Sell（五选一）",
    "confidence": 0-100 的数字,
    "risk": "低风险 / 中风险 / 高风险（三选一）",
    "entry": 建议买入价格（数字）,
    "stoploss": 止损价格（数字）,
    "target": 目标价格（数字）,
    "timeframe": "短线(1-5天) / 波段(1-4周) / 中线(1-3月)（三选一）",
    "technical_view": "技术面一句话评价",
    "fundamental_view": "基本面一句话评价",
    "news_view": "新闻面一句话评价",
    "summary": "综合一句话总结（最简单的中文，告诉小白该怎么做）",
    "action": "具体操作建议（例如：现在可以买入，止损 $XX，目标 $XX，预计持有 X 周）"
}}

要求：
1. 所有中文描述都要简单易懂，不要专业术语
2. 价格必须是数字
3. 如果三方面有矛盾（例如技术面好但基本面差），要在 summary 里提醒
4. 只回传 JSON
"""

        try:

            response = self.client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是股票分析师，只回传 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )

            content = response.choices[0].message.content.strip()

            # 清理 markdown 格式
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0]

            analysis = json.loads(content)
            return analysis

        except Exception as e:
            return {
                "rating": "N/A",
                "confidence": 0,
                "risk": "未知",
                "entry": "N/A",
                "stoploss": "N/A",
                "target": "N/A",
                "timeframe": "N/A",
                "technical_view": "N/A",
                "fundamental_view": "N/A",
                "news_view": "N/A",
                "summary": f"分析失败: {str(e)[:50]}",
                "action": "暂时观望"
            }

