
import os
from dotenv import load_dotenv

load_dotenv()

import pandas as pd
from modules.scanner import Scanner
from modules.universe import Universe
from modules.ai_analyzer import AIAnalyzer
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
print(f"   最低分数: {MIN_SCORE} 分")
print(f"   AI 深度分析: 前 {AI_TOP} 名")
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
# AI 分析 Top N
# =========================

top_for_ai = result.head(AI_TOP).copy()

# 预先建立 AI 列（避免类型冲突）
top_for_ai["AI评级"] = ""
top_for_ai["信心度"] = 0
top_for_ai["风险等级"] = ""
top_for_ai["买入价"] = ""
top_for_ai["止损价"] = ""
top_for_ai["目标价"] = ""
top_for_ai["一句话总结"] = ""
top_for_ai["操作建议"] = ""

print(f"🤖 AI 正在深度分析前 {len(top_for_ai)} 名...\n")

ai = AIAnalyzer()

for index, row in top_for_ai.iterrows():

    print(f"   分析中: {row['Symbol']}...")

    analysis = ai.analyze(row)

    top_for_ai.loc[index, "AI评级"] = str(analysis.get("rating", "N/A"))
    top_for_ai.loc[index, "信心度"] = analysis.get("confidence", 0)
    top_for_ai.loc[index, "风险等级"] = str(analysis.get("risk", "N/A"))
    top_for_ai.loc[index, "买入价"] = str(analysis.get("entry", "N/A"))
    top_for_ai.loc[index, "止损价"] = str(analysis.get("stoploss", "N/A"))
    top_for_ai.loc[index, "目标价"] = str(analysis.get("target", "N/A"))
    top_for_ai.loc[index, "一句话总结"] = str(analysis.get("summary", "N/A"))
    top_for_ai.loc[index, "操作建议"] = str(analysis.get("action", "N/A"))


# =========================
# 最终 Top 10（中文化）
# =========================

final_top = top_for_ai.head(FINAL_TOP).copy()

# 加入中文化的列
final_top["评分等级"] = final_top["Score"].apply(score_to_stars)
final_top["趋势"] = final_top["Trend"].apply(trend_to_chinese)
final_top["动能"] = final_top["Momentum"].apply(momentum_to_chinese)
final_top["是否突破"] = final_top["Breakout"].apply(breakout_to_chinese)
final_top["AI建议"] = final_top["AI评级"].apply(rating_to_chinese)


# =========================
# 显示结果（终端）
# =========================

print(f"\n{'='*50}")
print(f"🏆 ========== ALPHAQUANT 今日精选 TOP {FINAL_TOP} ==========")
print(f"{'='*50}\n")

display_cols = [
    "Rank", "Symbol", "Close", "Score", "评分等级",
    "趋势", "动能", "是否突破",
    "AI建议", "信心度", "买入价", "止损价", "目标价"
]

print(final_top[display_cols].to_string(index=False))

print(f"\n{'='*50}")
print(f"\n📝 AI 一句话总结：\n")

for _, row in final_top.iterrows():
    print(f"   {row['Rank']}. {row['Symbol']} (${row['Close']})")
    print(f"      💡 {row['一句话总结']}")
    print(f"      🎯 {row['操作建议']}")
    print()


# =========================
# 准备 Google Sheet 数据（小白友好版）
# =========================

sheet_data = final_top[[
    "Rank", "Symbol", "Close", "Score", "评分等级",
    "趋势", "动能", "是否突破",
    "AI建议", "信心度", "风险等级",
    "买入价", "止损价", "目标价",
    "一句话总结", "操作建议"
]].copy()

# 重命名列（让 Google Sheet 更好看）
sheet_data.columns = [
    "排名", "股票代码", "现价($)", "综合评分", "评分等级",
    "趋势方向", "上涨动能", "是否突破阻力",
    "AI建议", "AI信心度(%)", "风险等级",
    "建议买入价($)", "止损价($)", "目标价($)",
    "一句话总结", "具体操作建议"
]


# =========================
# 保存结果
# =========================

result.to_csv(FULL_OUTPUT_FILE, index=False)
final_top.to_csv(OUTPUT_FILE, index=False)
top_for_ai.to_csv("output/top_ai_full.csv", index=False)


# =========================
# Google Sheet 输出
# =========================

print(f"\n📤 正在更新 Google Sheet...\n")

try:

    gs = GoogleSheet()

    # 写入精选 Top 10（小白友好版）
    gs.update("AlphaQuant", sheet_data, "今日精选")

    # 也写入完整 AI 分析结果
    ai_full_sheet = top_for_ai[[
        "Rank", "Symbol", "Close", "Score",
        "Trend", "Momentum", "Breakout",
        "AI评级", "信心度", "风险等级",
        "买入价", "止损价", "目标价",
        "一句话总结", "操作建议"
    ]].copy()

    ai_full_sheet.columns = [
        "排名", "股票代码", "现价($)", "综合评分",
        "趋势", "动能", "突破",
        "AI评级", "信心度(%)", "风险等级",
        "买入价($)", "止损价($)", "目标价($)",
        "一句话总结", "操作建议"
    ]

    gs.update("AlphaQuant", ai_full_sheet, "AI完整分析")

except Exception as e:

    print(f"⚠️ Google Sheet 跳过: {e}")
    print(f"   （如果还没设置 credentials.json，这是正常的）")


# =========================
# 完成
# =========================

print(f"\n{'='*50}")
print(f"📁 全部扫描结果: {FULL_OUTPUT_FILE}")
print(f"📁 AI 完整分析: output/top_ai_full.csv")
print(f"📁 今日精选 Top {FINAL_TOP}: {OUTPUT_FILE}")
print(f"{'='*50}")
print(f"\n✅ AlphaQuant 今日扫描完成！打开 Google Sheet 查看结果 📱\n")


# =========================
# Telegram 推送
# =========================

print(f"\n📱 正在推送到 Telegram...\n")

try:

    from modules.telegram import TelegramBot

    bot = TelegramBot()
    message = bot.format_top10(final_top)
    bot.send(message)

except Exception as e:

    print(f"⚠️ Telegram 跳过: {e}")

