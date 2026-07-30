import pandas as pd
from modules.data_provider import DataProvider
from modules.technical import Technical


class Scoring:

    def calculate(self, row):

        score = 0

        # 1. EMA 多头排列：20分
        if (
            pd.notna(row["EMA20"])
            and pd.notna(row["EMA50"])
            and pd.notna(row["EMA200"])
        ):
            if row["EMA20"] > row["EMA50"] > row["EMA200"]:
                score += 20

        # 2. RSI：15分
        if pd.notna(row["RSI"]):
            if 45 <= row["RSI"] <= 65:
                score += 15

        # 3. MACD：15分
        if (
            pd.notna(row["MACD"])
            and pd.notna(row["MACD_SIGNAL"])
        ):
            if row["MACD"] > row["MACD_SIGNAL"]:
                score += 15

        # 4. 成交量：15分
        if (
            pd.notna(row["Volume"])
            and pd.notna(row["VOL20"])
        ):
            if row["Volume"] > row["VOL20"]:
                score += 15

        # 5. 突破过去20日高点：15分
        if (
            pd.notna(row["HIGH20"])
            and row["Close"] > row["HIGH20"]
        ):
            score += 15

        # 6. ADX：10分
        if pd.notna(row["ADX"]):
            if row["ADX"] >= 25:
                score += 10

        # 7. ATR：10分
        if (
            pd.notna(row["ATR"])
            and row["ATR"] > row["Close"] * 0.02
        ):
            score += 10

        return score


class Scanner:

    def __init__(self):

        self.provider = DataProvider()
        self.technical = Technical()
        self.scoring = Scoring()

    def scan(self, symbols):

        result = []

        for symbol in symbols:

            try:

                df = self.provider.get_history(symbol)

                if df.empty:
                    continue

                df = self.technical.calculate(df)

                latest = df.iloc[-1]

                score = self.scoring.calculate(latest)

                # =========================
                # Trend
                # =========================

                if (
                    pd.notna(latest["EMA20"])
                    and pd.notna(latest["EMA50"])
                    and pd.notna(latest["EMA200"])
                ):

                    if (
                        latest["EMA20"]
                        > latest["EMA50"]
                        > latest["EMA200"]
                    ):
                        trend = "Bull"

                    elif (
                        latest["EMA20"]
                        < latest["EMA50"]
                        < latest["EMA200"]
                    ):
                        trend = "Bear"

                    else:
                        trend = "Neutral"

                else:

                    trend = "Unknown"

                # =========================
                # Momentum
                # =========================

                if (
                    pd.notna(latest["MACD"])
                    and pd.notna(latest["MACD_SIGNAL"])
                ):

                    if latest["MACD"] > latest["MACD_SIGNAL"]:
                        momentum = "Strong"

                    else:
                        momentum = "Weak"

                else:

                    momentum = "Unknown"

                # =========================
                # Breakout
                # =========================

                if (
                    pd.notna(latest["HIGH20"])
                    and latest["Close"] > latest["HIGH20"]
                ):
                    breakout = "Yes"

                else:
                    breakout = "No"

                # =========================
                # Volume
                # =========================

                if (
                    pd.notna(latest["Volume"])
                    and pd.notna(latest["VOL20"])
                    and latest["Volume"] > latest["VOL20"]
                ):
                    volume_signal = "High"

                else:
                    volume_signal = "Normal"

                # =========================
                # Risk
                # =========================

                if (
                    pd.notna(latest["ATR"])
                    and latest["Close"] > 0
                ):

                    atr_percent = (
                        latest["ATR"]
                        / latest["Close"]
                        * 100
                    )

                else:

                    atr_percent = None

                # =========================
                # Result
                # =========================

                result.append({

                    "Symbol": symbol,

                    "Close": round(
                        latest["Close"], 2
                    ),

                    "EMA20": round(
                        latest["EMA20"], 2
                    ),

                    "EMA50": round(
                        latest["EMA50"], 2
                    ),

                    "EMA200": round(
                        latest["EMA200"], 2
                    ),

                    "RSI": round(
                        latest["RSI"], 2
                    ),

                    "MACD": round(
                        latest["MACD"], 2
                    ),

                    "MACD_SIGNAL": round(
                        latest["MACD_SIGNAL"], 2
                    ),

                    "Volume": int(
                        latest["Volume"]
                    ),

                    "VOL20": round(
                        latest["VOL20"], 0
                    ),

                    "HIGH20": round(
                        latest["HIGH20"], 2
                    ),

                    "ATR": round(
                        latest["ATR"], 2
                    ),

                    "ATR_%": round(
                        atr_percent, 2
                    ) if atr_percent is not None else None,

                    "ADX": round(
                        latest["ADX"], 2
                    ),

                    "Trend": trend,

                    "Momentum": momentum,

                    "Breakout": breakout,

                    "VolumeSignal": volume_signal,

                    "Score": score

                })

            except Exception as e:

                print(
                    f"{symbol}: {e}"
                )

        result_df = pd.DataFrame(result)

        if not result_df.empty:

            result_df = result_df.sort_values(
                by=["Score", "RSI"],
                ascending=[False, False]
            )

            result_df = result_df.reset_index(
                drop=True
            )

            result_df.insert(
                0,
                "Rank",
                result_df.index + 1
            )

        return result_df

    def scan_top(
        self,
        symbols,
        top_n=10
    ):

        df = self.scan(symbols)

        if df.empty:
            return df

        return df.head(top_n)

    def scan_by_threshold(
        self,
        symbols,
        min_score=50
    ):

        df = self.scan(symbols)

        if df.empty:
            return df

        return df[
            df["Score"] >= min_score
        ].reset_index(drop=True)