# AlfaFond — strategy lab (public demo)

A tiny, dependency-free trading lab you can **read in one sitting and run in one command**.
Three reference strategy archetypes, one honest backtest engine, and a validation stage
that shows you when an "edge" is really just overfit. It exists so you can judge the
engineering — and the honesty — *before* you hire or pay for anything.

> I sell technology, not returns. You configure, test and run your own strategies and you
> own the risk. These are teaching artifacts, **not** profitable bots and **not** the
> proprietary strategies. — [alfafond.com/dev](https://alfafond.com/dev)

## Run it

No install, no API key, no network — the data is a bundled CSV of **real public Binance
daily candles**. You need only Python 3.10+.

```bash
python3 strategy_lab.py                     # compare all strategies (in-sample → OOS)
python3 strategy_lab.py list                # list the strategies
python3 strategy_lab.py trend               # all 3 stages for one strategy
python3 strategy_lab.py meanrev validate    # one stage for one strategy
python3 strategy_lab.py breakout paper      # paper-stream one strategy, fill by fill
```

## The strategies

| key        | archetype                       | rule (plain English)                                   |
|------------|----------------------------------|--------------------------------------------------------|
| `trend`    | Trend following · SMA crossover  | Long while a fast moving average sits above a slow one. |
| `meanrev`  | Mean reversion · price z-score   | Buy when price is stretched below its mean; exit on reversion. |
| `breakout` | Breakout · Donchian channel      | Enter on a new N-day high; exit on an M-day low.        |

Each is a clean, honest illustration — not tuned to look good. Add your own by appending
a `Strategy` to `REGISTRY` in `lab_strategies.py`; that is exactly what a build-to-spec
engagement does.

## The three stages

They mirror how a real engagement validates a strategy:

1. **backtest** — run a strategy on the full history, fees included. One number on one
   window. It looks like a result; it isn't one yet.

2. **validate** — split the data in half, find the *best* parameters on the first half,
   then apply those same parameters to the unseen second half. The default command runs
   this across all three and prints the gap:

   ```
   strategy                            best IS     → OOS   baseline OOS   verdict
   Trend following · SMA crossover      +69.9%     -9.7%         -13.9%   holds (this split)
   Mean reversion · price z-score       +56.5%    -11.2%         -19.4%   holds (this split)
   Breakout · Donchian channel          +80.7%     +3.9%         +16.1%   OVERFIT
   ```

   The tuned "best" decays hard out-of-sample — in `breakout`'s case the optimised version
   is *worse* than leaving the parameters alone. That gap is the whole point: it tells you
   the honest number **before** a cent is at risk.

3. **paper** — stream the unseen candles one by one, printing every BUY/SELL and the
   running paper-equity. Real prices, real sequence, **zero real money**. This is the gate
   that stands between a backtest and your capital.

## What this is *not*

- Not financial advice, not a signal service, not managed money.
- Not the production system — that repository is private. This is a clean, standalone
  illustration of *method and code quality*, built only on open data and the standard library.
- Not tuned to look profitable. Most of these lose money out-of-sample, on purpose, to make
  the point that most "edges" are overfit and a serious process tells you so up front.

The real engagement runs the full **6-gate** version of stage 2 (tiered costs, Deflated
Sharpe, walk-forward, out-of-sample hold-out, plateau and split-half robustness) plus
Monte-Carlo risk-of-ruin and Kelly sizing — on a venue connector with a pre-trade risk gate
and an HTTP killswitch.

## Files

```
strategy_lab.py     CLI + the three stages (backtest / validate / paper)
lab_engine.py       data loader, indicators, the fee-aware backtest engine
lab_strategies.py   the strategy archetypes and their parameter grids
data/btcusdt_1d.csv real public daily OHLCV (Binance /api/v3/klines, no key)
```

The code is deterministic: the same CSV always yields the same output. Refresh the CSV
yourself anytime from the public Binance endpoint.

## License

MIT — see [`LICENSE`](LICENSE). Use it, fork it, learn from it.

---

Want this adapted to your venue and your strategy, validated honestly end to end?
→ [alfafond.com/dev](https://alfafond.com/dev)
