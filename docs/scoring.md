# Award scoring

The model score uses a fixed reference baseline. The scoring metric and evidence requirements below apply to every team.

## Model points

Let `s` be the chosen model's final private AP, `a = 1/6` the constant-score AP, and `b` the unchanged shipped reference model's AP on that same private split.

- When `s <= b`: `max(0, 15 * (s - a) / (b - a))`.
- When `s > b`: `min(50, 15 + 35 * (s - b) / 0.15)`.

Matching the reference earns **15/50**. Improvements of +0.02, +0.05, +0.10 and +0.15 AP earn **19.7, 26.7, 38.3 and 50**. Examples are rounded; calculations and ties use full precision. Scores at or below constant-score AP earn zero. No team's result changes the reference or thresholds.

The reference is the supplied default 289-feature linear CPU starter, fitted only on German training rows with seed 20261016 and the pinned Python 3.14.4 environment. Its German development AP is **0.38586286412186144**; that is not `b`. The fixed reference predictions and foreign AP are organizer-private until final results. The live AP leaderboard is feedback, separate from the overall award.

Insights have three 0-10 criteria: useful question; supported analysis and interpretation; effective visualizations. Presentation has three 0-5 criteria: clear explanation; understanding and answers; focused use of the five-minute slot. A technical organizer awards one reproducibility point for each of: code/configuration; reproduction instructions/dependencies; correct common German validation evidence; features/preprocessing/helpers declaration; accurate limitations. Provide evidence in `make_method_report.py`'s report; it is not an automatic self-award.

Overall-prize eligibility requires a valid prediction, supported insights with visualizations, reproducibility references and the presentation. Permitted-data and leakage rules remain validity requirements regardless of checklist points. An exact overall-points tie uses the chosen prediction's earlier original receipt, then stable entry reference, including when model points are capped. The AP board ranks full-precision AP, with the same receipt rule for exact AP ties.

The machine-readable policy and reference fingerprint are in [config/scoring.json](../config/scoring.json). The reference CSV, calibration and hidden labels remain in the private evaluator.

Leaderboard ranking follows the captain’s **currently selected model**, using its public AP during the event and its private AP after final evaluation. Switching the choice updates the public score and rank. A member-only upload needs a captain choice; otherwise the latest captain upload is the fallback. Earlier accepted scores remain in the team entry history.
