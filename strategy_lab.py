#!/usr/bin/env python3
"""
AlfaFond — strategy lab (public demo).

A self-contained, dependency-free trading lab you can read and run in minutes.
Three reference strategy archetypes (trend / mean-reversion / breakout), one
honest backtest engine, and three stages that mirror a real engagement:

  1. backtest  — run a strategy on real BTC/USDT daily candles, fees included
  2. validate  — optimise the strategy on the first half of history, then prove
                 the "best" parameters fall apart out-of-sample (the overfit trap)
  3. paper     — stream the unseen half candle-by-candle, printing every fill

No API key, no network, no custody of anything. The data is a bundled CSV of
real public Binance klines. Everything is reproducible: same input → same output.
These strategies are teaching artifacts, NOT profitable bots and NOT the
proprietary ones — the point is to show method and code quality honestly.

    python3 strategy_lab.py                     # compare all strategies (validate)
    python3 strategy_lab.py list                # list the strategies
    python3 strategy_lab.py trend               # all 3 stages for one strategy
    python3 strategy_lab.py meanrev validate    # one stage for one strategy
    python3 strategy_lab.py breakout paper      # paper-stream one strategy

Engineering by alfafond.com/dev — I sell technology, not returns.
"""

from __future__ import annotations

import os
import sys

from lab_engine import (DATA_FILE, FEE_BPS, START_EQUITY, Candle, backtest,
                        buy_and_hold_pct, load_candles)
from lab_strategies import REGISTRY, Strategy


def _split(candles: list[Candle]) -> tuple[list[Candle], list[Candle]]:
    mid = len(candles) // 2
    return candles[:mid], candles[mid:]


def _best_in_sample(strat: Strategy, candles: list[Candle]) -> tuple[tuple, float]:
    """Grid-search the strategy's params on the given window; return (params, ret%)."""
    closes = [c.close for c in candles]
    best_params, best_ret = strat.baseline, float("-inf")
    for params in strat.grid:
        r = backtest(candles, strat.make(params)(closes))
        if r.ret_pct > best_ret:
            best_params, best_ret = params, r.ret_pct
    return best_params, best_ret


# --- stages ----------------------------------------------------------------

def stage_backtest(strat: Strategy, candles: list[Candle]) -> None:
    r = backtest(candles, strat.make(strat.baseline)([c.close for c in candles]))
    print(f"\n=== BACKTEST · {strat.name} {strat.baseline} ===")
    print(f"  window:     {candles[0].date} → {candles[-1].date} ({len(candles)} candles)")
    print(f"  buy & hold: {buy_and_hold_pct(candles):+.1f}%")
    print(f"  strategy:   {r.ret_pct:+.1f}%   ({r.trades} round-trips, fees included)")
    print("  note: one number on one window proves nothing — see `validate`.")


def stage_validate(strat: Strategy, candles: list[Candle]) -> None:
    is_data, oos_data = _split(candles)
    oos_closes = [c.close for c in oos_data]

    best_params, best_ret = _best_in_sample(strat, is_data)
    oos_opt = backtest(oos_data, strat.make(best_params)(oos_closes))
    oos_fixed = backtest(oos_data, strat.make(strat.baseline)(oos_closes))

    print(f"\n=== VALIDATE · {strat.name} · in-sample → out-of-sample ===")
    print(f"  in-sample:      {is_data[0].date} → {is_data[-1].date}")
    print(f"  out-of-sample:  {oos_data[0].date} → {oos_data[-1].date}\n")
    print(f"  best params in-sample:   {str(best_params):<16} → {best_ret:+.1f}%  (looks great)")
    print(f"  SAME params OOS:         {str(best_params):<16} → {oos_opt.ret_pct:+.1f}%")
    print(f"  non-tuned baseline OOS:  {str(strat.baseline):<16} → {oos_fixed.ret_pct:+.1f}%")
    decay = best_ret - oos_opt.ret_pct
    overfit = oos_opt.ret_pct < oos_fixed.ret_pct
    print(f"\n  decay in-sample → out-of-sample: {decay:+.1f} pp")
    print(f"  verdict: {'OVERFIT — tuned winner decays out-of-sample' if overfit else 'holds up on this split (one split is not a proof)'}.")


