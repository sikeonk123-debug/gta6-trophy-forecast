# gta6-trophy-forecast

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/sikeonk123-debug/gta6-trophy-forecast/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/sikeonk123-debug/gta6-trophy-forecast/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Forecasts, for every PlayStation 5 trophy of Grand Theft Auto VI, the percent of players Exophase tracks who will have earned it at 2026-11-26T00:00:00Z, as five quantiles (0.05, 0.25, 0.5, 0.75, 0.95) per trophy. `main.py` (Python 3.13, standard library only, no network) reads each case at `/input` and writes its forecast to `/output`.

## How it forecasts

An earn rate is earners over players tracked, and both move: the tracked base grows as more players sync, and earners accumulate as players play, so a rate can fall on dilution or rise on progression. The program reads that net movement off the case's own history: at every distinct Exophase refresh, each trophy's logit rate is fitted against ln(1 + hours since release), per trophy, shrunk toward the pooled slope over all trophies. The median anchors that trend at the last read and reads it at an effective time half a refresh gap before the target, because the answer is the last Exophase refresh before the target, not the state at the target. The spread combines a random-walk term, the slope's own standard error carried over the projection, and refresh-timing uncertainty.

When the history is flat — no refresh at all, every read identical — no trend can be fitted. Exophase refreshes in jumps, and the first refresh of launch night multiplied the tracked base about sixfold while earners grew only modestly, so every rate fell severalfold. The fallback therefore assumes one refresh before the target, with the base up about fivefold and earners up about 1.3x, and a wide spread.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=rnmxxsbb&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
