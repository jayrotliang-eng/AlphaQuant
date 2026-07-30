
# =========================
# AlphaQuant 设置
# =========================

# 扫描设置
MIN_SCORE = 40          # 最低分数门槛
AI_TOP = 30             # AI 分析前几名
FINAL_TOP = 10          # 最终输出前几名

# 输出文件
OUTPUT_FILE = "output/top10.csv"
FULL_OUTPUT_FILE = "output/scan_result.csv"

# 评分等级（给小白看的）
def score_to_stars(score):
    """把分数转成星星"""
    if score >= 90:
        return "⭐⭐⭐⭐⭐"
    elif score >= 80:
        return "⭐⭐⭐⭐"
    elif score >= 70:
        return "⭐⭐⭐"
    elif score >= 60:
        return "⭐⭐"
    else:
        return "⭐"

def trend_to_chinese(trend):
    """趋势翻译"""
    mapping = {
        "Bull": "📈 上涨中",
        "Bear": "📉 下跌中",
        "Neutral": "➡️ 横盘中"
    }
    return mapping.get(trend, trend)

def momentum_to_chinese(momentum):
    """动能翻译"""
    mapping = {
        "Strong": "🔥 很强",
        "Moderate": "💪 中等",
        "Weak": "😴 偏弱"
    }
    return mapping.get(momentum, momentum)

def breakout_to_chinese(breakout):
    """突破翻译"""
    mapping = {
        "Yes": "✅ 是",
        "No": "❌ 否"
    }
    return mapping.get(breakout, breakout)

def rating_to_chinese(rating):
    """AI评级翻译"""
    mapping = {
        "Strong Buy": "🟢 强力买入",
        "Buy": "🔵 建议买入",
        "Hold": "🟡 观望",
        "Sell": "🔴 建议卖出",
        "Strong Sell": "⛔ 强力卖出"
    }
    return mapping.get(rating, rating)

