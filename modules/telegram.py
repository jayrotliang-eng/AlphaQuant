
import os
import requests


class TelegramBot:

    def __init__(self):

        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send(self, message):
        """发送消息到 Telegram"""

        if not self.token or not self.chat_id:
            print("⚠️ Telegram 跳过: 未设置 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID")
            return False

        try:

            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            response = requests.post(url, json=payload)

            if response.status_code == 200:
                print("✅ Telegram 推送成功！")
                return True
            else:
                print(f"⚠️ Telegram 推送失败: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Telegram 推送失败: {e}")
            return False

    def format_top10(self, df):
        """把 Top 10 结果格式化成 Telegram 消息"""

        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")

        msg = f"🏆 <b>AlphaQuant 今日精选</b>\n"
        msg += f"📅 {today}\n"
        msg += f"{'─' * 30}\n\n"

        for _, row in df.iterrows():

            rank = row.get("Rank", "")
            symbol = row.get("Symbol", "")
            close = row.get("Close", "")
            score = row.get("Score", "")
            ai_rating = row.get("AI评级", row.get("AI_Rating", ""))
            entry = row.get("买入价", row.get("AI_Entry", ""))
            stoploss = row.get("止损价", row.get("AI_StopLoss", ""))
            target = row.get("目标价", row.get("AI_Target", ""))
            summary = row.get("一句话总结", "")
            risk = row.get("风险等级", "")

            msg += f"<b>{rank}. {symbol}</b> — ${close}\n"
            msg += f"   评分: {score} | AI: {ai_rating}\n"

            if risk:
                msg += f"   风险: {risk}\n"

            msg += f"   💰 买入: ${entry} → 目标: ${target}\n"
            msg += f"   🛑 止损: ${stoploss}\n"

            if summary:
                msg += f"   💡 {summary}\n"

            msg += f"\n"

        msg += f"{'─' * 30}\n"
        msg += f"📊 扫描 S&P500 全部 ~500 支\n"
        msg += f"🤖 AI 深度分析前 30 名\n"
        msg += f"✅ 精选 Top 10 推送给你\n"

        return msg

