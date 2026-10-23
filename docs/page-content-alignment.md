# Backup website content alignment

Updated on 23 October 2026 from
[`hulaearth/ai-for-nature-full`](https://github.com/hulaearth/ai-for-nature-full),
revision `91fa9e6d89ebf704eb08df39149e0f5c95d73e97`.
The primary website remains <https://ai-for-nature.hula.earth/>. This repository
and its private HF Space are a backup, activated only on organizer instruction.

## What was brought over

- The “Where could birds thrive?” introduction and explanation of why habitat matters.
- One main task, with exploration and cross-species work in an optional expansion.
- A plain-language data overview: start with tables, add spatial files if useful,
  and keep decoding, storage and licensing details in expandable sections.
- Rules organized around permitted work, deliverables, scoring and detailed checklists.
- A six-step guide from registration through final prediction and presentation.
- The official Hula Earth wordmark and the same forest, lime and cream visual scheme.

Optional climate/water features, 2010–2023 bird history, German mapping inputs,
Drive transport-part instructions, mirrors and source credits already maintained
in this backup remain available. They were not removed because the primary site
uses a shorter data page.

Participant prose now lives in `scripts/content/*.html`. The source repo is
not needed to build this backup. `scripts/build_site.py` inserts the existing
forms, schedule, preview and shared page shell; `site/*.html` are generated output.
Styles remain embedded into every routed page, with exact CSP hashes, so private
Space navigation does not depend on fetching a separate stylesheet.

## Deliberate differences: retain the working backup contract

This is a content/structure update, not a port of the primary application.
Several primary pages disagree with each other or with this evaluator. Copying
their operational instructions would tell participants to submit incompatible
files or use controls this backup does not have.

| Area | Retained backup behavior |
| --- | --- |
| Navigation | Seven existing hash-routed views; same IDs, data hooks and deep links |
| Accounts | Hugging Face sign-in and confirmed team membership |
| Final choice | Captain-only “Make this my final entry if accepted” / “Use for final”; latest accepted captain upload is the fallback |
| Test contract | 159,150 rows at 15,915 locations; 24 MB CSV; unchanged manifest and public encryption key |
| Quotas and receipts | Existing five accepted finals, ten practice checks, provider receipt commitments and rejection behavior |
| Reference | 64-value, 1 km-radius AlphaEarth logistic starter; German development AP 0.34087975805917803 |
| Timing | Materials 10:00; modeling 11:00; test unlock 13:30; deadline 17:30 CEST |
| Presentations | 17:45–19:45; five minutes plus two minutes of questions |
| Team guidance | Two or three people; no account/role validation changes |
| Handoff | Existing method/report and code/checkpoint reference plus separate Google presentation Form |
| Additional environmental inputs | Existing permission for analysis/training, with final features computable from supplied anonymous inputs |
| Runtime | Both standby gates remain false; event workflows remain disabled |

The primary content contains a 63,590-row / 8 MB test, GitHub sign-in, automatic
star selection and a 289-feature reference. Its homepage also lists an 18:00
deadline and 4+2 minute pitches, whereas its rules say 17:30. None of these were
silently substituted into the backup. A future incident operator must reconcile
the actual event contract with both evaluators before directing real submissions
between platforms. **Primary submissions, receipts and teams are not imported.**

## Verification and publication

- Existing JavaScript, form templates and operational contracts were compared
  byte for byte: 18 files unchanged. All 96 existing element IDs and 20 data
  hook names remain in the generated integrated page.
- All 50 Python tests, seven JavaScript test suites and `scripts/check_site.py`
  passed. The latter checks nine HTML entry points, shared CSS/CSP, unique IDs,
  local links, embedded fallbacks, practice schema and the frozen evaluator contract.
- Browser checks navigated all seven views: one visible view at a time, shared
  styling, no horizontal page overflow and no console errors. The new home and
  data layouts were visually reviewed.
- The Space was changed to **Private** in HF Settings. Anonymous API and static
  page requests returned HTTP 401. No credentials were extracted or changed.
- Ten static content/style files were uploaded to the already private Space
  through its authenticated file UI and downloaded again: all SHA-256 hashes
  match. Hosted application/submission JavaScript also matches the unchanged source.
- Hosted `config.json` still referenced the older 289-feature starter. Only its
  stale `starter_commit` and `scoring_policy` fields were merged from the existing
  frozen repository contract. All 49 other hosted fields, including data/final/
  registration/practice flags, were retained. This is a metadata repair to match
  the approved evaluator, not a new reference recipe or runtime activation.
- No Actions workflow was enabled, no data/key material was released, and team,
  receipt and leaderboard JSON were not overwritten. The Space remains private.

For activation and restoration of participant access, use
[`BACKUP_ACTIVATION.md`](../BACKUP_ACTIVATION.md), especially **Space visibility
during a takeover**. This update does not certify a live event rehearsal: runtime
remained stopped as requested.
