
import os
import json
import gspread
from google.oauth2.service_account import Credentials


class GoogleSheet:

    def __init__(self):

        # 找到 JSON 密钥文件
        creds_file = None

        # 方法1: 从环境变量读取路径
        if os.getenv("GOOGLE_CREDS_FILE"):
            creds_file = os.getenv("GOOGLE_CREDS_FILE")

        # 方法2: 自动搜索 JSON 文件
        if not creds_file:
            for f in os.listdir("."):
                if f.endswith(".json") and "gen-lang" in f:
                    creds_file = f
                    break

        if not creds_file:
            raise FileNotFoundError("找不到 Google Cloud 密钥文件")

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        self.gc = gspread.authorize(creds)

    def update(self, spreadsheet_name, df, sheet_name="今日精选"):
        """
        更新 Google Sheet 并美化格式
        """

        try:

            spreadsheet = self.gc.open(spreadsheet_name)

        except gspread.SpreadsheetNotFound:
            raise Exception(f"找不到名为 '{spreadsheet_name}' 的 Google Sheet，请确认已分享给 service account")

        # 找到或建立 worksheet
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=30)

        # 清空旧数据
        worksheet.clear()

        # 写入数据
        data = [df.columns.tolist()] + df.values.tolist()
        worksheet.update(range_name="A1", values=data)

        # =========================
        # 美化格式
        # =========================

        self._format_sheet(spreadsheet, worksheet, df)

        print(f"   ✅ Google Sheet '{sheet_name}' 已更新并美化")

    def _format_sheet(self, spreadsheet, worksheet, df):
        """
        美化 Google Sheet：颜色、宽度、对齐、冻结等
        """

        sheet_id = worksheet.id
        num_rows = len(df) + 1  # +1 for header
        num_cols = len(df.columns)

        requests = []

        # =========================
        # 1. 冻结首行（表头固定）
        # =========================
        requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        })

        # =========================
        # 2. 表头样式：深蓝底 + 白字 + 粗体
        # =========================
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.13,
                            "green": 0.22,
                            "blue": 0.42
                        },
                        "textFormat": {
                            "foregroundColor": {
                                "red": 1.0,
                                "green": 1.0,
                                "blue": 1.0
                            },
                            "bold": True,
                            "fontSize": 10
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
            }
        })

        # =========================
        # 3. 数据区域：居中对齐 + 字体
        # =========================
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": num_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {
                            "fontSize": 10
                        }
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment,textFormat)"
            }
        })

        # =========================
        # 4. 交替行颜色（斑马线）
        # =========================
        requests.append({
            "addBanding": {
                "bandedRange": {
                    "sheetId": sheet_id,
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": num_rows,
                        "startColumnIndex": 0,
                        "endColumnIndex": num_cols
                    },
                    "rowProperties": {
                        "headerColor": {
                            "red": 0.13,
                            "green": 0.22,
                            "blue": 0.42
                        },
                        "firstBandColor": {
                            "red": 1.0,
                            "green": 1.0,
                            "blue": 1.0
                        },
                        "secondBandColor": {
                            "red": 0.93,
                            "green": 0.95,
                            "blue": 0.98
                        }
                    }
                }
            }
        })

        # =========================
        # 5. 自动调整列宽
        # =========================
        # 短列（排名、评分、价格等）
        short_cols = self._find_columns(df, ["排名", "综合评分", "AI信心度(%)", "风险等级"])
        for col_idx in short_cols:
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": col_idx,
                        "endIndex": col_idx + 1
                    },
                    "properties": {"pixelSize": 80},
                    "fields": "pixelSize"
                }
            })

        # 中等列（股票代码、现价、买入价等）
        medium_cols = self._find_columns(df, [
            "股票代码", "现价($)", "评分等级", "趋势方向",
            "上涨动能", "是否突破阻力", "估值水平", "成长性",
            "财务健康", "新闻情绪", "AI建议", "建议持有周期",
            "建议买入价($)", "止损价($)", "目标价($)", "关注清单"
        ])
        for col_idx in medium_cols:
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": col_idx,
                        "endIndex": col_idx + 1
                    },
                    "properties": {"pixelSize": 120},
                    "fields": "pixelSize"
                }
            })

        # 长列（总结、建议、事件等）
        long_cols = self._find_columns(df, [
            "所属行业", "近期关键事件", "一句话总结", "具体操作建议"
        ])
        for col_idx in long_cols:
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": col_idx,
                        "endIndex": col_idx + 1
                    },
                    "properties": {"pixelSize": 280},
                    "fields": "pixelSize"
                }
            })

        # =========================
        # 6. 行高
        # =========================
        # 表头
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": 1
                },
                "properties": {"pixelSize": 36},
                "fields": "pixelSize"
            }
        })
        # 数据行
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": num_rows
                },
                "properties": {"pixelSize": 30},
                "fields": "pixelSize"
            }
        })

        # =========================
        # 7. 条件格式：AI建议用颜色区分
        # =========================
        ai_col = self._find_column_index(df, "AI建议")
        if ai_col is not None:

            # Strong Buy / 强力买入 = 深绿
            requests.append(self._conditional_format(
                sheet_id, 1, num_rows, ai_col, ai_col + 1,
                "建议买入",
                {"red": 0.2, "green": 0.66, "blue": 0.33},
                {"red": 1.0, "green": 1.0, "blue": 1.0}
            ))

            # Hold / 持有 = 橙色
            requests.append(self._conditional_format(
                sheet_id, 1, num_rows, ai_col, ai_col + 1,
                "持有观望",
                {"red": 0.98, "green": 0.74, "blue": 0.18},
                {"red": 0.0, "green": 0.0, "blue": 0.0}
            ))

            # Sell = 红色
            requests.append(self._conditional_format(
                sheet_id, 1, num_rows, ai_col, ai_col + 1,
                "建议卖出",
                {"red": 0.9, "green": 0.2, "blue": 0.2},
                {"red": 1.0, "green": 1.0, "blue": 1.0}
            ))

        # =========================
        # 8. 风险等级颜色
        # =========================
        risk_col = self._find_column_index(df, "风险等级")
        if risk_col is not None:

            # 低风险 = 绿
            requests.append(self._conditional_format(
                sheet_id, 1, num_rows, risk_col, risk_col + 1,
                "低风险",
                {"red": 0.85, "green": 0.95, "blue": 0.85},
                {"red": 0.13, "green": 0.55, "blue": 0.13}
            ))

            # 中风险 = 黄
            requests.append(self._conditional_format(
                sheet_id, 1, num_rows, risk_col, risk_col + 1,
                "中风险",
                {"red": 1.0, "green": 0.96, "blue": 0.81},
                {"red": 0.7, "green": 0.53, "blue": 0.0}
            ))

            # 高风险 = 红
            requests.append(self._conditional_format(
                sheet_id, 1, num_rows, risk_col, risk_col + 1,
                "高风险",
                {"red": 1.0, "green": 0.85, "blue": 0.85},
                {"red": 0.8, "green": 0.1, "blue": 0.1}
            ))

        # =========================
        # 9. 边框
        # =========================
        requests.append({
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": num_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols
                },
                "top": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                "bottom": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                "left": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                "right": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                "innerHorizontal": {"style": "SOLID", "color": {"red": 0.9, "green": 0.9, "blue": 0.9}},
                "innerVertical": {"style": "SOLID", "color": {"red": 0.9, "green": 0.9, "blue": 0.9}}
            }
        })

        # =========================
        # 执行所有格式化
        # =========================

        try:
            spreadsheet.batch_update({"requests": requests})
        except Exception as e:
            print(f"   ⚠️ 部分格式化失败（数据已写入）: {str(e)[:60]}")

    def _find_columns(self, df, col_names):
        """找出指定列名的索引"""
        indices = []
        for name in col_names:
            if name in df.columns:
                indices.append(df.columns.tolist().index(name))
        return indices

    def _find_column_index(self, df, col_name):
        """找出单个列名的索引"""
        if col_name in df.columns:
            return df.columns.tolist().index(col_name)
        return None

    def _conditional_format(self, sheet_id, start_row, end_row, start_col, end_col, text, bg_color, text_color):
        """生成条件格式请求"""
        return {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_CONTAINS",
                            "values": [{"userEnteredValue": text}]
                        },
                        "format": {
                            "backgroundColor": bg_color,
                            "textFormat": {
                                "foregroundColor": text_color,
                                "bold": True
                            }
                        }
                    }
                },
                "index": 0
            }
        }

