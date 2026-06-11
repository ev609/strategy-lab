#!/usr/bin/env python3
"""
Backtest engine — strategy-agnostic, dependency-free.

A strategy is just a function that turns a price series into a list of target
positions (0 = flat, 1 = fully long). The engine executes those positions on
real candles with fees, and reports the result. No look-ahead: the target for
bar i is computed from prices up to and including bar i, and executed at that
same close (standard close-to-close daily convention).

Part of the AlfaFond public demo — alfafond.com/dev. Teaching artifact, not a
profitable bot.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass, field

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "btcusdt_1d.csv")
FEE_BPS = 7.5          # taker fee in basis points (0.075%) charged on every fill
START_EQUITY = 10_000  # starting balance, USD


@dataclass
class Candle:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def load_candles(path: str = DATA_FILE) -> list[Candle]:
    """Load real OHLCV candles from the bundled CSV — no network, no keys."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        Candle(r["date"], float(r["open"]), float(r["high"]),
               float(r["low"]), float(r["close"]), float(r["volume"]))
        for r in rows
    ]


def sma(values: list[float], period: int) -> list[float]:
    """Simple moving average; NaN until enough history exists.

    NaN (not None) keeps the type clean and makes warm-up safe for free:
    any comparison against NaN is False, so no signal fires before the window fills.
    """
    out: list[float] = []
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= period:
            acc -= values[i - period]
        out.append(acc / period if i >= period - 1 else math.nan)
    return out


def rolling_std(values: list[float], period: int) -> list[float]:
    """Population standard deviation over a trailing window; NaN during warm-up."""
    out: list[float] = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(math.nan)
            continue
        window = values[i - period + 1:i + 1]
        mean = sum(window) / period
        var = sum((x - mean) ** 2 for x in window) / period
        out.append(math.sqrt(var))
    return out


@dataclass
class BacktestResult:
    ret_pct: float                      # total return on equity, %
    trades: int                         # number of round-trips
    equity_curve: list[float] = field(default_factory=list)


def backtest(candles: list[Candle], positions: list[int],
             start_equity: float = START_EQUITY) -> BacktestResult:
    """
    Execute a 0/1 target-position series on real candles. Long-flat, full-equity
    sizing, no leverage. Fees on every entry and exit. PnL = qty * (exit - entry).
    """
    if len(positions) != len(candles):
        raise ValueError("positions and candles must be the same length")

    equity = start_equity
    qty = 0.0
    trades = 0
    curve: list[float] = []

    for i, c in enumerate(candles):
        curve.append(equity if qty == 0 else qty * c.close)
        target = positions[i]
        if qty == 0 and target == 1:
            fee = equity * FEE_BPS / 10_000
            equity -= fee
            qty = equity / c.close
            trades += 1
        elif qty > 0 and target == 0:
            gross = qty * c.close
            equity = gross - gross * FEE_BPS / 10_000
            qty = 0.0

    if qty > 0:                         # final mark of any open position
        equity = qty * candles[-1].close

    return BacktestResult((equity / start_equity - 1) * 100, trades, curve)


def buy_and_hold_pct(candles: list[Candle]) -> float:
    return (candles[-1].close / candles[0].close - 1) * 100
