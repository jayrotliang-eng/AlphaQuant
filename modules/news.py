
import os
import re
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class NewsAnalyzer:
    """
    终极新闻情绪分析器
    第1层：免费抓取真实新闻标题（Yahoo RSS + Google News）
    第2层：关键词快速情绪判断（不消耗 API）
    第3层：AI 深度分析（Groq 免费 → 规则兜底）
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # AI 客户端（优先 Groq，免费）
        groq_key = os.getenv("GROQ_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")

        if groq_key:
            self.ai_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key
            )
            self.ai_model = "llama-3.3-70b-versatile"
            self.ai_source = "Groq"
        elif openrouter_key:
            self.ai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key
            )
            self.ai_model = "deepseek/deepseek-chat"
            self.ai_source = "OpenRouter"
        else:
            self.ai_client = None
            self.ai_source = None

    def analyze(self, symbol, sector="", industry=""):
        """完整新闻分析：抓新闻 → 关键词判断 → AI 深度分析"""

        # === 第1层：免费抓取真实新闻 ===
        headlines = self._fetch_news(symbol)

        # === 第2层：关键词快速情绪判断（永远免费） ===
        keyword_score, keyword_sentiment = self._keyword_sentiment(headlines)
        has_major = self._detect_major_news(headlines)

        # === 第3层：AI 深度分析 ===
        ai_analysis = self._ai_deep_analysis(symbol, sector, industry, headlines)

        # === 合并结果 ===
        return {
            # 新闻数据
            "news_count": len(headlines),
            "headlines": headlines[:5],
            "has_major_news": has_major,

            # 关键词情绪（免费快速判断）
            "keyword_sentiment": keyword_sentiment,
            "keyword_score": keyword_score,

            # AI 深度分析
            "sentiment": ai_analysis.get("sentiment", keyword_sentiment),
            "key_events": ai_analysis.get("key_events", "无数据"),
            "risk_factors": ai_analysis.get("risk_factors", "N/A"),
            "catalyst": ai_analysis.get("catalyst", "N/A"),
            "news_score": ai_analysis.get("news_score", self._convert_score(keyword_score)),

            # 综合总结
            "summary": self._generate_summary(symbol, headlines, ai_analysis, keyword_sentiment, has_major),
            "analysis_source": ai_analysis.get("source", "关键词")
        }

    # ==========================================
    # 第1层：免费新闻抓取
    # ==========================================

    def _fetch_news(self, symbol):
        """从多个免费来源获取新闻标题"""
        headlines = []

        # 来源 1：Yahoo Finance RSS
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', resp.text)
                if not titles:
                    titles = re.findall(r'<title>(.*?)</title>', resp.text)
                headlines.extend(titles[1:10])
        except Exception:
            pass

        # 来源 2：Google News RSS
        if len(headlines) < 3:
            try:
                url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    titles = re.findall(r'<title>(.*?)</title>', resp.text)
                    headlines.extend(titles[2:8])
            except Exception:
                pass

        # 去重
        seen = set()
        unique = []
        for h in headlines:
            h_clean = h.strip()
            if h_clean and h_clean not in seen and len(h_clean) > 10:
                seen.add(h_clean)
                unique.append(h_clean)

        return unique[:10]

    # ==========================================
    # 第2层：关键词快速情绪判断（永远免费）
    # ==========================================

    def _keyword_sentiment(self, headlines):
        """用关键词分析情绪（不消耗任何 API）"""
        positive_words = [
            'surge', 'soar', 'jump', 'rally', 'gain', 'rise', 'high', 'record',
            'beat', 'exceed', 'strong', 'growth', 'profit', 'upgrade', 'buy',
            'outperform', 'bullish', 'boost', 'positive', 'best', 'up',
            'innovation', 'breakthrough', 'partnership', 'expand', 'success',
            'dividend', 'revenue', 'earnings beat', 'optimistic', 'momentum',
            'approve', 'launch', 'recover', 'improve'
        ]
        negative_words = [
            'fall', 'drop', 'decline', 'crash', 'loss', 'low', 'cut', 'slash',
            'miss', 'weak', 'down', 'sell', 'downgrade', 'bearish', 'fear',
            'risk', 'warning', 'layoff', 'lawsuit', 'investigation', 'fraud',
            'debt', 'bankruptcy', 'recall', 'penalty', 'fine', 'worst',
            'concern', 'disappoint', 'plunge', 'tumble', 'slump', 'delay',
            'suspend', 'terminate', 'crisis'
        ]

        pos_count = 0
        neg_count = 0

        for headline in headlines:
            h_lower = headline.lower()
            for word in positive_words:
                if word in h_lower:
                    pos_count += 1
            for word in negative_words:
                if word in h_lower:
                    neg_count += 1

        total = pos_count + neg_count
        if total == 0:
            return 0, "⚪ 中性"

        score = (pos_count - neg_count) / total  # -1 到 +1

        if score > 0.4:
            label = "🟢 强烈正面"
        elif score > 0.15:
            label = "🟢 偏正面"
        elif score > -0.15:
            label = "⚪ 中性"
        elif score > -0.4:
            label = "🟠 偏负面"
        else:
            label = "🔴 强烈负面"

        return round(score, 2), label

    def _detect_major_news(self, headlines):
        """检测是否有重大新闻"""
        major_keywords = [
            'acquisition', 'acquire', 'merger', 'buyout', 'takeover',
            'earnings', 'quarterly results', 'guidance', 'forecast',
            'ceo', 'cfo', 'resign', 'appoint', 'fired',
            'fda', 'approval', 'patent', 'trial',
            'split', 'buyback', 'dividend increase', 'dividend cut',
            'sec', 'investigation', 'lawsuit', 'settlement',
            'bankruptcy', 'restructuring', 'delisting'
        ]

        for headline in headlines:
            h_lower = headline.lower()
            for keyword in major_keywords:
                if keyword in h_lower:
                    return True
        return False

    def _convert_score(self, keyword_score):
        """把 -1~+1 的关键词分数转成 1~10"""
        return max(1, min(10, int((keyword_score + 1) * 4.5 + 1)))

    # ==========================================
    # 第3层：AI 深度分析
    # ==========================================

    def _ai_deep_analysis(self, symbol, sector, industry, headlines):
        """用 AI 深度分析新闻影响"""
        if not self.ai_client:
            return {"source": "关键词"}

        # 构建新闻上下文
        news_context = ""
        if headlines:
            news_context = "最新新闻标题:\n" + "\n".join([f"- {h}" for h in headlines[:5]])
        else:
            news_context = "（无法获取最新新闻，请根据你的训练知识判断）"

        prompt = f"""你是一位资深金融新闻分析师。
