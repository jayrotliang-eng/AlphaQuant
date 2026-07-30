
import yfinance as yf


class FundamentalAnalyzer:
    """
    分析公司基本面：赚不赚钱、贵不贵、有没有成长性
    """

    def analyze(self, symbol):
        """
        获取基本面数据，返回小白能看懂的结论
        """

        try:

            stock = yf.Ticker(symbol)
            info = stock.info

            # 获取关键数据
            pe_ratio = info.get("trailingPE", None)
            forward_pe = info.get("forwardPE", None)
            peg_ratio = info.get("pegRatio", None)
            revenue_growth = info.get("revenueGrowth", None)
            profit_margin = info.get("profitMargins", None)
            debt_to_equity = info.get("debtToEquity", None)
            free_cashflow = info.get("freeCashflow", None)
            market_cap = info.get("marketCap", None)
            dividend_yield = info.get("dividendYield", None)
            sector = info.get("sector", "未知")
            industry = info.get("industry", "未知")

            # 分析结论
            result = {
                "sector": sector,
                "industry": industry,
                "market_cap": self._format_market_cap(market_cap),
                "pe_ratio": round(pe_ratio, 1) if pe_ratio else "N/A",
                "forward_pe": round(forward_pe, 1) if forward_pe else "N/A",
                "revenue_growth": f"{revenue_growth*100:.1f}%" if revenue_growth else "N/A",
                "profit_margin": f"{profit_margin*100:.1f}%" if profit_margin else "N/A",
                "debt_to_equity": round(debt_to_equity, 1) if debt_to_equity else "N/A",
                "dividend_yield": f"{dividend_yield*100:.2f}%" if dividend_yield else "无",
                "valuation": self._judge_valuation(pe_ratio, forward_pe, peg_ratio),
                "growth": self._judge_growth(revenue_growth),
                "health": self._judge_health(profit_margin, debt_to_equity, free_cashflow),
                "summary": self._generate_summary(symbol, pe_ratio, revenue_growth, profit_margin, debt_to_equity)
            }

            return result

        except Exception as e:
            return {
                "sector": "N/A",
                "industry": "N/A",
                "market_cap": "N/A",
                "pe_ratio": "N/A",
                "forward_pe": "N/A",
                "revenue_growth": "N/A",
                "profit_margin": "N/A",
                "debt_to_equity": "N/A",
                "dividend_yield": "N/A",
                "valuation": "未知",
                "growth": "未知",
                "health": "未知",
                "summary": f"分析失败: {str(e)[:50]}"
            }

    def _format_market_cap(self, cap):
        """市值转成人类读得懂的格式"""
        if not cap:
            return "N/A"
        if cap >= 1e12:
            return f"${cap/1e12:.1f}兆"
        elif cap >= 1e9:
            return f"${cap/1e9:.1f}B"
        elif cap >= 1e6:
            return f"${cap/1e6:.1f}M"
        return f"${cap}"

    def _judge_valuation(self, pe, forward_pe, peg):
        """判断估值：便宜、合理、偏贵"""
        if not pe:
            return "无法判断"
        if pe < 15:
            return "💚 便宜"
        elif pe < 25:
            return "🟡 合理"
        elif pe < 40:
            return "🟠 偏贵"
        else:
            return "🔴 很贵"

    def _judge_growth(self, revenue_growth):
        """判断成长性"""
        if not revenue_growth:
            return "无数据"
        if revenue_growth > 0.20:
            return "🚀 高速成长"
        elif revenue_growth > 0.10:
            return "📈 稳定成长"
        elif revenue_growth > 0:
            return "➡️ 缓慢成长"
        else:
            return "📉 营收下滑"

    def _judge_health(self, margin, debt, fcf):
        """判断财务健康"""
        score = 0

        if margin and margin > 0.15:
            score += 1
        if debt and debt < 100:
            score += 1
        if fcf and fcf > 0:
            score += 1

        if score >= 3:
            return "💪 很健康"
        elif score >= 2:
            return "👍 还不错"
        elif score >= 1:
            return "⚠️ 一般"
        else:
            return "🚨 要注意"

    def _generate_summary(self, symbol, pe, growth, margin, debt):
        """生成一句话基本面总结"""

        parts = []

        if pe:
            if pe < 15:
                parts.append("估值便宜")
            elif pe > 40:
                parts.append("估值偏高")

        if growth:
            if growth > 0.15:
                parts.append("营收成长快")
            elif growth < 0:
                parts.append("营收在下滑")

        if margin:
            if margin > 0.20:
                parts.append("赚钱能力强")
            elif margin < 0.05:
                parts.append("利润很薄")

        if debt:
            if debt > 200:
                parts.append("负债偏高")

        if parts:
            return f"{symbol}: " + "，".join(parts)
        else:
            return f"{symbol}: 基本面数据正常"

