"""
backtest.py
-----------
Minimal backtest harness: replays each signal from structure_analysis.py
forward through the price data to see whether the Stop-Loss or the
Take-Profit is hit first, then reports aggregate performance.

This is a simplified backtester (no spread/slippage/commission modeling,
one open trade assumed independent of others). It is meant to sanity-check
the signal logic, not to certify a strategy as profitable.
"""

from dataclasses import dataclass
from typing import List
import pandas as pd

from structure_analysis import generate_signals, Signal
from position_sizing import calculate_lot_size


@dataclass
class TradeResult:
    signal: Signal
    outcome: str          # "win", "loss", or "open" (ran off the end of data)
    exit_price: float
    r_multiple: float      # realised risk multiple, e.g. +2.0R, -1.0R


def simulate_trade(df: pd.DataFrame, signal: Signal, max_lookahead: int = 60) -> TradeResult:
    entry_idx = signal.index
    end_idx = min(entry_idx + max_lookahead, len(df) - 1)

    for i in range(entry_idx + 1, end_idx + 1):
        row = df.iloc[i]
        if signal.direction == "buy":
            hit_sl = row["low"] <= signal.stop_loss
            hit_tp = row["high"] >= signal.take_profit
        else:
            hit_sl = row["high"] >= signal.stop_loss
            hit_tp = row["low"] <= signal.take_profit

        # Conservative assumption: if both could have been touched in the
        # same candle, count it as the loss (worst case).
        if hit_sl and hit_tp:
            return TradeResult(signal, "loss", signal.stop_loss, -1.0)
        if hit_sl:
            return TradeResult(signal, "loss", signal.stop_loss, -1.0)
        if hit_tp:
            r = abs(signal.take_profit - signal.entry) / abs(signal.entry - signal.stop_loss)
            return TradeResult(signal, "win", signal.take_profit, r)

    return TradeResult(signal, "open", df.iloc[end_idx]["close"], 0.0)


def run_backtest(
    df: pd.DataFrame,
    account_balance: float = 40.0,
    risk_percent: float = 1.0,
    pip_value_per_lot: float = 1.0,
) -> None:
    signals = generate_signals(df)
    results: List[TradeResult] = [simulate_trade(df, s) for s in signals]

    closed = [r for r in results if r.outcome in ("win", "loss")]
    wins = [r for r in closed if r.outcome == "win"]
    losses = [r for r in closed if r.outcome == "loss"]

    balance = account_balance
    equity_curve = [balance]

    for r in closed:
        sl_distance = abs(r.signal.entry - r.signal.stop_loss)
        lot = calculate_lot_size(balance, risk_percent, sl_distance, pip_value_per_lot)
        risk_amount = balance * (risk_percent / 100.0)
        pnl = risk_amount * r.r_multiple
        balance += pnl
        equity_curve.append(balance)

    win_rate = (len(wins) / len(closed) * 100) if closed else 0.0
    avg_r = sum(r.r_multiple for r in closed) / len(closed) if closed else 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        max_dd = max(max_dd, (peak - e) / peak * 100)

    print("=== Backtest report ===")
    print(f"Signals generated:   {len(signals)}")
    print(f"Trades closed:       {len(closed)}  ({len(wins)} win / {len(losses)} loss)")
    print(f"Win rate:            {win_rate:.1f}%")
    print(f"Average R multiple:  {avg_r:+.2f}R")
    print(f"Starting balance:    ${account_balance:.2f}")
    print(f"Ending balance:      ${balance:.2f}")
    print(f"Max drawdown:        {max_dd:.1f}%")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_data/XAUUSD_H4_sample.csv"
    data = pd.read_csv(path, parse_dates=["time"])
    run_backtest(data)
