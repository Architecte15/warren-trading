"""
position_sizing.py
-------------------
Risk-based position sizing for the Warren Trading system.

Core rule (per the MASTERY TRIADE EMPIRE risk framework):
    - Never risk more than 1-2% of account equity on a single trade.
    - Minimum accepted Risk:Reward ratio is 1:2.

IMPORTANT: `pip_value_per_lot` is broker- and instrument-specific.
For XAU/USD, conventions vary widely between brokers (cent accounts,
different contract sizes, etc.). Always confirm the exact pip value
for your account type in MetaTrader 5 (right-click the symbol ->
Specification) before trusting this for real capital.
"""

from dataclasses import dataclass
import math


@dataclass
class PositionSizeResult:
    lot_size: float
    risk_amount: float
    stop_loss_distance: float
    take_profit_distance: float
    risk_reward_ratio: float


def calculate_lot_size(
    account_balance: float,
    risk_percent: float,
    stop_loss_distance: float,
    pip_value_per_lot: float = 10.0,
    min_lot: float = 0.01,
    lot_step: float = 0.01,
    max_lot: float = 100.0,
) -> float:
    """
    Compute the lot size so that a full stop-loss hit costs exactly
    `risk_percent` of `account_balance`.

    stop_loss_distance: distance between entry and SL, expressed in the
        same unit as `pip_value_per_lot` (e.g. pips for EUR/USD, points
        for XAU/USD -- be consistent with your broker's quoting).
    pip_value_per_lot: monetary value of one pip/point move for 1.00 lot.
    """
    if stop_loss_distance <= 0:
        raise ValueError("stop_loss_distance must be positive")
    if not (0 < risk_percent <= 100):
        raise ValueError("risk_percent must be between 0 and 100")

    risk_amount = account_balance * (risk_percent / 100.0)
    raw_lot = risk_amount / (stop_loss_distance * pip_value_per_lot)

    # Round down to the nearest lot step so we never risk more than intended
    stepped_lot = math.floor(raw_lot / lot_step) * lot_step
    stepped_lot = round(stepped_lot, 2)

    return max(min(stepped_lot, max_lot), min_lot)


def build_trade_plan(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
    take_profit_price: float,
    pip_value_per_lot: float = 10.0,
    price_to_pip_factor: float = 1.0,
) -> PositionSizeResult:
    """
    Given entry/SL/TP prices, compute the lot size and validate the
    Risk:Reward ratio against the 1:2 minimum required by the strategy.

    price_to_pip_factor converts a raw price difference into "pips"
    (e.g. for EUR/USD with 5-digit quotes, 1 pip = 0.0001, so
    price_to_pip_factor = 10000; for XAU/USD in points, this is often 1).
    """
    sl_distance = abs(entry_price - stop_loss_price) * price_to_pip_factor
    tp_distance = abs(take_profit_price - entry_price) * price_to_pip_factor

    if sl_distance == 0:
        raise ValueError("Entry and Stop-Loss cannot be equal")

    rr_ratio = tp_distance / sl_distance

    lot_size = calculate_lot_size(
        account_balance=account_balance,
        risk_percent=risk_percent,
        stop_loss_distance=sl_distance,
        pip_value_per_lot=pip_value_per_lot,
    )

    risk_amount = account_balance * (risk_percent / 100.0)

    return PositionSizeResult(
        lot_size=lot_size,
        risk_amount=round(risk_amount, 2),
        stop_loss_distance=sl_distance,
        take_profit_distance=tp_distance,
        risk_reward_ratio=round(rr_ratio, 2),
    )


if __name__ == "__main__":
    # Example: $40 account, 2% risk, XAU/USD trade
    plan = build_trade_plan(
        account_balance=40.0,
        risk_percent=2.0,
        entry_price=4350.00,
        stop_loss_price=4340.00,
        take_profit_price=4370.00,
        pip_value_per_lot=1.0,   # confirm against your broker's contract spec
        price_to_pip_factor=1.0,
    )
    print(f"Lot size:        {plan.lot_size}")
    print(f"Risk amount:     ${plan.risk_amount}")
    print(f"R:R ratio:       1:{plan.risk_reward_ratio}")
    if plan.risk_reward_ratio < 2.0:
        print("WARNING: this trade does not meet the 1:2 minimum R:R rule.")
