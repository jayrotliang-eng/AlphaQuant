
import os
import json
from openai import OpenAI


class AIAnalyzer:

    def __init__(self):

        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )

    def analyze(self, row):

        prompt = f"""你是一位专业的量化股票分析师。

请根据以下技术指标分析这支股票，并给出交易建议。

股票代码：{row["Symbol"]}
当前价格：{row["Close"]}
EMA20：{row["EMA20"]}
EMA50：{row["EMA50"]}
EMA200：{row["EMA200"]}
RSI：{row["RSI"]}
MACD：{row["MACD"]}
MACD信号线：{row["MACD_SIGNAL"]}
ADX：{row["ADX"]}
ATR：{row["ATR"]}
趋势：{row["Trend"]}
动量：{row["Momentum"]}
突破：{row["Breakout"]}
成交量信号：{row["VolumeSignal"]}
技术评分：{row["Score"]}

请严格按照以下JSON格式返回（不要输出Markdown、不要加```）：

{{"rating":"Strong Buy/Buy/Hold/Sell/Strong Sell","confidence":0到100的整数,"reason":"用简体中文解释原因，不超过50字","risk":"Low/Moderate/High","entry":"建议买入价格","stoploss":"建议止损价格","target":"建议目标价格","summary":"用简体中文总结，不超过30字"}}

规则：
1. confidence 必须是 0~100 的整数
2. 所有解释一律使用简体中文
3. summary 不超过30个中文字
4. reason 不超过50个中文字
5. entry/stoploss/target 必须是具体数字
"""

        try:

            response = self.client.chat.completions.create(

                model="deepseek/deepseek-chat-v3",

                messages=[
                    {
                        "role": "system",
                        "content": "你是专业量化分析师。只输出纯JSON，不要Markdown格式。所有文字使用简体中文。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.2

            )

            text = response.choices[0].message.content.strip()

            # 清理可能的 Markdown 包裹
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
                text = text.strip()

            return json.loads(text)

        except json.JSONDecodeError:

            return {
                "rating": "Hold",
                "confidence": 0,
                "reason": "AI 返回格式错误",
                "risk": "Unknown",
                "entry": "N/A",
                "stoploss": "N/A",
                "target": "N/A",
                "summary": "分析失败"
            }

        except Exception as e:

            print(f"   ⚠️ AI 分析失败 ({row['Symbol']}): {e}")

            return {
                "rating": "Hold",
                "confidence": 0,
                "reason": str(e),
                "risk": "Unknown",
                "entry": "N/A",
                "stoploss": "N/A",
                "target": "N/A",
                "summary": "分析失败"
            }