请分析 {symbol} 这支股票最近的新闻情况和市场情绪。

股票: {symbol}
行业: {sector} / {industry}

{news_context}

请用 JSON 格式回答：
{{
    "sentiment": "正面/中性/负面（三选一）",
    "key_events": "最近影响股价的1-2个关键事件（简短中文，不确定就写'无重大事件'）",
    "risk_factors": "目前主要风险（简短中文）",
    "catalyst": "可能推动上涨的因素（简短中文）",
    "news_score": 数字1-10（10=非常正面, 5=中性, 1=非常负面）
}}

要求：只回传 JSON，不要其他文字。所有描述用简单中文。"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": "你是金融新闻分析师，只回传 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )

            content = response.choices[0].message.content.strip()

            # 清理 markdown
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0].strip()

            analysis = json.loads(content)
            analysis["source"] = self.ai_source
            return analysis

        except Exception as e:
            # AI 失败，回退到关键词结果
            return {"source": "关键词"}

    # ==========================================
    # 综合总结
    # ==========================================

    def _generate_summary(self, symbol, headlines, ai_analysis, keyword_sentiment, has_major):
        """生成最终新闻总结"""
        parts = [f"{symbol}:"]

        # 新闻数量
        if headlines:
            parts.append(f"近期{len(headlines)}条新闻")
        else:
            parts.append("无近期新闻")

        # AI 情绪 or 关键词情绪
        sentiment = ai_analysis.get("sentiment", "")
        if sentiment and sentiment != "未知":
            parts.append(f"情绪:{sentiment}")
        else:
            parts.append(f"情绪:{keyword_sentiment}")

        # 关键事件
        events = ai_analysis.get("key_events", "")
        if events and events != "无数据" and events != "分析失败":
            parts.append(events)

        # 重大新闻标记
        if has_major:
            parts.append("⚡有重大新闻")

        return " | ".join(parts)

