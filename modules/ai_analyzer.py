
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class AIAnalyzer:
    """
    混合分析器优先级：
    1. OpenRouter（如果有余额）
    2. Groq（免费，稳定）
    3. Together AI（免费 $5 额度）← 新加的！
    4. 纯规则判断（永远兜底）
    """

    def __init__(self):
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.together_key = os.getenv("TOGETHER_API_KEY", "")
        
        # OpenRouter 客户端
        self.openrouter_available = bool(self.openrouter_key)
        if self.openrouter_available:
            try:
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.openrouter_key
                )
            except Exception:
                self.openrouter_available = False

        # Groq 客户端
        self.groq_available = bool(self.groq_key)
        if self.groq_available:
            try:
                self.groq_client = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=self.groq_key
                )
            except Exception:
                self.groq_available = False

        # Together AI 客户端（新加）
        self.together_available = bool(self.together_key)
        if self.together_available:
            try:
                self.together_client = OpenAI(
                    base_url="https://api.together.xyz/v1",
                    api_key=self.together_key
                )
            except Exception:
                self.together_available = False

    def analyze(self, row, fundamentals=None, news=None):
        """分析单支股票 - 按优先级尝试"""
        
        # 1. 先试 OpenRouter
        if self.openrouter_available:
            result = self._call_api(
                self.openrouter_client, 
                "deepseek/deepseek-chat",
                row, fundamentals, news, 
                "OpenRouter"
            )
            if result:
                return result

        # 2. 再试 Groq
        if self.groq_available:
            result = self._call_api(
                self.groq_client,
                "compound-beta",
                row, fundamentals, news,
                "Groq"
            )
            if result:
                return result

        # 3. 再试 Together AI（新加）
        if self.together_available:
            result = self._call_api(
                self.together_client,
                "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                row, fundamentals, news,
                "Together"
            )
            if result:
                return result

        # 4. 最后用纯规则判断
        return self._rule_based_analysis(row, fundamentals, news)

    def _call_api(self, client, model, row, fundamentals, news, source_name):
        """通用 API 调用"""
        ticker = row.get("ticker", row.get("Symbol", "N/A"))
        try:
            price = float(row.get("close", row.get("Close", 0)) or 0)
            score = float(row.get("score", row.get("Score", 0)) or 0)
            rsi = float(row.get("rsi", row.get("RSI", 50)) or 50)
            macd = float(row.get("macd", row.get("MACD", 0)) or 0)
            adx = float(row.get("adx", row.get("ADX", 0)) or 0)

            prompt = f"""分析以下股票并给出投资建议（用中文回答）：
股票: {ticker}
现价: ${price:.2f}
技术评分: {score:.0f}/100
RSI: {rsi:.1f}
MACD: {macd:.4f}
ADX: {adx:.1f}
"""
            if fundamentals:
                prompt += f"基本面: {json.dumps(fundamentals, ensure_ascii=False)}\n"
            if news:
                prompt += f"新闻情绪: {news}\n"

            prompt += """
请返回 JSON 格式：
{"rating":"买入/观望/卖出","confidence":60-95的数字,"reason":"50字以内","entry":"建议买入价","target":"目标价","stop_loss":"止损价","hold_period":"持有周期","risk":"高/中/低","summary":"一句话总结"}
只返回 JSON，不要其他内容。"""

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()
            
            # 清理 markdown 格式
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
                content = content.rsplit("```", 1)[0] if "```" in content else content
                content = content.strip()

            raw = json.loads(content)
            
            # 统一转换成英文 key（不管 AI 返回中文还是英文都能处理）
            result = {
                "rating": raw.get("rating", raw.get("建议", "观望")),
                "confidence": self._parse_confidence(raw.get("confidence", raw.get("信心", 60))),
                "reason": raw.get("reason", raw.get("理由", "AI分析")),
                "entry": str(raw.get("entry", raw.get("目标价", f"{price:.2f}"))),
                "target": str(raw.get("target", raw.get("目标价", f"{price * 1.08:.2f}"))),
                "stop_loss": str(raw.get("stop_loss", raw.get("止损价", f"{price * 0.95:.2f}"))),
                "hold_period": raw.get("hold_period", raw.get("持有周期", "1-2周")),
                "risk": raw.get("risk", raw.get("风险", "中")),
                "summary": raw.get("summary", raw.get("总结", raw.get("reason", raw.get("理由", "AI分析")))),
                "分析来源": source_name
            }
            return result

        except Exception as e:
            error_msg = str(e)
            if "402" in error_msg or "insufficient" in error_msg.lower():
                print(f"   ⚠️ {source_name} 额度用完，尝试下一个")
                if source_name == "OpenRouter":
                    self.openrouter_available = False
                elif source_name == "Groq":
                    self.groq_available = False
                elif source_name == "Together":
                    self.together_available = False
            elif "401" in error_msg or "invalid" in error_msg.lower():
                print(f"   ⚠️ {source_name} Key 无效，尝试下一个")
                if source_name == "OpenRouter":
                    self.openrouter_available = False
                elif source_name == "Groq":
                    self.groq_available = False
                elif source_name == "Together":
                    self.together_available = False
            elif "429" in error_msg or "rate" in error_msg.lower():
                print(f"   ⚠️ {source_name} 频率限制，等待后重试...")
                import time
                time.sleep(5)
                return None
            else:
                print(f"   ⚠️ {source_name} 失败 ({ticker}): {error_msg[:60]}")
            return None

    def _parse_confidence(self, value):
        """把信心值统一转成数字"""
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            if "高" in value:
                return 85
            elif "中" in value:
                return 70
            elif "低" in value:
                return 55
            else:
                try:
                    return int(value)
                except ValueError:
                    return 60
        return 60

    def _rule_based_analysis(self, row, fundamentals=None, news=None):
        """纯规则判断 - 不需要任何 API，100% 免费"""
        try:
            price = float(row.get("close", row.get("Close", 0)) or 0)
            score = float(row.get("score", row.get("Score", 0)) or 0)
            rsi = float(row.get("rsi", row.get("RSI", 50)) or 50)
            macd = float(row.get("macd", row.get("MACD", 0)) or 0)
            adx = float(row.get("adx", row.get("ADX", 0)) or 0)
            sma_20 = float(row.get("sma_20", row.get("SMA_20", price)) or price)
            sma_50 = float(row.get("sma_50", row.get("SMA_50", price)) or price)
            atr = float(row.get("atr", row.get("ATR", 0)) or 0)
        except (ValueError, TypeError):
            price = 0
            score = 0
            rsi = 50
            macd = 0
            adx = 0
            sma_20 = 0
            sma_50 = 0
            atr = 0

        # 判断趋势
        trend_up = price > sma_20 > sma_50 if (price and sma_20 and sma_50) else False
        trend_down = price < sma_20 < sma_50 if (price and sma_20 and sma_50) else False
        strong_momentum = adx > 25 and macd > 0

        # 综合建议
        if score >= 75 and trend_up and rsi < 70:
            rating = "买入"
            confidence = 85 if strong_momentum else 70
            reason = self._generate_buy_reason(rsi, adx, macd, price, sma_20)
        elif score >= 60 and trend_up:
            rating = "买入"
            confidence = 65
            reason = "趋势向上但动能一般，可轻仓参与"
        elif rsi > 75 or (trend_down and macd < 0):
            rating = "卖出"
            confidence = 80 if rsi > 80 else 65
            reason = self._generate_sell_reason(rsi, adx, trend_down)
        elif score < 40 or trend_down:
            rating = "观望"
            confidence = 60
            reason = "趋势不明或偏弱，等待明确信号"
        else:
            rating = "观望"
            confidence = 55
            reason = "信号混合，建议等待突破方向确认"

        # 计算目标价和止损价
        if atr > 0:
            target_price = price + (atr * 2.5)
            stop_loss = price - (atr * 1.5)
        else:
            target_price = price * 1.08
            stop_loss = price * 0.95

        # 加入基本面
        if fundamentals:
            try:
                pe = float(fundamentals.get("pe_ratio", 0) or 0)
            except (ValueError, TypeError):
                pe = 0
            if pe > 0 and pe < 15:
                reason += "；估值偏低"
            elif pe > 40:
                reason += "；估值偏高注意风险"

        return {
            "rating": rating,
            "confidence": confidence,
            "reason": reason,
            "entry": f"{price:.2f}",
            "target": f"{target_price:.2f}",
            "stop_loss": f"{stop_loss:.2f}",
            "hold_period": "1-2周" if rating == "买入" else "观望",
            "risk": "低" if confidence >= 80 else ("中" if confidence >= 60 else "高"),
            "summary": f"{rating}（{reason[:20]}）",
            "分析来源": "规则"
        }

    def _generate_buy_reason(self, rsi, adx, macd, price, sma_20):
        reasons = []
        if adx > 30:
            reasons.append("趋势强劲")
        if macd > 0:
            reasons.append("MACD金叉")
        if rsi < 50:
            reasons.append("RSI低位反弹")
        elif rsi < 65:
            reasons.append("动能充足")
        if price > sma_20:
            reasons.append("站上均线")
        return "，".join(reasons[:3]) if reasons else "多项指标看好"

    def _generate_sell_reason(self, rsi, adx, trend_down):
        reasons = []
        if rsi > 75:
            reasons.append("RSI超买")
        if trend_down:
            reasons.append("趋势转弱")
        if adx > 25:
            reasons.append("下跌动能强")
        return "，".join(reasons[:3]) if reasons else "技术面转弱建议减仓"

    def generate_fallback(self, row):
        """最终兜底"""
        try:
            price = float(row.get("close", row.get("Close", 0)) or 0)
            score = float(row.get("score", row.get("Score", 0)) or 0)
        except (ValueError, TypeError):
            price = 0
            score = 0
            
        if score >= 70:
            rating = "买入"
        elif score >= 50:
            rating = "观望"
        else:
            rating = "卖出"
        return {
            "rating": rating,
            "confidence": 50,
            "reason": "数据不足，仅供参考",
            "entry": f"{price:.2f}",
            "target": f"{price * 1.08:.2f}",
            "stop_loss": f"{price * 0.95:.2f}",
            "hold_period": "观望",
            "risk": "高",
            "summary": f"{rating}（数据不足）",
            "分析来源": "兜底"
        }

