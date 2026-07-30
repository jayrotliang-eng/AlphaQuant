import ta

class Technical:

    def calculate(self, df):

        df["EMA20"] = ta.trend.ema_indicator(df["Close"], window=20)

        df["EMA50"] = ta.trend.ema_indicator(df["Close"], window=50)

        df["EMA200"] = ta.trend.ema_indicator(df["Close"], window=200)

        df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

        macd = ta.trend.MACD(df["Close"])

        df["MACD"] = macd.macd()

        df["MACD_SIGNAL"] = macd.macd_signal()

                # 成交量20日均线
        df["VOL20"] = df["Volume"].rolling(20).mean()

        # 20日最高价
        df["HIGH20"] = df["High"].rolling(20).max().shift(1)

        # ATR
        df["ATR"] = ta.volatility.average_true_range(
            df["High"],
            df["Low"],
            df["Close"],
            window=14
        )

        # ADX
        df["ADX"] = ta.trend.adx(
            df["High"],
            df["Low"],
            df["Close"],
            window=14
        )

        return df