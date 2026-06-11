#!/usr/bin/env python3
"""
Reference strategy archetypes for the AlfaFond demo.

Each strategy turns a list of closing prices into a list of target positions
(0 = flat, 1 = long), using only data up to each bar. These are clean, honest
illustrations of three classic archetypes — NOT the proprietary strategies, and
NOT tuned to look profitable. The point is to show the engine's range and let
the validation stage expose how each one really behaves out-of-sample.

Add your own by appending a Strategy to REGISTRY — that is exactly what a
build-to-spec engagement does.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from lab_engine import rolling_std, sma

# A signal function: closes -> target position per bar (0/1).
SignalFn = Callable[[list[float]], list[int]]


@dataclass
class Strategy:
    key: str
    name: str
    desc: str                       # one line, shown on the site and in --list
    grid: list[tuple]               # parameter combos to search in-sample
    baseline: tuple                 # a sensible, NON-optimised default
    make: Callable[[tuple], SignalFn]


# --- 1 · trend following (SMA crossover) -----------------------------------

def _trend(params: tuple) -> SignalFn:
    fast, slow = params

    def signal(closes: list[float]) -> list[int]:
        f = sma(closes, fast)
        s = sma(closes, slow)
        # long whenever the fast average is above the slow one
        return [1 if (f[i] > s[i]) else 0 for i in range(len(closes))]

    return signal


# --- 2 · mean reversion (z-score of price vs its own mean) ------------------

def _meanrev(params: tuple) -> SignalFn:
    window, entry_z, exit_z = params

    def signal(closes: list[float]) -> list[int]:
        mean = sma(closes, window)
        std = rolling_std(closes, window)
        out: list[int] = []
        pos = 0
        for i, p in enumerate(closes):
            if math.isnan(mean[i]) or std[i] == 0 or math.isnan(std[i]):
                out.append(0)
                continue
            z = (p - mean[i]) / std[i]
            if pos == 0 and z <= -entry_z:        # cheap vs its mean → buy the dip
                pos = 1
            elif pos == 1 and z >= -exit_z:       # reverted toward mean → exit
                pos = 0
            out.append(pos)
        return out

    return signal


# --- 3 · breakout (Donchian channel on closes) -----------------------------

def _breakout(params: tuple) -> SignalFn:
    enter_n, exit_n = params

    def signal(closes: list[float]) -> list[int]:
        out: list[int] = []
        pos = 0
        warmup = max(enter_n, exit_n)
        for i in range(len(closes)):
            if i < warmup:
                out.append(0)
                continue
            upper = max(closes[i - enter_n:i])    # highest of the prior enter_n closes
            lower = min(closes[i - exit_n:i])     # lowest of the prior exit_n closes
            if pos == 0 and closes[i] > upper:    # new high → ride the breakout
                pos = 1
            elif pos == 1 and closes[i] < lower:  # broke support → step aside
                pos = 0
            out.append(pos)
        return out

    return signal


REGISTRY: dict[str, Strategy] = {
    "trend": Strategy(
        key="trend",
        name="Trend following · SMA crossover",
        desc="Long while a fast moving average sits above a slow one; flat otherwise.",
        grid=[(f, s) for f in (5, 8, 10, 12, 15, 20)
              for s in (30, 40, 50, 60, 80, 100) if f < s],
        baseline=(10, 50),
        make=_trend,
    ),
    "meanrev": Strategy(
        key="meanrev",
        name="Mean reversion · price z-score",
        desc="Buy when price is stretched below its own mean; exit as it reverts.",
        grid=[(w, e, x) for w in (10, 20, 30)
              for e in (1.0, 1.5, 2.0) for x in (0.0, 0.5)],
        baseline=(20, 1.5, 0.5),
        make=_meanrev,
    ),
    "breakout": Strategy(
        key="breakout",
        name="Breakout · Donchian channel",
        desc="Enter on a new N-day high; exit on an M-day low.",
        grid=[(en, ex) for en in (10, 20, 30, 55) for ex in (10, 20)],
        baseline=(20, 10),
        make=_breakout,
    ),
}
