"""Forecast GTA VI PS5 trophy earn rates on Exophase at a case's target.

Model (per case, from that case's read history only):
  * Earn rate = earners / players tracked. Both move: the tracked player
    base grows as more players sync, and earners accumulate as players
    play, so a rate can fall on dilution or rise on progression. The net
    movement is read off the history itself: at every distinct Exophase
    refresh, each trophy's logit rate is fitted against ln(1 + hours since
    release), per trophy, shrunk toward the pooled slope over all trophies
    (two-decimal rates on a handful of refreshes are noisy, and the
    shrinkage keeps one trophy's slope honest). The median forecast anchors
    that trend at the last read and reads it at an effective time half a
    refresh gap before the target, because the answer is the last Exophase
    refresh before the target, not the state at the target.
  * The spread on the logit scale combines a random-walk term, the slope's
    own standard error carried over the projection, and refresh-timing
    uncertainty, so the five quantiles widen honestly with the horizon.
  * When the history is flat (no refresh at all: every read identical),
    no trend can be fitted. Exophase refreshes in jumps, and the first
    refresh of launch night multiplied the tracked base about sixfold while
    earners grew only modestly, so every rate fell severalfold. The fallback
    therefore assumes one refresh before the target, with the base up about
    fivefold and earners up about 1.3x, and a wide spread.

v2 changes (21 Nov 2026, validated on 17 simulated final-like cases; see
VALIDATION.md):
  * Rare-trophy prior: a trophy flat at the display floor (last rate
    <= 0.05%, logit range ~0 over the fit window) carries no slope signal —
    its fitted slope is 0 only because nothing has happened yet. It now
    gets the pooled slope instead of its own zero. In the simulations this
    fires for ~21 of 55 trophies and is the single biggest win.
  * Pooled slope over trophies that actually moved only: including the flat
    trophies' zero slopes dragged the median pooled slope down (~0.59) and
    understated the trend every trophy follows.
  * No damping (damp 1.10): v1 damped the slope toward zero for long
    projections, but the ln(1+h) transform already encodes the
    deceleration, and a lognormal-ish time-to-earn curve is convex in
    ln(t) while trophies are still in their steep phase — the fitted trend
    understates the 4.5-day move, it does not overstate it.
  * Wider spread: base sigma 0.5 -> 0.6875 per sqrt(day), cap 1.35 -> 2.0
    (effective ~1.47 logit units at the 4.5-day horizon). v1's 90%
    intervals covered the truth only 60% of the time on long horizons.

Standard library only, no network, deterministic: the same input bytes
always produce the same output bytes.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a module
# shipped beside this file imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
RELEASE = datetime(2026, 11, 19, 0, 0, 0, tzinfo=timezone.utc)

# --- numeric helpers -------------------------------------------------------


def clamp_pct(x):
    return min(99.99, max(0.01, x))


def logit(pct):
    p = clamp_pct(pct) / 100.0
    return math.log(p / (1.0 - p))


def inv_logit(lg):
    if lg >= 0:
        return 100.0 / (1.0 + math.exp(-lg))
    e = math.exp(lg)
    return 100.0 * e / (1.0 + e)


def round4(x):
    """Round to 4 decimals, half up (the convention the scorer's examples use)."""
    scaled = x * 10000.0
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 10000.0
    return int(value) if float(value).is_integer() else value


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def hours_since_release(moment):
    return (moment - RELEASE).total_seconds() / 3600.0


def linfit(xs, ys):
    """Least-squares y = a + b*x; returns (a, b) or None."""
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx < 1e-12:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    return (my - b * mx, b)


# --- history ----------------------------------------------------------------


def build_reads(case):
    """One dict per history read: hours since release, players, rates, earners."""
    reads = []
    n_trophies = len(case["trophies"])
    for entry in case["history"]:
        rates = [
            None if r is None else min(100.0, max(0.0, r)) for r in entry["rates"]
        ]  # the page prints 0..100
        players = float(entry["players_tracked"])
        earners = []
        for i in range(n_trophies):
            r = rates[i] if i < len(rates) else None
            earners.append(None if r is None else r * players / 100.0)
        reads.append(
            {
                "h": hours_since_release(parse_time(entry["at"])),
                "n": players,
                "rates": rates,
                "earners": earners,
            }
        )
    reads.sort(key=lambda r: r["h"])
    return reads


def distinct_states(reads):
    """Consecutive reads with identical players and rates are one Exophase state."""
    states = []
    for read in reads:
        key = (read["n"], tuple(read["rates"]))
        if states and states[-1][0] == key:
            continue
        states.append((key, read))
    return [read for _, read in states]


# --- trend projection ---------------------------------------------------------

def trend_slopes(states, n_trophies):
    """Per-trophy slope of logit(rate) against ln(1 + hours), fitted on the
    recent states (last 48 hours when there are enough of them), shrunk
    toward the pooled slope over all trophies.

    Returns (slope_list, se_list, dx_fit): the shrunk slope and its standard
    error per trophy, in logit units per unit of ln(1+h), and the span of
    ln(1+h) the fit covers.
    """
    h_last = states[-1]["h"]
    window = [s for s in states if s["h"] >= h_last - 48.0]
    if len(window) < 4:
        window = states
    xs = [math.log(1.0 + s["h"]) for s in window]
    dx_fit = (max(xs) - min(xs)) if len(xs) > 1 else 0.0

    own = []
    for i in range(n_trophies):
        pts = []
        for x, s in zip(xs, window):
            r = s["rates"][i] if i < len(s["rates"]) else None
            if r is not None:
                pts.append((x, logit(r)))
        if len(pts) < 3 or max(p[0] for p in pts) - min(p[0] for p in pts) < 1e-9:
            own.append(None)
            continue
        fit = linfit([p[0] for p in pts], [p[1] for p in pts])
        if fit is None:
            own.append(None)
            continue
        a, b = fit
        resid = [y - (a + b * x) for x, y in pts]
        dof = max(1, len(pts) - 2)
        s2 = sum(e * e for e in resid) / dof
        mx = sum(p[0] for p in pts) / len(pts)
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        se = math.sqrt(s2 / sxx) if sxx > 1e-12 else 1.0
        yrange = max(p[1] for p in pts) - min(p[1] for p in pts)
        own.append((b, se, len(pts), yrange))
    # Pooled slope over trophies that actually moved: a trophy flat at the
    # display floor has a fitted slope of 0 only because nothing has
    # happened yet, so including those zeros would drag the pooled slope
    # down and understate the trend the flat trophies will follow.
    moving = [o[0] for o in own if o is not None and o[3] >= 0.05]
    moving.sort()
    if moving:
        g_slope = moving[len(moving) // 2]
    else:
        slopes = [o[0] for o in own if o is not None]
        slopes.sort()
        g_slope = slopes[len(slopes) // 2] if slopes else 0.0
    ses = [o[1] for o in own if o is not None]
    g_se = (sum(ses) / len(ses)) if ses else 1.0

    slope_list, se_list = [], []
    last_rates = states[-1]["rates"]
    for idx, o in enumerate(own):
        if o is None:
            slope_list.append(g_slope)
            se_list.append(g_se)
            continue
        b, se, n, yrange = o
        # A trophy flat at the display floor (last rate <= 0.05%, logit range
        # ~0 over the window) carries no slope signal at all: its fitted
        # slope is 0 only because nothing has happened yet, not because it
        # will not move. Give it the pooled slope instead of its own zero.
        last_r = last_rates[idx] if idx < len(last_rates) else None
        if last_r is not None and last_r <= 0.05 and yrange < 0.05:
            slope_list.append(g_slope)
            se_list.append(g_se)
            continue
        w = n / (n + 4.0)  # shrink toward the pooled slope
        b = w * b + (1.0 - w) * g_slope
        b = min(max(b, -2.0), 2.0)
        se = math.sqrt((w * se) ** 2 + ((1.0 - w) * g_se) ** 2)
        slope_list.append(b)
        se_list.append(se)
    return slope_list, se_list, dx_fit


# --- per-case forecast ---------------------------------------------------------


def forecast_flat(last_rates, last_n):
    """Fallback when the history never moved: assume one refresh before the
    target, base up ~5x, earners up ~1.3x, with a wide spread."""
    rows = []
    for i, trophy_rate in enumerate(last_rates):
        if trophy_rate is None:
            trophy_rate = 0.0
        if trophy_rate >= 99.99:
            median = 100.0
        else:
            growth = 1.2 + 0.2 * min(1.0, trophy_rate / 2.0)
            median = clamp_pct(trophy_rate * growth / 5.0)
        rows.append((median, 0.9))
    return rows


def forecast_case(case):
    trophies = case["trophies"]
    n_trophies = len(trophies)
    horizon_days = case["horizon_minutes"] / 1440.0
    target_h = hours_since_release(parse_time(case["target"]))
    reads = build_reads(case)
    if not reads:
        return {"trophies": [{"id": t["id"], "q": [0.5, 0.75, 1.0, 1.35, 1.8]} for t in trophies]}
    states = distinct_states(reads)
    last = states[-1]
    last_rates = last["rates"]

    # Flat history: no refresh to learn from.
    growth = (states[-1]["n"] - states[0]["n"]) / max(1.0, states[0]["n"])
    if len(states) < 2 or growth < 0.05:
        med_sig = forecast_flat(last_rates, last["n"])
        return {"trophies": [row_for(t["id"], med, sig) for t, (med, sig) in zip(trophies, med_sig)]}

    # Median gap between refreshes: the answer is the last refresh before
    # the target, so project to half a gap before the target.
    gaps = [b["h"] - a["h"] for a, b in zip(states, states[1:]) if b["h"] > a["h"]]
    gaps.sort()
    gap_h = gaps[len(gaps) // 2] if gaps else 6.0
    gap_h = min(max(gap_h, 0.0), 12.0)
    eff_h = target_h - 0.5 * gap_h
    eff_h = max(eff_h, last["h"])
    dx = math.log(1.0 + eff_h) - math.log(1.0 + last["h"])

    slope_list, se_list, dx_fit = trend_slopes(states, n_trophies)
    # Damp the trend for long projections: a rate's logit curve flattens as
    # it approaches its ceiling, so a straight line fitted over the window
    # overstates a move far beyond it. The damping pulls the slope toward
    # zero as the projection grows past the fit's own span.
    damp = 1.10

    base_sigma = 0.6875 * math.sqrt(horizon_days)
    rows = []
    for i, trophy in enumerate(trophies):
        rate = last_rates[i] if i < len(last_rates) else None
        if rate is None:
            rate = 0.0
        if rate >= 99.99:
            rows.append(row_for(trophy["id"], 100.0, 0.2))
            continue
        # Anchor the trend at the last read: the freshest information is
        # where the rate stands now, the damped slope says where it is heading.
        median = clamp_pct(inv_logit(logit(rate) + damp * slope_list[i] * dx))
        # Spread: random walk + slope uncertainty over the projection +
        # refresh timing.
        sigma = math.sqrt(
            base_sigma ** 2 + (se_list[i] * dx) ** 2 + 0.25 ** 2
        )
        sigma = min(max(sigma, 0.45), 2.0)
        rows.append(row_for(trophy["id"], median, sigma))
    return {"trophies": rows}


def row_for(trophy_id, median, sigma):
    lg = logit(median)
    qs = []
    for z in Z:
        q = inv_logit(lg + z * sigma)
        qs.append(round4(min(100.0, max(0.0, q))))
    # Quantiles must not decrease (rounding can only tie, never invert, but
    # enforce it outright).
    for k in range(1, len(qs)):
        if qs[k] < qs[k - 1]:
            qs[k] = qs[k - 1]
    return {"id": trophy_id, "q": qs}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case)
        out = OUTPUT_DIR / f"{path.stem}.out"
        out.write_text(json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