def stage_paper(strat: Strategy, candles: list[Candle]) -> None:
    warmup, stream = _split(candles)
    f = strat.make(strat.baseline)
    print(f"\n=== PAPER / TESTNET · {strat.name} {strat.baseline} · {len(stream)} candles ===")
    print("  real prices, real sequence, zero real money.\n")

    history = list(warmup)
    equity = START_EQUITY
    qty = 0.0
    for c in stream:
        history.append(c)
        positions = f([x.close for x in history])
        target = positions[-1]
        if qty == 0 and target == 1:
            equity -= equity * FEE_BPS / 10_000
            qty = equity / c.close
            print(f"  {c.date}  BUY  @ {c.close:>10,.0f}   paper-equity ${qty * c.close:>11,.0f}")
        elif qty > 0 and target == 0:
            gross = qty * c.close
            equity = gross - gross * FEE_BPS / 10_000
            qty = 0.0
            print(f"  {c.date}  SELL @ {c.close:>10,.0f}   paper-equity ${equity:>11,.0f}")

    final = equity if qty == 0 else qty * stream[-1].close
    print(f"\n  final paper-equity: ${final:,.0f}  ({(final / START_EQUITY - 1) * 100:+.1f}% from ${START_EQUITY:,})")
    print("  paper held up? then — and only then — you wire your own keys and go live.")


STAGES = {"backtest": stage_backtest, "validate": stage_validate, "paper": stage_paper}


# --- comparison overview (default) -----------------------------------------

def compare_all(candles: list[Candle]) -> None:
    is_data, oos_data = _split(candles)
    oos_closes = [c.close for c in oos_data]
    print(f"\n=== STRATEGY LAB · honest in-sample → out-of-sample comparison ===")
    print(f"  data: {candles[0].date} → {candles[-1].date}  ·  buy & hold OOS: "
          f"{buy_and_hold_pct(oos_data):+.1f}%\n")
    print(f"  {'strategy':<33} {'best IS':>9} {'→ OOS':>9} {'baseline OOS':>14}   verdict")
    print("  " + "-" * 85)
    for strat in REGISTRY.values():
        best_params, best_ret = _best_in_sample(strat, is_data)
        oos_opt = backtest(oos_data, strat.make(best_params)(oos_closes)).ret_pct
        oos_fixed = backtest(oos_data, strat.make(strat.baseline)(oos_closes)).ret_pct
        verdict = "OVERFIT" if oos_opt < oos_fixed else "holds (this split)"
        print(f"  {strat.name:<33} {best_ret:>+8.1f}% {oos_opt:>+8.1f}% "
              f"{oos_fixed:>+13.1f}%   {verdict}")
    print("\n  the tuned 'best' almost always decays out-of-sample. that gap is the")
    print("  whole reason to validate before risking capital. run a single strategy")
    print("  for detail:  python3 strategy_lab.py <key> [backtest|validate|paper]")


def list_strategies() -> None:
    print("\n  available strategies:\n")
    for s in REGISTRY.values():
        print(f"    {s.key:<10} {s.desc}")
    print()


# --- entrypoint ------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not os.path.exists(DATA_FILE):
        print(f"missing data file: {DATA_FILE}", file=sys.stderr)
        return 1
    candles = load_candles()

    args = argv[1:]
    if not args:
        compare_all(candles)
        print()
        return 0
    if args[0] in ("list", "--list", "-l"):
        list_strategies()
        return 0

    key = args[0]
    if key not in REGISTRY:
        print(f"unknown strategy '{key}'. options: {', '.join(REGISTRY)} (or 'list')",
              file=sys.stderr)
        return 2
    strat = REGISTRY[key]

    stage = args[1] if len(args) > 1 else "all"
    if stage == "all":
        for fn in (stage_backtest, stage_validate, stage_paper):
            fn(strat, candles)
        print()
        return 0
    if stage in STAGES:
        STAGES[stage](strat, candles)
        print()
        return 0

    print(f"unknown stage '{stage}'. use: all, {', '.join(STAGES)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
