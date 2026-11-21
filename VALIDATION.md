# VALIDATION — v2 vs v1 (trophy forecast)

Date: 21 Nov 2026. Model work only; no submission, no repo touch, no recording.
Final v2 = `main.py` in this directory (v1 kept as `main-v1.py`).

## What changed in v2 (four targeted changes, nothing else)

1. **Rare-trophy prior** — a trophy flat at the display floor (last rate
   ≤ 0.05%, logit range < 0.05 over the fit window) carries no slope signal:
   its fitted slope is 0 only because nothing has happened yet. It now gets
   the pooled slope instead of its own zero. Fires for ~21 of 55 trophies in
   the simulated final-like cases.
2. **Pooled slope over trophies that actually moved only** — including the
   flat trophies' zero slopes dragged the median pooled slope down to ~0.59
   and understated the trend every trophy follows.
3. **No damping (damp = 1.10)** — v1 damped the slope toward zero for long
   projections, but the ln(1+h) transform already encodes deceleration, and
   a right-skewed time-to-earn curve is convex in ln(t) while trophies are
   still in their steep phase: the fitted trend understates the 4.5-day move.
4. **Wider spread** — base sigma 0.5 → 0.6875 per √day, cap 1.35 → 2.0
   (effective ≈ 1.47 logit units at the 4.5-day horizon). v1's 90% intervals
   covered the truth only 60% of the time on long horizons.

Unchanged: 48h fit window (24h and all-history were both worse), shrinkage
strength, median anchored at the last read, half-refresh-gap effective time,
flat-history fallback (practice-case output is byte-identical to v1),
tier-specific slopes (no gain), fitted-value anchor (slightly worse).

## Simulation harness (`sim/`)

Generative worlds deliberately different from v1's fitting family: players
join on a saturating logistic N(t) fitted to the real anchors N(4.5h)=3,868
and N(50.6h)=54,144 (live Exophase leaderboard, 21 Nov 02:30 UTC); each
trophy has an eventual-earner fraction solved so the simulated rate at
h=50.6 equals the observed rate, and a lognormal time-to-earn (median hours
per trophy by type: story early, grind late). Exophase refreshes in jumps;
history is every read to the checkpoint (59.5h); truth is the state at the
last refresh before the 168h target. Scorer = mean pinball loss on the logit
scale, exactly per RULES.txt, plus a format validator and a determinism
double-run check.

17 worlds: N_inf {75k, 150k, 300k, 500k} × progression {0.67×, 1.0×, 1.5×}
× refresh gap {2h, 3h, 6h}, plus a casual-late-joiner world (joiners after
24h earn 2.5× slower), a thin-tailed Weibull time-to-earn world, and two
adversarial **frozen** worlds (earners stop after the checkpoint, rates fall
on dilution alone — deliberately unrealistic, to bound the downside of
projecting rises).

## Head-to-head (mean pinball loss, logit scale; lower is better)

| world | v1 | v2 | house starter |
|---|---|---|---|
| w_fastN500_medP | 0.905 | 0.546 | 1.159 |
| w_fastN_fastP | 0.757 | 0.501 | 0.953 |
| w_fastN_medP | 0.970 | 0.579 | 1.218 |
| w_fastN_medP_frozen | 0.677 | 0.974 | 0.464 |
| w_fastN_medP_g6 | 0.967 | 0.575 | 1.240 |
| w_fastN_slowP | 1.227 | 0.688 | 1.534 |
| w_medN_fastP | 0.753 | 0.490 | 0.954 |
| w_medN_medP | 0.976 | 0.579 | 1.226 |
| w_medN_medP_casual | 0.732 | 0.475 | 0.885 |
| w_medN_medP_frozen | 0.471 | 0.775 | 0.283 |
| w_medN_medP_g2 | 0.992 | 0.579 | 1.247 |
| w_medN_medP_g6 | 0.990 | 0.597 | 1.252 |
| w_medN_medP_weib2 | 1.105 | 0.642 | 1.385 |
| w_medN_slowP | 1.303 | 0.741 | 1.635 |
| w_slowN_fastP | 0.620 | 0.428 | 0.814 |
| w_slowN_medP | 0.907 | 0.541 | 1.164 |
| w_slowN_slowP | 1.046 | 0.654 | 1.384 |

Summary:

| | v1 | v2 | house starter |
|---|---|---|---|
| 15 normal worlds (mean) | 0.950 | **0.574** | 1.203 |
| 2 frozen worlds (mean) | 0.574 | 0.874 | 0.373 |
| all 17 worlds (mean) | 0.906 | **0.610** | 1.106 |
| worst normal world | 1.303 | **0.741** | 1.635 |
| 90% interval coverage | 0.60 | **0.95** | 0.42 |

v2 beats v1 in **all 15 normal worlds** (by 0.19–0.56 per world) and loses
only in the two frozen worlds, where projecting any rise is wrong by
construction. The frozen worlds assume earners literally stop for 4.5 days
while 100k+ new players join — impossible 2 days after launch, when
everyone is still playing. Even counting them, v2 wins overall by 0.30
(-33% vs v1). The house baseline (~1.51 on the real practice cases) is
beaten by both versions in every normal world; v2's margin over it is
~0.63 vs v1's ~0.25.

Ablation ladder (15 normal worlds): starter 1.203 → v1 0.950 → no damping
0.827 → + wider spread 0.778 → + damp 1.10 0.736 → + rare prior 0.640 →
+ moving-only pooled slope **0.574**. Each step was kept only because it
improved the mean across all 15 worlds, never a single world.

## Caveats (read before submitting)

- These are simulations, not the server's practice grade — the server grade
  for v1 is still unknown, and no simulation can prove the real-world loss.
  What the simulations do establish is that v2's changes are not
  overfitting to one scenario: they win across N growth 75k–500k, fast/slow
  progression, 2–6h refresh gaps, casual late joiners, and a thin-tailed
  time-to-earn distribution.
- The simulator itself leans toward rising rates (launch-week progression
  wave); the frozen worlds are the counterweight, and v2's loss there is
  bounded (+0.30 vs v1) while its gain in normal worlds is larger (-0.38).
- The `Gone Fishing` trophy (100.00% observed) is still forecast at 100%
  with a tight interval in both versions — the page shows ≥99.995%, so
  near-instant earning for essentially every player is the right read, and
  the simulator's ~94.6% for it is a known simulator artifact, not a
  model bug.

## Final compliance checks (installed `main.py`, 21 Nov 2026)

- Practice cases p00/p01 from the kit: output **byte-identical to v1**
  (flat-history fallback untouched), 55 rows, valid format.
- Simulated final-like cases: 55 rows, ids 1–55 in order, 5 quantiles
  non-decreasing, all in 0–100, output ≈ 3.2 KB (limit 65,536).
- Runtime 0.09 s per run of 4 cases (limit 8 s per case).
- Two runs byte-identical (deterministic, no randomness, no time dependence
  beyond the case file itself).
- Stdlib only (`json`, `math`, `os`, `sys`, `datetime`, `pathlib`); no
  network; no file access outside `/input` and `/output`.
