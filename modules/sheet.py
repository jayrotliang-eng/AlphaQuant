
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd


class GoogleSheet:

    def __init__(self):

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=scopes
        )

        self.client = gspread.authorize(creds)

    def update(self, spreadsheet_name, df, worksheet_name="Top10"):
        """
        将 DataFrame 写入 Google Sheet

        参数：
        - spreadsheet_name: Google Sheet 名称（例如 "AlphaQuant"）
        - df: 要写入的 DataFrame
        - worksheet_name: 工作表名称
        """

        try:

            # 打开 Google Sheet
            sh = self.client.open(spreadsheet_name)

            # 尝试打开工作表，不存在则建立
            try:
                worksheet = sh.worksheet(worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sh.add_worksheet(
                    title=worksheet_name,
                    rows=100,
                    cols=30
                )

            # 清空旧数据
            worksheet.clear()

            # 写入表头 + 数据
            data = [df.columns.tolist()] + df.values.tolist()

            worksheet.update(
                range_name="A1",
                values=data
            )

            print(f"✅ Google Sheet 已更新: {spreadsheet_name} → {worksheet_name}")
            print(f"   写入 {len(df)} 行数据")

            return True

        except Exception as e:

            print(f"❌ Google Sheet 更新失败: {e}")
            return False

    def update_multiple(self, spreadsheet_name, sheets_dict):
        """
        写入多个工作表

        参数：
        - spreadsheet_name: Google Sheet 名称
        - sheets_dict: {"工作表名": DataFrame, ...}
        """

        for sheet_name, df in sheets_dict.items():
            self.update(spreadsheet_name, df, sheet_name)

