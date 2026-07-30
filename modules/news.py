
import os
import json
from openai import OpenAI


class NewsAnalyzer:
    """
    用 AI 分析最近新闻对股票的影响
    （通过 AI 的训练知识来判断，不需要额外 API）
    """

    def __init__(self):

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def analyze(self, symbol, sector="", industry=""):
        """
        让 AI 根据它的知识，分析该股票的近期情况
        """

        prompt = f"""你是一位金融新闻分析师。
请根据你所知道的信息，分析 {symbol} 这支股票最近的情况。

股票: {symbol}
行业: {sector} / {industry}

请用 JSON 格式回答：

{{
    "sentiment": "正面 / 中性 / 负面（三选一）",
    "key_events": "最近影响这支股票的1-2个关键事件或趋势（简短中文描述，如果不确定就写'无重大事件'）",
    "risk_factors": "目前的主要风险（简短中文描述）",
    "catalyst": "可能推动上涨的因素（简短中文描述）",
    "news_score": 1-10 的数字（10=非常正面，5=中性，1=非常负面）
}}

要求：
1. 如果你不确定最近的具体新闻，就根据行业趋势来判断
2. 只回传 JSON，不要其他文字
3. 所有描述用简单中文
"""

        try:

            response = self.client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是金融新闻分析师，只回传 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
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
                "sentiment": "未知",
                "key_events": "分析失败",
                "risk_factors": "N/A",
                "catalyst": "N/A",
                "news_score": 5
            }

