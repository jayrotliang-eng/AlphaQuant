
import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class AIAnalyzer:
    """
    AI 分析器（自动切换模式）
    优先级：OpenRouter → Groq → 规则兜底
    """

    def __init__(self):
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")

    def analyze(self, stock_data, fundamentals=None, news=None):
        """
        分析单支股票，返回标准格式结果
        """
        symbol = stock_data.get("Symbol", stock_data.get("symbol", "UNKNOWN"))

        # 构建 prompt
        prompt = self._build_prompt(stock_data, fundamentals, news)

        # 尝试顺序：OpenRouter → Groq → 规则兜底
        result = None

        # 1. 尝试 OpenRouter
        if self.openrouter_key:
            result = self._call_openrouter(prompt, symbol)

        # 2. 尝试 Groq
        if result is None and self.groq_key:
            result = self._call_groq(prompt, symbol)

        # 3. 规则兜底
        if result is None:
            result = self._rule_based_analysis(stock_data, fundamentals, news)

        return result

    def _build_prompt(self, stock_data, fundamentals=None, news=None):
        """构建 AI 分析 prompt（含技术面 + 基本面 + 新闻）"""
        symbol = stock_data.get("Symbol", stock_data.get("symbol", "UNKNOWN"))
        price = float(float(stock_data.get("Close", 0) or stock_data.get("price", 0) or 0) or stock_data.get("close", 0) or stock_data.get("现价", 0) or 0)
        score = stock_data.get("Score", stock_data.get("score", 0))
        rsi = stock_data.get("rsi", 0)
        macd = stock_data.get("macd", 0)
        adx = stock_data.get("ADX", stock_data.get("adx", 0))
        atr = stock_data.get("ATR_%", stock_data.get("atr", 0))
        trend = stock_data.get("trend", "未知")

        prompt = f"""你是专业股票分析师。请分析以下股票并给出投资建议。

## 股票: {symbol}
- 当前价格: ${price}
- 技术评分: {score}/100
- RSI: {rsi}
- MACD: {macd}
- ADX: {adx}
- ATR: {atr}
- 趋势: {trend}
"""

        if fundamentals:
            prompt += f"""
## 基本面数据:
{str(fundamentals)[:300]}
"""

        if news:
            prompt += f"""
## 最近新闻/市场情绪:
{str(news)[:500]}
"""

        prompt += """
## 请用以下 JSON 格式回答（不要加任何其他文字）:
{
    "rating": "买入/观望/卖出",
    "confidence": 0-100 的数字,
    "entry": "建议买入价（数字）",
    "stop_loss": "止损价（数字）",
    "hold_period": "建议持有天数（数字）",
    "reason": "50字内的分析理由"
}
"""
        return prompt

    def _call_openrouter(self, prompt, symbol):
        """尝试 OpenRouter"""
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key
            )
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct:free",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            content = response.choices[0].message.content
            result = self._parse_json(content)
            if result:
                result["分析来源"] = "OpenRouter"
                return result
        except Exception as e:
            error_msg = str(e)
            if "402" in error_msg or "insufficient" in error_msg.lower():
                print(f"   ⚠️ OpenRouter 额度不足，切换到 Groq...")
            else:
                print(f"   ⚠️ OpenRouter 错误: {error_msg[:50]}")
        return None

    def _call_groq(self, prompt, symbol):
        """尝试 Groq（使用 compound-beta 模型）"""
        try:
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=self.groq_key
            )
            response = client.chat.completions.create(
                model="compound-beta",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )

            # compound-beta 返回格式可能非标准，尝试多种方式读取
            content = None
            try:
                # 标准格式
                content = response.choices[0].message.content
            except (AttributeError, TypeError, IndexError):
                try:
                    # 嵌套 list 格式
                    choices = response.choices
                    if isinstance(choices, list) and len(choices) > 0:
                        first = choices[0]
                        if isinstance(first, list) and len(first) > 0:
                            first = first[0]
                        if hasattr(first, 'message'):
                            content = first.message.content
                        elif isinstance(first, dict):
                            content = first.get('message', {}).get('content', '')
                except Exception:
                    pass

            if content:
                result = self._parse_json(content)
                if result:
                    result["分析来源"] = "Groq"
                    time.sleep(3)  # 防止频率限制
                    return result

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate" in error_msg.lower():
                print(f"   ⚠️ Groq 频率限制，等待...")
                time.sleep(15)
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                print(f"   ⚠️ Groq 模型不可用")
            else:
                print(f"   ⚠️ Groq 错误: {error_msg[:50]}")
        return None

    def _parse_json(self, content):
        """从 AI 回复中解析 JSON"""
        if not content:
            return None
        try:
            # 尝试直接解析
            result = json.loads(content)
            return self._validate_result(result)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        try:
            if "```" in content:
                json_str = content.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                result = json.loads(json_str.strip())
                return self._validate_result(result)
        except (json.JSONDecodeError, IndexError):
            pass

        # 尝试找 { } 包裹的部分
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                return self._validate_result(result)
        except json.JSONDecodeError:
            pass

        return None

    def _validate_result(self, result):
        """验证并标准化 AI 返回的结果"""
        if not isinstance(result, dict):
            return None

        # 标准化 key（支持中英文）
        standardized = {}
        
        # rating（建议）
        standardized["rating"] = (
            result.get("rating") or 
            result.get("建议") or 
            "观望"
        )
        
        # confidence（信心）
        conf = result.get("confidence") or result.get("信心") or 50
        try:
            standardized["confidence"] = int(float(str(conf).replace("%", "")))
        except (ValueError, TypeError):
            standardized["confidence"] = 50

        # entry（买入价）
        entry = result.get("entry") or result.get("目标价") or result.get("建议买入价") or "N/A"
        standardized["entry"] = str(entry).replace("$", "").strip()

        # stop_loss（止损价）
        stop = result.get("stop_loss") or result.get("止损价") or result.get("止损") or "N/A"
        standardized["stop_loss"] = str(stop).replace("$", "").strip()

        # hold_period（持有天数）
        hold = result.get("hold_period") or result.get("持有天数") or result.get("建议持有") or "N/A"
        standardized["hold_period"] = str(hold).replace("天", "").strip()

        # reason（理由）
        standardized["reason"] = (
            result.get("reason") or 
            result.get("理由") or 
            result.get("分析理由") or 
            "AI 综合分析"
        )

        # 补充 main.py 需要的其他 key
        standardized["risk"] = "中"
        # target 保持原值不覆盖
        standardized["timeframe"] = standardized.get("hold_period", "5-10")
        standardized["technical_view"] = standardized.get("reason", "")
        standardized["fundamental_view"] = ""
        standardized["news_view"] = ""
        standardized["summary"] = standardized.get("reason", "综合分析")
        standardized["source"] = result.get("分析来源", result.get("source", "规则"))
        standardized["target"] = str(result.get("target", result.get("目标价", "N/A"))).replace("$", "").strip()
        # Fallback: 如果 target 是 N/A，用 entry * 1.05
        if standardized.get("target") in [None, "N\/A", "", "0"]:
            try:
                entry_val = float(standardized.get("entry", 0))
                if entry_val > 0:
                    standardized["target"] = f"{entry_val * 1.05:.2f}"
            except:
                pass
        standardized["action"] = standardized.get("rating", "观望")

        return standardized

    def _rule_based_analysis(self, stock_data, fundamentals=None, news=None):
        """规则兜底（强化版 - 技术面 + 基本面 + 新闻综合判断）"""
        symbol = stock_data.get("Symbol", stock_data.get("symbol", "UNKNOWN"))
        price = float(float(stock_data.get("Close", 0) or stock_data.get("price", 0) or 0))
        score = float(stock_data.get("Score", stock_data.get("score", 0)))
        rsi = float(stock_data.get("RSI", stock_data.get("rsi", 50)))
        adx = float(stock_data.get("ADX", stock_data.get("adx", 0)))
        atr = float(stock_data.get("ATR_%", stock_data.get("atr", 0)))
        trend = stock_data.get("Trend", stock_data.get("trend", ""))

        # ===== 技术面评分 =====
        tech_score = 0
        reasons = []

        # RSI 判断
        if rsi < 30:
            tech_score += 20
            reasons.append("RSI 超卖")
        elif rsi < 45:
            tech_score += 10
            reasons.append("RSI 偏低")
        elif rsi > 70:
            tech_score -= 20
            reasons.append("RSI 超买")
        elif rsi > 55:
            tech_score += 5

        # 趋势判断
        if "上涨" in str(trend) or "up" in str(trend).lower():
            tech_score += 20
            reasons.append("趋势向上")
        elif "下跌" in str(trend) or "down" in str(trend).lower():
            tech_score -= 20
            reasons.append("趋势向下")

        # ADX 判断
        if adx > 25:
            tech_score += 10
            reasons.append("趋势强劲")

        # 综合评分
        if score >= 80:
            tech_score += 20
            reasons.append("技术评分高")
        elif score >= 60:
            tech_score += 10

        # ===== 基本面加分 =====
        fundamental_score = 0
        if fundamentals and isinstance(fundamentals, dict):
            pe = fundamentals.get("pe_ratio") or fundamentals.get("PE")
            revenue_growth = fundamentals.get("revenue_growth") or fundamentals.get("营收成长")
            
            if pe and pe != "N/A":
                try:
                    pe_val = float(str(pe).replace("%", ""))
                    if 5 < pe_val < 20:
                        fundamental_score += 15
                        reasons.append("估值合理")
                    elif pe_val > 50:
                        fundamental_score -= 10
                        reasons.append("估值偏高")
                except (ValueError, TypeError):
                    pass

            if revenue_growth and revenue_growth != "N/A":
                try:
                    growth_val = float(str(revenue_growth).replace("%", "").replace("+", ""))
                    if growth_val > 20:
                        fundamental_score += 15
                        reasons.append("高速成长")
                    elif growth_val > 10:
                        fundamental_score += 10
                        reasons.append("稳定成长")
                except (ValueError, TypeError):
                    pass

        # ===== 新闻加分 =====
        news_score = 0
        if news and isinstance(news, dict):
            sentiment = news.get("sentiment") or news.get("情绪")
            if sentiment:
                sentiment_str = str(sentiment).lower()
                if "正面" in sentiment_str or "positive" in sentiment_str or "bullish" in sentiment_str:
                    news_score += 10
                    reasons.append("新闻正面")
                elif "负面" in sentiment_str or "negative" in sentiment_str or "bearish" in sentiment_str:
                    news_score -= 10
                    reasons.append("新闻负面")

        # ===== 综合判断 =====
        total_score = tech_score + fundamental_score + news_score

        if total_score >= 30:
            rating = "买入"
            confidence = min(85, 60 + total_score)
        elif total_score >= 10:
            rating = "观望（偏多）"
            confidence = min(70, 50 + total_score)
        elif total_score <= -20:
            rating = "卖出"
            confidence = min(80, 50 + abs(total_score))
        else:
            rating = "观望"
            confidence = 50

        # 计算目标价和止损价
        atr_val = atr if atr > 0 else price * 0.02
        entry = f"{price * 0.99:.2f}"  # 建议在当前价下方 1% 买入
        stop_loss = f"{price - (atr_val * 2):.2f}"  # 止损: 2倍 ATR
        target = f"{price + (atr_val * 3):.2f}"  # 目标: 3倍 ATR

        reason = "；".join(reasons[:3]) if reasons else f"{symbol}（数据不足）"

        target = f"{price + (atr_val * 3):.2f}"

        return {
            "rating": rating,
            "confidence": confidence,
            "entry": entry,
            "stop_loss": stop_loss,
            "hold_period": "5-10",
            "target": target,
            "risk": "中" if total_score >= 0 else "高",
            "timeframe": "5-10天",
            "technical_view": reason,
            "fundamental_view": "基本面正常" if fundamental_score >= 0 else "基本面偏弱",
            "news_view": "新闻正面" if news_score > 0 else ("新闻负面" if news_score < 0 else "新闻中性"),
            "summary": reason,
            "action": rating,
            "reason": reason,
            "分析来源": "规则"
        }

