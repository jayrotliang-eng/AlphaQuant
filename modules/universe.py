import pandas as pd


class Universe:

    def __init__(self):

        self.sp500 = "data/sp500.csv"

    def get_symbols(self):

        df = pd.read_csv(self.sp500)

        return df["Symbol"].tolist()

    def count(self):

        return len(self.get_symbols())