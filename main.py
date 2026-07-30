
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
    FULL_OUTPUT_FILE
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

print(f"\n📊 AlphaQuant V2")
print(f"   股票池: {len(symbols)} 支")
print(f"   最低分数: {MIN_SCORE}")
print(f"   AI 分析: Top {AI_TOP}")
print(f"   最终输出: Top {FINAL_TOP}")
print(f"\n{'='*50}\n")


# =========================
# 扫描全部股票
# =========================

print("🔍 开始扫描...\n")

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
    print(f"✅ 扫描完成")
    print(f"   总扫描: {len(result)} 支")
    print(f"   达标 (≥{MIN_SCORE}分): {len(qualified)} 支")
    print(f"{'='*50}\n")

else:

    print("❌ 没有扫描结果")
    exit()


# =========================
# AI 分析 Top N
# =========================

top_for_ai = result.head(AI_TOP).copy()

# 预先建立 AI 列（避免类型冲突）
top_for_ai["AI_Rating"] = ""
top_for_ai["AI_Confidence"] = 0
top_for_ai["AI_Risk"] = ""
top_for_ai["AI_Entry"] = ""
top_for_ai["AI_StopLoss"] = ""
top_for_ai["AI_Target"] = ""
top_for_ai["AI_Summary"] = ""

print(f"🤖 AI 正在分析 Top {len(top_for_ai)} 支...\n")

ai = AIAnalyzer()

for index, row in top_for_ai.iterrows():

    print(f"   分析中: {row['Symbol']}...")

    analysis = ai.analyze(row)

    top_for_ai.loc[index, "AI_Rating"] = str(analysis.get("rating", "N/A"))
    top_for_ai.loc[index, "AI_Confidence"] = analysis.get("confidence", 0)
    top_for_ai.loc[index, "AI_Risk"] = str(analysis.get("risk", "N/A"))
    top_for_ai.loc[index, "AI_Entry"] = str(analysis.get("entry", "N/A"))
    top_for_ai.loc[index, "AI_StopLoss"] = str(analysis.get("stoploss", "N/A"))
    top_for_ai.loc[index, "AI_Target"] = str(analysis.get("target", "N/A"))
    top_for_ai.loc[index, "AI_Summary"] = str(analysis.get("summary", "N/A"))


# =========================
# 最终 Top 10
# =========================

final_top = top_for_ai.head(FINAL_TOP)


# =========================
# 显示结果
# =========================

print(f"\n{'='*50}")
print(f"========== ALPHAQUANT TOP {FINAL_TOP} ==========")
print(f"{'='*50}\n")

print(
    final_top[[
        "Rank", "Symbol", "Close", "Score",
        "Trend", "Momentum", "Breakout",
        "AI_Rating", "AI_Confidence",
        "AI_Entry", "AI_StopLoss", "AI_Target"
    ]].to_string(index=False)
)


# =========================
# 保存结果
# =========================

result.to_csv(FULL_OUTPUT_FILE, index=False)

final_top.to_csv(OUTPUT_FILE, index=False)

top_for_ai.to_csv("output/top_ai_full.csv", index=False)


# =========================
# Google Sheet 输出
# =========================

print("\n📤 正在更新 Google Sheet...\n")

try:

    gs = GoogleSheet()

    # 准备输出数据（精简版，适合手机查看）
    sheet_data = final_top[[
        "Rank", "Symbol", "Close", "Score",
        "Trend", "Momentum", "Breakout",
        "AI_Rating", "AI_Confidence",
        "AI_Entry", "AI_StopLoss", "AI_Target",
        "AI_Summary"
    ]].copy()

    # 写入 Google Sheet
    gs.update("AlphaQuant", sheet_data, "Top10")

    # 也写入完整 AI 分析结果
    gs.update("AlphaQuant", top_for_ai, "AI_Full")

except Exception as e:

    print(f"⚠️ Google Sheet 跳过: {e}")
    print("   （如果还没设置 credentials.json，这是正常的）")


# =========================
# 完成
# =========================

print(f"\n{'='*50}")
print(f"📁 全部扫描结果: {FULL_OUTPUT_FILE}")
print(f"📁 AI 分析完整: output/top_ai_full.csv")
print(f"📁 最终 Top {FINAL_TOP}: {OUTPUT_FILE}")
print(f"{'='*50}")
print(f"\n✅ AlphaQuant 扫描完成！\n")

