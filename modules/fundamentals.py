
import yfinance as yf


class FundamentalAnalyzer:
    """
    终极基本面分析器
    结合数据获取 + 小白友好结论 + 数字评分 + 分析师共识
    """

    def analyze(self, symbol):
        """获取基本面数据，返回完整分析"""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info

            # 获取所有关键数据
            pe_ratio = info.get("trailingPE", None)
            forward_pe = info.get("forwardPE", None)
            peg_ratio = info.get("pegRatio", None)
            revenue_growth = info.get("revenueGrowth", None)
            profit_margin = info.get("profitMargins", None)
            roe = info.get("returnOnEquity", None)
            debt_to_equity = info.get("debtToEquity", None)
            free_cashflow = info.get("freeCashflow", None)
            market_cap = info.get("marketCap", None)
            dividend_yield = info.get("dividendYield", None)
            sector = info.get("sector", "未知")
            industry = info.get("industry", "未知")
            week52_high = info.get("fiftyTwoWeekHigh", None)
            week52_low = info.get("fiftyTwoWeekLow", None)
            current_price = info.get("currentPrice", None)
            target_price = info.get("targetMeanPrice", None)
            recommendation = info.get("recommendationKey", "N/A")
            num_analysts = info.get("numberOfAnalystOpinions", 0)

            # 完整结果
            result = {
                # 基本信息
                "sector": sector,
                "industry": industry,
                "market_cap": self._format_market_cap(market_cap),

                # 估值指标
                "pe_ratio": round(pe_ratio, 1) if pe_ratio else "N/A",
                "forward_pe": round(forward_pe, 1) if forward_pe else "N/A",
                "peg_ratio": round(peg_ratio, 2) if peg_ratio else "N/A",

                # 成长指标
                "revenue_growth": f"{revenue_growth*100:.1f}%" if revenue_growth else "N/A",
                "profit_margin": f"{profit_margin*100:.1f}%" if profit_margin else "N/A",
                "roe": f"{roe*100:.1f}%" if roe else "N/A",

                # 财务健康
                "debt_to_equity": round(debt_to_equity, 1) if debt_to_equity else "N/A",
                "free_cashflow": self._format_cashflow(free_cashflow),
                "dividend_yield": f"{dividend_yield*100:.2f}%" if dividend_yield else "无",

                # 价格参考
                "52week_high": f"${week52_high:.2f}" if week52_high else "N/A",
                "52week_low": f"${week52_low:.2f}" if week52_low else "N/A",
                "distance_from_high": self._calc_distance(current_price, week52_high),

                # 分析师共识
                "analyst_target": f"${target_price:.2f}" if target_price else "N/A",
                "analyst_upside": self._calc_upside(current_price, target_price),
                "analyst_recommendation": self._translate_recommendation(recommendation),
                "num_analysts": num_analysts,

                # 小白友好结论
                "valuation": self._judge_valuation(pe_ratio, forward_pe, peg_ratio),
                "growth": self._judge_growth(revenue_growth),
                "health": self._judge_health(profit_margin, debt_to_equity, free_cashflow, roe),

                # 综合评分和总结
                "fundamental_score": self._calculate_score(info),
                "summary": self._generate_summary(symbol, pe_ratio, revenue_growth, profit_margin, debt_to_equity, target_price, current_price, recommendation)
            }

            return result

        except Exception as e:
            return {
                "sector": "N/A",
                "industry": "N/A",
                "market_cap": "N/A",
                "pe_ratio": "N/A",
                "forward_pe": "N/A",
                "peg_ratio": "N/A",
                "revenue_growth": "N/A",
                "profit_margin": "N/A",
                "roe": "N/A",
                "debt_to_equity": "N/A",
                "free_cashflow": "N/A",
                "dividend_yield": "N/A",
                "52week_high": "N/A",
                "52week_low": "N/A",
                "distance_from_high": "N/A",
                "analyst_target": "N/A",
                "analyst_upside": "N/A",
                "analyst_recommendation": "N/A",
                "num_analysts": 0,
                "valuation": "未知",
                "growth": "未知",
                "health": "未知",
                "fundamental_score": 0,
                "summary": f"分析失败: {str(e)[:50]}"
            }

    # ===== 格式化工具 =====

    def _format_market_cap(self, cap):
        """市值格式化"""
        if not cap:
            return "N/A"
        if cap >= 1e12:
            return f"${cap/1e12:.1f}T"
        elif cap >= 1e9:
            return f"${cap/1e9:.1f}B"
        elif cap >= 1e6:
            return f"${cap/1e6:.1f}M"
        return f"${cap}"

    def _format_cashflow(self, fcf):
        """自由现金流格式化"""
        if not fcf:
            return "N/A"
        if fcf >= 1e9:
            return f"${fcf/1e9:.1f}B"
        elif fcf >= 1e6:
            return f"${fcf/1e6:.0f}M"
        return f"${fcf:,.0f}"

    def _calc_distance(self, current, high):
        """计算距离52周高点的距离"""
        if not current or not high:
            return "N/A"
        distance = (current - high) / high * 100
        return f"{distance:.1f}%"

    def _calc_upside(self, current, target):
        """计算分析师目标价的上涨空间"""
        if not current or not target:
            return "N/A"
        upside = (target - current) / current * 100
        if upside > 0:
            return f"📈 +{upside:.1f}%"
        else:
            return f"📉 {upside:.1f}%"

    def _translate_recommendation(self, rec):
        """翻译分析师建议"""
        translations = {
            "strongBuy": "🟢 强烈买入",
            "buy": "🟢 买入",
            "hold": "🟡 持有",
            "sell": "🔴 卖出",
            "strongSell": "🔴 强烈卖出",
            "underperform": "🟠 弱于大盘",
            "outperform": "🟢 优于大盘",
        }
        return translations.get(rec, rec if rec != "N/A" else "无评级")

    # ===== 判断逻辑 =====

    def _judge_valuation(self, pe, forward_pe, peg):
        """判断估值"""
        if not pe:
            return "⚪ 无法判断"

        # PEG < 1 是低估的信号
        if peg and peg < 1:
            return "💚 低估（PEG<1）"

        if pe < 12:
            return "💚 很便宜"
        elif pe < 20:
            return "💚 便宜"
        elif pe < 30:
            return "🟡 合理"
        elif pe < 50:
            return "🟠 偏贵"
        else:
            return "🔴 很贵"

    def _judge_growth(self, revenue_growth):
        """判断成长性"""
        if not revenue_growth:
            return "⚪ 无数据"
        if revenue_growth > 0.25:
            return "🚀 爆发式成长"
        elif revenue_growth > 0.15:
            return "🚀 高速成长"
        elif revenue_growth > 0.08:
            return "📈 稳定成长"
        elif revenue_growth > 0:
            return "➡️ 缓慢成长"
        elif revenue_growth > -0.1:
            return "📉 轻微下滑"
        else:
            return "🔴 严重下滑"

    def _judge_health(self, margin, debt, fcf, roe):
        """判断财务健康（升级版 - 加入ROE和现金流）"""
        score = 0
        total = 0

        if margin is not None:
            total += 1
            if margin > 0.15:
                score += 1

        if debt is not None:
            total += 1
            if debt < 100:
                score += 1

        if fcf is not None:
            total += 1
            if fcf > 0:
                score += 1

        if roe is not None:
            total += 1
            if roe > 0.12:
                score += 1

        if total == 0:
            return "⚪ 数据不足"

        ratio = score / total
        if ratio >= 0.75:
            return "💪 很健康"
        elif ratio >= 0.5:
            return "👍 还不错"
        elif ratio >= 0.25:
            return "⚠️ 一般"
        else:
            return "🚨 要注意"

    # ===== 综合评分 =====

    def _calculate_score(self, info):
        """计算基本面综合评分 (0-100)"""
        score = 50  # 基础分

        # PE 合理性
        pe = info.get("trailingPE")
        if pe:
            if 10 <= pe <= 25:
                score += 12
            elif 5 <= pe < 10 or 25 < pe <= 35:
                score += 5
            elif pe > 60:
                score -= 10

        # PEG（<1 低估, >2 高估）
        peg = info.get("pegRatio")
        if peg:
            if peg < 1:
                score += 10
            elif peg < 1.5:
                score += 5
            elif peg > 2.5:
                score -= 5

        # 营收增长
        growth = info.get("revenueGrowth")
        if growth:
            if growth > 0.25:
                score += 15
            elif growth > 0.15:
                score += 10
            elif growth > 0.05:
                score += 5
            elif growth < -0.05:
                score -= 8

        # 利润率
        margin = info.get("profitMargins")
        if margin:
            if margin > 0.25:
                score += 10
            elif margin > 0.15:
                score += 7
            elif margin > 0.05:
                score += 3
            elif margin < 0:
                score -= 10

        # ROE
        roe = info.get("returnOnEquity")
        if roe:
            if roe > 0.25:
                score += 10
            elif roe > 0.15:
                score += 7
            elif roe > 0.08:
                score += 3
            elif roe < 0:
                score -= 8

        # 负债率
        debt = info.get("debtToEquity")
        if debt:
            if debt < 50:
                score += 5
            elif debt > 200:
                score -= 8

        # 分析师建议加分
        rec = info.get("recommendationKey", "")
        if rec in ("strongBuy", "buy"):
            score += 8
        elif rec == "hold":
            score += 0
        elif rec in ("sell", "strongSell"):
            score -= 8

        return max(0, min(100, score))

    # ===== 总结 =====

    def _generate_summary(self, symbol, pe, growth, margin, debt, target, current, recommendation):
        """生成一句话总结（升级版 - 加入分析师意见）"""
        parts = []

        # 估值
        if pe:
            if pe < 15:
                parts.append("估值便宜")
            elif pe > 40:
                parts.append("估值偏高")

        # 成长
        if growth:
            if growth > 0.15:
                parts.append("营收成长快")
            elif growth < -0.05:
                parts.append("营收在下滑")

        # 利润
        if margin:
            if margin > 0.20:
                parts.append("赚钱能力强")
            elif margin < 0.05:
                parts.append("利润很薄")

        # 负债
        if debt:
            if debt > 200:
                parts.append("负债偏高")

        # 分析师
        if target and current:
            upside = (target - current) / current * 100
            if upside > 20:
                parts.append(f"分析师看涨{upside:.0f}%")
            elif upside < -10:
                parts.append(f"分析师看跌")

        if recommendation in ("strongBuy", "buy"):
            parts.append("华尔街推荐买入")
        elif recommendation in ("sell", "strongSell"):
            parts.append("华尔街建议卖出")

        if parts:
            return f"{symbol}: " + "，".join(parts)
        else:
            return f"{symbol}: 基本面数据正常，无明显优劣"

