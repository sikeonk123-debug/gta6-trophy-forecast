# gta6-trophy-forecast

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/sikeonk123-debug/gta6-trophy-forecast/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/sikeonk123-debug/gta6-trophy-forecast/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Forecasts, for every PlayStation 5 trophy of Grand Theft Auto VI, the percent of players Exophase tracks who will have earned it at 2026-11-26T00:00:00Z, as five quantiles (0.05, 0.25, 0.5, 0.75, 0.95) per trophy. `main.py` (Python 3.13, standard library only, no network) reads each case at `/input` and writes its forecast to `/output`.

## How it forecasts

An earn rate is earners over players tracked, and both move: the tracked base grows as more players sync, and earners accumulate as players play, so a rate can fall on dilution or rise on progression. The program reads that net movement off the case's own history: at every distinct Exophase refresh, each trophy's logit rate is fitted against ln(1 + hours since release), per trophy, shrunk toward the pooled slope over all trophies. The median anchors that trend at the last read and reads it at an effective time half a refresh gap before the target, because the answer is the last Exophase refresh before the target, not the state at the target. The spread combines a random-walk term, the slope's own standard error carried over the projection, and refresh-timing uncertainty.

When the history is flat — no refresh at all, every read identical — no trend can be fitted. Exophase refreshes in jumps, and the first refresh of launch night multiplied the tracked base about sixfold while earners grew only modestly, so every rate fell severalfold. The fallback therefore assumes one refresh before the target, with the base up about fivefold and earners up about 1.3x, and a wide spread.

## v2 (21 Nov 2026)

Four targeted changes over v1, each kept only because it improved the mean pinball loss across 17 simulated final-like cases (see `VALIDATION.md`):

- **Rare-trophy prior.** A trophy flat at the display floor (last rate ≤ 0.05%, logit range ~0 over the fit window) carries no slope signal — its fitted slope is 0 only because nothing has happened yet. It now gets the pooled slope instead of its own zero. Fires for ~21 of 55 trophies; the single biggest win.
- **Pooled slope over trophies that actually moved only.** Including the flat trophies' zero slopes dragged the median pooled slope down to ~0.59 and understated the trend every trophy follows.
- **No damping (damp = 1.10).** v1 damped the slope toward zero for long projections, but the ln(1+h) transform already encodes the deceleration, and a right-skewed time-to-earn curve is convex in ln(t) while trophies are still in their steep phase.
- **Wider spread.** Base sigma 0.5 → 0.6875 per √day, cap 1.35 → 2.0 (≈ 1.47 logit units at the 4.5-day horizon). v1's 90% intervals covered the truth only 60% of the time on long horizons.

Head-to-head on the 17 simulated worlds (mean pinball loss, logit scale): v2 **0.610** vs v1 0.906 vs house starter 1.106 — v2 wins in all 15 normal worlds (0.574 vs 0.950) and loses only in two deliberately unrealistic frozen-earner stress worlds. v1 is kept as `main-v1.py` in this directory.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=rnmxxsbb&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
