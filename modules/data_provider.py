import yfinance as yf

class DataProvider:

    def get_history(self, symbol, period="2y"):

        stock = yf.Ticker(symbol)

        df = stock.history(period=period)

        df.reset_index(inplace=True)

        return df