
import os
import json
from openai import OpenAI


class AIAnalyzer:

    def __init__(self):

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def analyze(self, row):
        """
        用 AI 分析单支股票，返回白话中文建议
        """

        prompt = f"""你是一位专业但说话简单易懂的股票分析师。
请用「金融小白也能看懂」的方式分析这支股票。

股票: {row['Symbol']}
现价: ${row['Close']}
综合评分: {row['Score']}/100
趋势: {row.get('Trend', 'N/A')}
动能: {row.get('Momentum', 'N/A')}
是否突破: {row.get('Breakout', 'N/A')}

请回答以下内容（用 JSON 格式）：

{{
    "rating": "Strong Buy / Buy / Hold / Sell / Strong Sell（五选一）",
    "confidence": 0-100 的数字（你有多确定）,
    "risk": "低风险 / 中风险 / 高风险（三选一）",
    "entry": 建议买入价格（数字）,
    "stoploss": 止损价格（跌到这里就卖出，数字）,
    "target": 目标价格（涨到这里可以考虑卖出，数字）,
    "summary": "一句话总结，用最简单的中文，告诉小白这支股票现在适不适合买，为什么",
    "action": "具体操作建议，例如：现在可以买入，设好止损在 $XX，目标看 $XX"
}}

要求：
1. summary 和 action 必须用简单中文，不要用专业术语
2. 价格必须是数字，不要加 $ 符号
3. 只回传 JSON，不要其他文字
"""

        try:

            response = self.client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是股票分析师，只回传 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
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
                "summary": f"分析失败: {str(e)[:50]}",
                "action": "暂时观望"
            }

