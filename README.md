# Warren Trading

Research and execution tooling for a discretionary XAU/USD & EUR/USD
strategy (market structure, POI on H4/Daily, liquidity sweeps, pinbar
/ engulfing entries, 1–2% risk per trade, minimum 1:2 Risk:Reward),
built around MetaTrader 5.

⚠️ **Educational / research project. Not financial advice.** Nothing
here is validated as profitable — test extensively on a demo account
before risking real capital, and confirm every broker-specific number
(pip value, contract size, lot step) against your own account
specification in MT5.

## What's in here

| File | Purpose |
|---|---|
| `position_sizing.py` | Risk-based lot size calculator (1–2% rule) and trade-plan validator (1:2 minimum R:R). |
| `structure_analysis.py` | Swing high/low detection, support/resistance (POI) zone clustering, liquidity sweep detection, pinbar & engulfing pattern recognition. |
| `backtest.py` | Replays generated signals against historical candles to report win rate, average R multiple, and max drawdown. |
| `generate_sample_data.py` | Produces synthetic OHLC data so the pipeline can run end-to-end before you plug in real MT5 exports. |
| `WarrenGold_EA.mq5` | MQL5 Expert Advisor skeleton: AUTO / SEMI_AUTO / SIGNAL_ONLY modes, hard-clamped 1–2% risk sizing, 1:2 R:R filter, break-even management. The market-structure detection itself is a `TODO` — it's prototyped in Python first, then meant to be ported or bridged in. |

## Quick start (Python side)

```bash
pip install pandas
python3 generate_sample_data.py          # creates sample_data/XAUUSD_H4_sample.csv
python3 structure_analysis.py            # prints detected signals
python3 backtest.py                      # runs the backtest report
```

Replace `sample_data/XAUUSD_H4_sample.csv` with a real MT5 export
(right-click a chart → "Export candles to CSV") before drawing any
real conclusions — the bundled sample data is randomly generated and
its backtest numbers mean nothing about real market performance.

## Using the EA (MT5 side)

1. Copy `WarrenGold_EA.mq5` into your MT5 `MQL5/Experts/` folder.
2. Compile it in MetaEditor.
3. Attach it to an XAU/USD chart **on a demo account**.
4. Leave `InpMode` on `SIGNAL_ONLY` until the structure-detection logic
   (currently a `TODO`) is ported over and you've validated it against
   the Python backtest results.

## Roadmap

- [ ] Port `structure_analysis.py`'s detection logic into `DetectSetup()`
      in the EA, or connect it via a JSON file bridge (same pattern as
      the existing `AvaBridgeEA`).
- [ ] Add spread/commission modeling to the backtester.
- [ ] Walk-forward validation on real XAU/USD and EUR/USD H4/Daily history.
