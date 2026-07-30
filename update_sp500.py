
import pandas as pd
import requests
import os


def update_sp500():

    url = (
        "https://raw.githubusercontent.com/"
        "datasets/s-and-p-500-companies/"
        "main/data/constituents.csv"
    )

    print("正在下载 S&P500 成分股...")

    try:

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        os.makedirs("data", exist_ok=True)

        with open("data/sp500_raw.csv", "w") as f:
            f.write(response.text)

        df = pd.read_csv("data/sp500_raw.csv")

        if "Symbol" in df.columns:
            symbols = df[["Symbol"]].copy()
        elif "symbol" in df.columns:
            symbols = df[["symbol"]].rename(
                columns={"symbol": "Symbol"}
            )
        else:
            print(f"❌ 无法识别 Symbol 列: {df.columns.tolist()}")
            return

        # 清理（BRK.B → BRK-B）
        symbols["Symbol"] = (
            symbols["Symbol"]
            .str.replace(".", "-", regex=False)
            .str.strip()
        )

        symbols = symbols.drop_duplicates()

        symbols.to_csv("data/sp500.csv", index=False)

        print(f"✅ S&P500 成分股已更新")
        print(f"   总数: {len(symbols)} 支")
        print(f"   保存: data/sp500.csv")

    except Exception as e:
        print(f"❌ 下载失败: {e}")


if __name__ == "__main__":
    update_sp500()

