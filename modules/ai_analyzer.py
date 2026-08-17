
import os
import time
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class AIAnalyzer:

    # 2026-08 更新：当前可用的免费/低价模型
    MODELS = [
        "deepseek/deepseek-chat-v3-0324",                   # 低价首选
        "nousresearch/hermes-3-llama-3.1-405b:free",        # 免费备用 1
        "qwen/qwen-2.5-72b-instruct:free",                 # 免费备用 2
        "deepseek/deepseek-r1-distill-llama-70b:free",      # 免费备用 3
        "microsoft/phi-4:free",                             # 免费备用 4
    ]

    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.current_model_index = 0
        self.use_gemini = False  # 当所有 OpenRouter 模型都失败时切换

    def _get_model(self):
        return self.MODELS[self.current_model_index]

    def _switch_to_next_model(self):
        if self.current_model_index < len(self.MODELS) - 1:
            self.current_model_index += 1
            print(f"   🔄 切换模型: {self._get_model()}")
            return True
        return False

    def _reset_model(self):
        """每次分析新股票时重置到第一个模型"""
        if not self.use_gemini:
            self.current_model_index = 0

    def _call_gemini(self, prompt):
        """直接调用 Google Gemini API（免费层，不需要信用卡）"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 300
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text
        else:
            raise Exception(f"Gemini error: {response.status_code} - {response.text[:200]}")

    def analyze(self, row, fundamentals=None, news=None):
        """AI 分析单只股票（兼容基本面+新闻输入）"""

        # 每次分析新股票，从第一个模型开始尝试（除非已确认要用 Gemini）
        self._reset_model()

        # 从 row 提取基本信息
        if hasattr(row, 'get'):
            ticker = row.get("ticker", row.get("Ticker", "N/A"))
            price = float(row.get("price", row.get("Price", 0)))
            score = float(row.get("score", row.get("Score", 0)))
            trend = row.get("trend", row.get("Trend", "N/A"))
            adx = float(row.get("adx", row.get("ADX", 0)))
            atr_pct = float(row.get("atr_pct", row.get("ATR_%", 0)))
        else:
            ticker = "N/A"
            price = 0
            score = 0
            trend = "N/A"
            adx = 0
            atr_pct = 0

        # 构建 prompt
        prompt = f"""你是一位专业的股票技术分析师。请用中文分析以下股票：

股票代码: {ticker}
当前价格: ${price:.2f}
技术评分: {score}/100
趋势方向: {trend}
趋势强度(ADX): {adx:.1f}
波动率(ATR%): {atr_pct:.1f}%"""

        # 加入基本面数据
        if fundamentals and isinstance(fundamentals, dict):
            prompt += f"""

基本面数据:
- 市盈率(PE): {fundamentals.get('pe_ratio', 'N/A')}
- 营收增长: {fundamentals.get('revenue_growth', 'N/A')}
- 利润率: {fundamentals.get('profit_margin', 'N/A')}
- 市值: {fundamentals.get('market_cap', 'N/A')}"""

        # 加入新闻情绪
        if news and isinstance(news, dict):
            prompt += f"""

近期新闻情绪:
- 情绪评分: {news.get('sentiment', 'N/A')}
- 新闻摘要: {news.get('summary', '无重大新闻')}"""

        prompt += """

请提供：
1. 趋势方向（用 ↑上涨中 / ↓下跌中 / →横盘 表示）
2. 上涨动能（强/中/弱）
3. 是否有支撑推力（是/否）
4. 买入建议（建议买入/观望/建议卖出）
5. 信心度（0-100%）
6. 风险等级（低风险/中风险/高风险）
7. 建议入场价
8. 建议止损价
9. 目标价
10. 一句话总结（20字内）

请严格按以下格式回复（用 | 分隔，一行搞定，不要换行）：
趋势方向|上涨动能|支撑推力|买入建议|信心度|风险等级|入场价|止损价|目标价|总结"""

        # ============================================
        # 如果已确认 OpenRouter 全挂，直接用 Gemini
        # ============================================
        if self.use_gemini:
            return self._try_gemini(prompt, ticker, price)

        # ============================================
        # 重试逻辑：尝试所有 OpenRouter 模型
        # ============================================
        for attempt in range(len(self.MODELS)):
            try:
                response = self.client.chat.completions.create(
                    model=self._get_model(),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
                result = response.choices[0].message.content.strip()
                parsed = self._parse_result(result, ticker, price)
                return parsed

            except Exception as e:
                error_msg = str(e)

                if "402" in error_msg or "insufficient" in error_msg.lower() or "credit" in error_msg.lower():
                    print(f"   ⚠️ {self._get_model()} 额度不足")
                    if not self._switch_to_next_model():
                        break  # 所有模型都失败，跳出循环去 Gemini

                elif "429" in error_msg:
                    print(f"   ⏳ 频率限制，等待 10 秒...")
                    time.sleep(10)

                elif "404" in error_msg:
                    print(f"   ⚠️ {self._get_model()} 不可用")
                    if not self._switch_to_next_model():
                        break

                elif "401" in error_msg:
                    print(f"   ⚠️ OpenRouter API Key 无效")
                    break  # Key 都无效，直接去 Gemini

                else:
                    print(f"   ❌ AI 错误 ({ticker}): {error_msg[:80]}")
                    if not self._switch_to_next_model():
                        break

        # ============================================
        # 最后后备：Google Gemini API（免费）
        # ============================================
        return self._try_gemini(prompt, ticker, price)

    def _try_gemini(self, prompt, ticker, price):
        """尝试用 Gemini API 分析"""
        if not self.gemini_key:
            print(f"   ❌ 所有 AI 模型不可用，无 Gemini Key")
            return self._default_result(ticker, price)
        
        try:
            if not self.use_gemini:
                self.use_gemini = True
                print(f"   🔄 切换到 Google Gemini（免费）")
            
            result = self._call_gemini(prompt)
            parsed = self._parse_result(result, ticker, price)
            return parsed
        except Exception as e:
            print(f"   ❌ Gemini 也失败 ({ticker}): {str(e)[:80]}")
            return self._default_result(ticker, price)

    def _parse_result(self, result, ticker, price):
        """解析 AI 回复"""
        try:
            # 处理多行或单行格式
            clean = result.replace("\n", "|")
            parts = [p.strip() for p in clean.split("|") if p.strip()]

            if len(parts) >= 10:
                confidence = parts[4].replace("%", "").strip()
                try:
                    confidence = str(int(float(confidence)))
                except ValueError:
                    confidence = "50"

                return {
                    "趋势方向": parts[0],
                    "上涨动能": parts[1],
                    "支撑推力": parts[2],
                    "AI建议": parts[3],
                    "信心度": confidence,
                    "风险等级": parts[5],
                    "入场价": parts[6].replace("$", "").replace("￥", ""),
                    "止损价": parts[7].replace("$", "").replace("￥", ""),
                    "目标价": parts[8].replace("$", "").replace("￥", ""),
                    "总结": parts[9]
                }
        except Exception:
            pass

        return self._default_result(ticker, price)

    def _default_result(self, ticker, price):
        """当 AI 无法分析时的默认结果"""
        return {
            "趋势方向": "→横盘",
            "上涨动能": "中",
            "支撑推力": "否",
            "AI建议": "观望",
            "信心度": "50",
            "风险等级": "中风险",
            "入场价": f"{price:.2f}",
            "止损价": f"{price * 0.95:.2f}",
            "目标价": f"{price * 1.10:.2f}",
            "总结": "数据不足，建议观望"
        }