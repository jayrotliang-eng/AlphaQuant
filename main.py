
import os
import pandas as pd
from dotenv import load_dotenv

# 载入 .env 文件
load_dotenv()

from modules.scanner import Scanner
from modules.universe import Universe
from modules.ai_analyzer import AIAnalyzer
from modules.fundamentals import FundamentalAnalyzer
from modules.news import NewsAnalyzer
from modules.sheet import GoogleSheet
from config.settings import (
    AI_TOP,
    FINAL_TOP,
    MIN_SCORE,
    OUTPUT_FILE,
    FULL_OUTPUT_FILE,
    score_to_stars,
    trend_to_chinese,
    momentum_to_chinese,
    breakout_to_chinese,
    rating_to_chinese
)
from config.watchlist import WATCHLIST


# =========================
# 建立输出目录
# =========================

os.makedirs("output", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("cache", exist_ok=True)


# =========================
# 读取股票池
# =========================

universe = Universe()
symbols = universe.get_symbols()

print(f"\n📊 AlphaQuant 每日扫描")
print(f"   股票池: {len(symbols)} 支美股")
print(f"   关注清单: {len(WATCHLIST)} 支")
print(f"   最低分数: {MIN_SCORE} 分")
print(f"   AI 深度分析: 前 {AI_TOP} 名 + 关注清单")
print(f"   最终精选: 前 {FINAL_TOP} 名")
print(f"\n{'='*50}\n")


# =========================
# 扫描全部股票
# =========================

print("🔍 正在扫描所有股票...\n")

scanner = Scanner()
result = scanner.scan(symbols)


# =========================
# 过滤低分
# =========================

if not result.empty:

    qualified = result[
        result["Score"] >= MIN_SCORE
    ].copy()

    print(f"\n{'='*50}")
    print(f"✅ 扫描完成！")
    print(f"   总共扫描: {len(result)} 支")
    print(f"   达标股票 (≥{MIN_SCORE}分): {len(qualified)} 支")
    print(f"{'='*50}\n")

else:

    print("❌ 没有扫描结果")
    exit()


# =========================
# 合并关注清单
# =========================

watchlist_in_result = result[result["Symbol"].isin(WATCHLIST)].copy()
top_for_ai = result.head(AI_TOP).copy()

combined = pd.concat([top_for_ai, watchlist_in_result]).drop_duplicates(subset="Symbol").reset_index(drop=True)

print(f"🔗 合并分析: Top {AI_TOP} ({len(top_for_ai)}支) + 关注清单 ({len(watchlist_in_result)}支)")
print(f"   去重后总共: {len(combined)} 支需要 AI 分析\n")


# =========================
# 基本面 + 新闻 + AI 综合分析
# =========================

combined["AI评级"] = ""
combined["信心度"] = 0
combined["风险等级"] = ""
combined["买入价"] = ""
combined["止损价"] = ""
combined["目标价"] = ""
combined["持有周期"] = ""
combined["技术面评价"] = ""
combined["基本面评价"] = ""
combined["新闻面评价"] = ""
combined["一句话总结"] = ""
combined["操作建议"] = ""
combined["行业"] = ""
combined["市值"] = ""
combined["估值"] = ""
combined["成长性"] = ""
combined["财务健康"] = ""
combined["新闻情绪"] = ""
combined["关键事件"] = ""
combined["是否关注"] = ""

print(f"🤖 开始三维度深度分析...\n")

fund_analyzer = FundamentalAnalyzer()
news_analyzer = NewsAnalyzer()
ai = AIAnalyzer()

for index, row in combined.iterrows():

    symbol = row["Symbol"]
    is_watchlist = "⭐" if symbol in WATCHLIST else ""
    combined.loc[index, "是否关注"] = is_watchlist

    print(f"   [{index+1}/{len(combined)}] {symbol} {is_watchlist}")

    # Step 1: 基本面
    print(f"      📊 基本面分析...")
    fundamentals = fund_analyzer.analyze(symbol)
    combined.loc[index, "行业"] = f"{fundamentals.get('sector','')} / {fundamentals.get('industry', '')}"
    combined.loc[index, "市值"] = str(fundamentals.get("market_cap", "N/A"))
    combined.loc[index, "估值"] = str(fundamentals.get("valuation", "N/A"))
    combined.loc[index, "成长性"] = str(fundamentals.get("growth", "N/A"))
    combined.loc[index, "财务健康"] = str(fundamentals.get("health", "N/A"))

    # Step 2: 新闻情绪
    print(f"      📰 新闻情绪分析...")
    news = news_analyzer.analyze(
        symbol,
        sector=fundamentals.get("sector", ""),
        industry=fundamentals.get("industry", "")
    )
    combined.loc[index, "新闻情绪"] = str(news.get("sentiment", "N/A"))
    combined.loc[index, "关键事件"] = str(news.get("key_events", "N/A"))

    # Step 3: AI 综合判断
    print(f"      🤖 AI 综合判断...")
    analysis = ai.analyze(row, fundamentals=fundamentals, news=news)

    combined.loc[index, "AI评级"] = str(analysis.get("rating", "N/A"))
    combined.loc[index, "信心度"] = analysis.get("confidence", 0)
    combined.loc[index, "风险等级"] = str(analysis.get("risk", "N/A"))
    combined.loc[index, "买入价"] = str(analysis.get("entry", "N/A"))
    combined.loc[index, "止损价"] = str(analysis.get("stop_loss", analysis.get("止损价", analysis.get("stoploss", "N/A"))))
    combined.loc[index, "目标价"] = str(analysis.get("target", analysis.get("目标价", analysis.get("target_price", "N/A"))))
    combined.loc[index, "持有周期"] = str(analysis.get("timeframe", "N/A"))
    combined.loc[index, "技术面评价"] = str(analysis.get("technical_view", "N/A"))
    combined.loc[index, "基本面评价"] = str(analysis.get("fundamental_view", "N/A"))
    combined.loc[index, "新闻面评价"] = str(analysis.get("news_view", "N/A"))
    combined.loc[index, "一句话总结"] = str(analysis.get("summary", "N/A"))
    combined.loc[index, "操作建议"] = str(analysis.get("action", "N/A"))

    print(f"      ✅ 完成 → {analysis.get('rating', 'N/A')}\n")


# =========================
# 最终 Top 10
# =========================

combined["信心度"] = pd.to_numeric(combined["信心度"], errors="coerce").fillna(0)
final_top = combined.sort_values("信心度", ascending=False).head(FINAL_TOP).copy()
final_top["Rank"] = range(1, len(final_top) + 1)

final_top["评分等级"] = final_top["Score"].apply(score_to_stars)
final_top["趋势"] = final_top["Trend"].apply(trend_to_chinese)
final_top["动能"] = final_top["Momentum"].apply(momentum_to_chinese)
final_top["是否突破"] = final_top["Breakout"].apply(breakout_to_chinese)
final_top["AI建议"] = final_top["AI评级"].apply(rating_to_chinese)


# =========================
# 显示结果（终端）
# =========================

print(f"\n{'='*60}")
print(f"🏆 ========== ALPHAQUANT 今日精选 TOP {FINAL_TOP} ==========")
print(f"{'='*60}\n")

for _, row in final_top.iterrows():
    watchmark = row["是否关注"]
    print(f"{'─'*50}")
    print(f"  {row['Rank']}. {row['Symbol']} {watchmark} — ${row['Close']}  |  评分: {row['Score']}分 {row['评分等级']}")
    print(f"     {row['趋势']} | {row['动能']} | 突破: {row['是否突破']}")
    print(f"     📊 基本面: {row['估值']} | {row['成长性']} | {row['财务健康']}")
    print(f"     📰 新闻: {row['新闻情绪']} — {row['关键事件'][:40]}")
    print(f"     🤖 AI建议: {row['AI建议']} (信心 {row['信心度']}%)")
    print(f"     💰 买入: ${row['买入价']} → 目标: ${row['目标价']} | 🛑 止损: ${row['止损价']}")
    print(f"     ⏰ 持有周期: {row['持有周期']} | 风险: {row['风险等级']}")
    print(f"     💡 {row['一句话总结']}")
    print(f"     🎯 {row['操作建议']}")
    print()


# =========================
# 关注清单报告
# =========================

watchlist_results = combined[combined["是否关注"] == "⭐"].copy()

if not watchlist_results.empty:
    print(f"\n{'='*60}")
    print(f"⭐ ========== 关注清单报告 ==========")
    print(f"{'='*60}\n")

    for _, row in watchlist_results.iterrows():
        print(f"  {row['Symbol']} — ${row['Close']} | 评分: {row['Score']}分")
        print(f"     AI: {row['AI评级']} | {row['一句话总结']}")
        print(f"     🎯 {row['操作建议']}")
        print()


# =========================
# 准备 Google Sheet 数据
# =========================

sheet_data = final_top[[
    "Rank", "Symbol", "Close", "Score", "评分等级",
    "趋势", "动能", "是否突破",
    "行业", "估值", "成长性", "财务健康",
    "新闻情绪", "关键事件",
    "AI建议", "信心度", "风险等级", "持有周期",
    "买入价", "止损价", "目标价",
    "一句话总结", "操作建议", "是否关注"
]].copy()

sheet_data.columns = [
    "排名", "股票代码", "现价($)", "综合评分", "评分等级",
    "趋势方向", "上涨动能", "是否突破阻力",
    "所属行业", "估值水平", "成长性", "财务健康",
    "新闻情绪", "近期关键事件",
    "AI建议", "AI信心度(%)", "风险等级", "建议持有周期",
    "建议买入价($)", "止损价($)", "目标价($)",
    "一句话总结", "具体操作建议", "关注清单"
]


# =========================
# 保存结果
# =========================

result.to_csv(FULL_OUTPUT_FILE, index=False)
final_top.to_csv(OUTPUT_FILE, index=False)
combined.to_csv("output/top_ai_full.csv", index=False)


# =========================
# Google Sheet 输出
# =========================

print(f"\n📤 正在更新 Google Sheet...\n")

try:
    gs = GoogleSheet()
    gs.update("AlphaQuant", sheet_data, "今日精选")

    if not watchlist_results.empty:
        watchlist_sheet = watchlist_results[[
            "Symbol", "Close", "Score",
            "AI评级", "信心度", "风险等级",
            "买入价", "止损价", "目标价",
            "一句话总结", "操作建议"
        ]].copy()

        watchlist_sheet.columns = [
            "股票代码", "现价($)", "综合评分",
            "AI评级", "信心度(%)", "风险等级",
            "买入价($)", "止损价($)", "目标价($)",
            "一句话总结", "操作建议"
        ]

        gs.update("AlphaQuant", watchlist_sheet, "关注清单")

    print(f"   ✅ Google Sheet 更新完成")

except Exception as e:
    print(f"   ⚠️ Google Sheet 跳过: {e}")


# =========================
# Telegram 推送
# =========================

print(f"\n📱 正在推送到 Telegram...\n")

try:
    from modules.tg_bot import TelegramBot


    bot = TelegramBot()
    bot.send_full_report(final_top, watchlist_results)

except Exception as e:
    print(f"   ⚠️ Telegram 跳过: {e}")


# =========================
# 完成
# =========================

print(f"\n{'='*50}")
print(f"📁 全部扫描结果: {FULL_OUTPUT_FILE}")
print(f"📁 AI 完整分析: output/top_ai_full.csv")
print(f"📁 今日精选 Top {FINAL_TOP}: {OUTPUT_FILE}")
print(f"{'='*50}")
print(f"\n✅ AlphaQuant 今日扫描完成！\n")

