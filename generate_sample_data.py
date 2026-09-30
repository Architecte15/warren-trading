"""
generate_sample_data.py
------------------------
Generates a synthetic H4 OHLC CSV (random-walk with a few engineered
bounces off round levels) purely so the rest of the codebase can be
run and tested end-to-end without needing a real MT5 export first.

Replace with real exported data before drawing any trading conclusions:
MT5 -> right-click chart -> "Export candles to CSV" (or via the
MetaTrader Python API) on XAU/USD or EUR/USD, H4 or Daily timeframe.
"""

import csv
import random
from datetime import datetime, timedelta


def generate(path: str, n_candles: int = 500, start_price: float = 4300.0, seed: int = 42):
    random.seed(seed)
    price = start_price
    t = datetime(2026, 1, 1)
    rows = []

    for i in range(n_candles):
        drift = random.uniform(-1.2, 1.2)
        volatility = random.uniform(2.0, 8.0)

        open_p = price
        close_p = open_p + drift + random.uniform(-volatility, volatility) * 0.3
        high_p = max(open_p, close_p) + random.uniform(0.5, volatility)
        low_p = min(open_p, close_p) - random.uniform(0.5, volatility)

        # Occasionally engineer a "sweep and reject" near round 50-levels
        # to make the sample data actually produce a few signals.
        nearest_round = round(price / 50) * 50
        if abs(price - nearest_round) < 6 and random.random() < 0.25:
            if close_p > nearest_round:
                low_p = nearest_round - random.uniform(1, 4)
                close_p = nearest_round + random.uniform(2, 6)
            else:
                high_p = nearest_round + random.uniform(1, 4)
                close_p = nearest_round - random.uniform(2, 6)

        rows.append([
            (t + timedelta(hours=4 * i)).strftime("%Y-%m-%d %H:%M"),
            round(open_p, 2), round(high_p, 2), round(low_p, 2), round(close_p, 2),
        ])
        price = close_p

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "open", "high", "low", "close"])
        writer.writerows(rows)

    print(f"Wrote {n_candles} synthetic candles to {path}")


if __name__ == "__main__":
    import os
    os.makedirs("sample_data", exist_ok=True)
    generate("sample_data/XAUUSD_H4_sample.csv")
