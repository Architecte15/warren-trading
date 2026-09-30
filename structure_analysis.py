"""
structure_analysis.py
----------------------
Market structure and price-action detection for the MASTERY TRIADE
EMPIRE discretionary framework, applied to OHLC data (designed for
H4/Daily candles on XAU/USD or EUR/USD, exported from MetaTrader 5).

Implements:
    - Swing high / swing low detection (fractal-based)
    - Points of Interest (POI): support/resistance zones from swing clusters
    - Liquidity sweep detection (wick pierces a zone, close comes back inside)
    - Pinbar / rejection candle detection
    - Bullish / bearish engulfing detection

Expected input: a pandas DataFrame with columns
    ["time", "open", "high", "low", "close"]
sorted in ascending chronological order.
"""

from dataclasses import dataclass, field
from typing import List, Literal
import pandas as pd


@dataclass
class Zone:
    price_low: float
    price_high: float
    kind: Literal["support", "resistance"]
    touches: int = 1


@dataclass
class Signal:
    index: int
    time: object
    direction: Literal["buy", "sell"]
    reason: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float


def detect_swing_points(df: pd.DataFrame, lookback: int = 3) -> pd.DataFrame:
    """
    Fractal-based swing high/low detection: a candle is a swing high if
    its high is the highest within `lookback` candles on both sides
    (same logic for swing lows).
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    is_swing_high = [False] * n
    is_swing_low = [False] * n

    for i in range(lookback, n - lookback):
        window_high = highs[i - lookback: i + lookback + 1]
        window_low = lows[i - lookback: i + lookback + 1]
        if highs[i] == max(window_high):
            is_swing_high[i] = True
        if lows[i] == min(window_low):
            is_swing_low[i] = True

    out = df.copy()
    out["swing_high"] = is_swing_high
    out["swing_low"] = is_swing_low
    return out


def build_poi_zones(df: pd.DataFrame, tolerance_pct: float = 0.15) -> List[Zone]:
    """
    Cluster swing highs into resistance zones and swing lows into
    support zones. `tolerance_pct` controls how close two swing points
    must be (as a % of price) to be merged into the same zone.
    """
    zones: List[Zone] = []

    def cluster(prices: List[float], kind: str):
        sorted_prices = sorted(prices)
        for p in sorted_prices:
            merged = False
            for z in zones:
                if z.kind != kind:
                    continue
                mid = (z.price_low + z.price_high) / 2
                if abs(p - mid) / mid * 100 <= tolerance_pct:
                    z.price_low = min(z.price_low, p)
                    z.price_high = max(z.price_high, p)
                    z.touches += 1
                    merged = True
                    break
            if not merged:
                zones.append(Zone(price_low=p, price_high=p, kind=kind))

    swing_highs = df.loc[df["swing_high"], "high"].tolist()
    swing_lows = df.loc[df["swing_low"], "low"].tolist()
    cluster(swing_highs, "resistance")
    cluster(swing_lows, "support")

    # Only keep zones touched at least twice -> stronger POIs
    return [z for z in zones if z.touches >= 2]


def is_pinbar(row: pd.Series, wick_body_ratio: float = 2.0) -> Literal["bullish", "bearish", None]:
    body = abs(row["close"] - row["open"])
    upper_wick = row["high"] - max(row["close"], row["open"])
    lower_wick = min(row["close"], row["open"]) - row["low"]

    if body == 0:
        return None
    if lower_wick >= body * wick_body_ratio and lower_wick > upper_wick:
        return "bullish"   # long lower wick -> rejection of lower prices
    if upper_wick >= body * wick_body_ratio and upper_wick > lower_wick:
        return "bearish"   # long upper wick -> rejection of higher prices
    return None


def is_engulfing(prev: pd.Series, curr: pd.Series) -> Literal["bullish", "bearish", None]:
    prev_bearish = prev["close"] < prev["open"]
    prev_bullish = prev["close"] > prev["open"]
    curr_bullish = curr["close"] > curr["open"]
    curr_bearish = curr["close"] < curr["open"]

    if prev_bearish and curr_bullish:
        if curr["close"] >= prev["open"] and curr["open"] <= prev["close"]:
            return "bullish"
    if prev_bullish and curr_bearish:
        if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
            return "bearish"
    return None


def detect_liquidity_sweep(row: pd.Series, zone: Zone) -> bool:
    """
    A liquidity sweep on a support zone: the candle's low pierces below
    the zone but the close comes back above it (stop hunt then reversal).
    Symmetric logic applies to resistance zones.
    """
    if zone.kind == "support":
        return row["low"] < zone.price_low and row["close"] > zone.price_low
    else:
        return row["high"] > zone.price_high and row["close"] < zone.price_high


def generate_signals(
    df: pd.DataFrame,
    min_risk_reward: float = 2.0,
    swing_lookback: int = 3,
    zone_tolerance_pct: float = 0.15,
) -> List[Signal]:
    """
    Combine structure (POI + liquidity sweep) with a confirmation
    candle (pinbar or engulfing) to produce trade signals.
    This is a research/educational baseline -- tune thresholds against
    your own backtests before using it live.
    """
    structured = detect_swing_points(df, lookback=swing_lookback)
    zones = build_poi_zones(structured, tolerance_pct=zone_tolerance_pct)
    signals: List[Signal] = []

    for i in range(1, len(structured)):
        row = structured.iloc[i]
        prev_row = structured.iloc[i - 1]

        for zone in zones:
            if not detect_liquidity_sweep(row, zone):
                continue

            pin = is_pinbar(row)
            eng = is_engulfing(prev_row, row)
            confirmation = pin or eng

            if zone.kind == "support" and confirmation == "bullish":
                entry = row["close"]
                stop_loss = row["low"] - (row["high"] - row["low"]) * 0.1
                risk = entry - stop_loss
                take_profit = entry + risk * min_risk_reward
                signals.append(Signal(
                    index=i, time=row.get("time", i), direction="buy",
                    reason=f"Liquidity sweep + {confirmation} confirmation on support",
                    entry=entry, stop_loss=stop_loss, take_profit=take_profit,
                    risk_reward=min_risk_reward,
                ))

            if zone.kind == "resistance" and confirmation == "bearish":
                entry = row["close"]
                stop_loss = row["high"] + (row["high"] - row["low"]) * 0.1
                risk = stop_loss - entry
                take_profit = entry - risk * min_risk_reward
                signals.append(Signal(
                    index=i, time=row.get("time", i), direction="sell",
                    reason=f"Liquidity sweep + {confirmation} confirmation on resistance",
                    entry=entry, stop_loss=stop_loss, take_profit=take_profit,
                    risk_reward=min_risk_reward,
                ))

    return signals


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_data/XAUUSD_H4_sample.csv"
    data = pd.read_csv(path, parse_dates=["time"])
    sigs = generate_signals(data)
    print(f"Loaded {len(data)} candles, found {len(sigs)} signal(s).\n")
    for s in sigs[:10]:
        print(f"[{s.time}] {s.direction.upper():4} entry={s.entry:.2f} "
              f"SL={s.stop_loss:.2f} TP={s.take_profit:.2f} — {s.reason}")
