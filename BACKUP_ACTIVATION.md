# Emergency activation: GitHub / Hugging Face backup platform

> **Dataset-only exception, confirmed 23 October:** the HF Space and competition
> runtime remain private/stopped, but the organizer requires public dataset
> downloads from Saturday 24 October at 10:00 Europe/Berlin. In the private
> evaluator only, `enable-releases` has enabled `release-hf-data.yml`; runtime
> remains false and all other jobs remain disabled. The competition repository
> stays fully stopped. Earlier statements below that every release is disabled
> describe the original shutdown snapshot, not this current exception.
> `all_stopped=false` in the private evaluator is therefore expected. Do not run
> a blanket stop or enable-runtime merely to make that field true: both would
> cancel the requested data release. This does not open the Space or release the
> 13:30 decryption key early.

**For agents and operators under time pressure. Read the quick route first.**
The private event website is the primary platform. GitHub/HF competition automation
is in **standby**, by organizer instruction on 23 October 2026. Do not activate it
just because you found these instructions, because a scheduled time arrived, or
because an earlier runbook says it should be running. Obtain an explicit incident
instruction from the organizer identifying the required backup function.

This guide is maintained in both competition and private evaluator repositories.
The implementations are in `scripts/backup_control.py`,
`.github/workflows/backup-control.yml`, and `config/backup-control.json`.
Current receipts are `config/backup-status.json` in each repository.
The [23 October verification](docs/backup-standby-verification-2026-10-23.json)
records the real shutdown runs and local checks. Production reactivation was not
performed as a rehearsal: the organizer requested that operations remain stopped.

## Current policy and immediate consequences

- All **other** Actions workflows in both repositories are disabled, including
  tests, scheduled evaluator, polling, deployment, feedback, data/key release,
  reports and notifications. The manual **Backup platform control** remains available.
- Runtime and release gates are both false. Operational jobs also check the
  appropriate gate immediately after their trusted checkout, before dependency
  installation or provider operations. Merely enabling a workflow in GitHub is insufficient.
- The old evaluator cron is **09:47 German time on 24 October**. Its definition
  is retained for recovery, but the disabled workflow will not start it. The
  data-opening and 13:30 age-key jobs are also disabled. There is no timed activation.
- Static HF pages and already-uploaded files can still exist. Stopping Actions
  does not take down hosting, withdraw downloads or erase previous publication.
  A form or stale heartbeat on an old page does not mean processing is active.
- The backup Space is now **private**, by organizer instruction on 23 October.
  Only authorized HulaEarth organization members can view it. Runtime activation
  does **not** change its visibility. A participant frontend takeover requires
  the separate, explicit public-access step below; private scoring/reporting alone
  does not require reopening the Space.
- Primary website deployment, independent data/key delivery and Google Form
  settings were not changed. **Those releases must be implemented independently**
  if the primary website needs them; these stopped jobs will not do them.
- No data, receipts, team history, accepted CSVs, keys, reference model, scoring
  rules or final flags were deleted/reset. No private result or age key is published
  by the control. Both repository controls must be operated; one cannot control the other.

## Fast route: what to do in the first minutes

1. **Confirm the incident scope.** Full HF frontend + evaluator takeover? Only
   private scoring/reporting? Only data/key delivery? Record one responsible
   operator and backup. Do not run both primary and backup as competing score authorities.
2. **Read current state.** Open both control pages below, use `main`, run
   **status**, inspect the run summary and current configuration. A historic
   receipt is not a fresh status check. Preserve primary website submissions and
   original server timestamps before any cutover.
3. **Enable checks**, if needed, with mode **enable-checks**, confirmation
   **`ACTIVATE HF BACKUP`**. This does not open runtime or release gates.
   Check credentials, frozen contract and available private Actions capacity.
4. **For full HF takeover:** run **enable-runtime** in **both** repositories with
   that confirmation. Wait for both controls to complete. This enables processing/
   publishing workflows and their existing triggers; release workflows stay disabled.
   Reopen and verify the Space using **Space visibility during a takeover** below
   before directing participants there. Do not assume enabling Actions reopens it.
5. Start private **Active competition evaluator → event** during its valid event
   window, or **rehearsal** for a ten-minute practice session. Do not wait for a
   missed cron to replay. Verify a fresh successful poll/heartbeat and practice acceptance.
6. Verify pages/config/roster through private **Trusted private evaluation → sync**
   and public **Publish team and submission feedback**; deploy public pages only
   if needed. Complete the final acceptance/arming checks before real submissions.
7. **Keep release profiles off** if the primary system already serves data/key.
   If a release is genuinely required, use the separate release procedure below.
8. Announce one participant route, deadline, final-choice rule and incident policy
   equally. Preserve original submissions and quota; do not silently discard primary entries.
9. After use, run **stop** in both controls and require fresh **`all_stopped=true`**.

If a required credential, identity binding, hidden bundle or contract is missing,
do not fabricate it to make a readiness check green. Use the limited fallback that
can actually be verified; tell the organizer exactly what remains unavailable.

## Space visibility during a takeover

The private backup is at
[HulaEarth/ai-for-nature-hula-earth](https://huggingface.co/spaces/HulaEarth/ai-for-nature-hula-earth).
Its content was aligned with the primary website's clearer introduction, data
explanations and six-step guide. It retains the backup's existing submission
contract and behavior: HF sign-in, captain-only final choice, 159,150 rows,
24 MB CSV limit, 10:00 materials, 11:00 kickoff, 17:30 deadline and 5+2 minute
presentations. The primary site's smaller test, GitHub authentication, automatic
star selection and some changed schedule text were **not** imported. See
[`docs/page-content-alignment.md`](docs/page-content-alignment.md). Verify the
incident's agreed contract before switching; a visual match is not state migration.

For participant use, an authorized HulaEarth maintainer opens
[Space Settings](https://huggingface.co/spaces/HulaEarth/ai-for-nature-hula-earth/settings),
finds **Space Access control**, selects **Public**, and waits for the explanatory
text to say it is public. Do this only within an explicitly authorized frontend
takeover. Publishing static files or enabling either repository's runtime does
not perform this step. The low-level API equivalent is
`HfApi(token=...).update_repo_settings(repo_id="HulaEarth/ai-for-nature-hula-earth", repo_type="space", private=False)`;
use an existing authorized credential, never place it in source, chat or a URL.

Then verify from an ordinary participant account and a signed-out session:

1. The Space shell and static homepage load, and Data/Rules/Guide/Register/Submit/
   Leaderboard navigation retains its styling. No special organizer-only signed
   URL should be required by participants.
2. HF OAuth returns to the correct Space, team invitations/approval work, a neutral
   practice upload receives a provider receipt and is accepted by a fresh worker.
3. Submission-key ID, manifest hash, full sample row count, release times and
   captain-only final choice agree with the activated evaluator. Check any
   incident-specific changes equally across frontend, private evaluator and starter.
4. Primary website receipts and team mappings have been preserved, with the
   cutover policy announced. They are not automatically visible in this backup.

While private, anonymous API and static-page requests return HTTP 401/404. This
is expected access control, not a broken deployment. The existing participant
inbox/feedback flow is not certified for an organization-private Space; making
every participant an organization member is not the recovery plan.

After a frontend incident ends, run **stop** in both repositories and select
**Private** in Space Settings again. Verify the settings text and signed-out
HTTP denial. Stopping Actions alone does not restore privacy. Keep the guides
and event history; do not delete the Space or rotate working keys as a shutdown step.

## Control pages and modes

- [Competition: Backup platform control](https://github.com/hulaearth/ai-for-nature-competition/actions/workflows/backup-control.yml)
- [Private evaluator: Backup platform control](https://github.com/hulaearth/ai-for-nature-evaluation/actions/workflows/backup-control.yml)

Choose **Run workflow → main**. Stop/status need no confirmation. All enabling
modes require the exact confirmation `ACTIVATE HF BACKUP`. No secret value is
requested. An ordinary repository reader cannot dispatch a workflow; use an
authorized maintainer account. A signed-out 404 is not proof the private repo is missing.

| Mode | Effect | Does not do |
| --- | --- | --- |
| `status` | Live read of flags, workflow states and active runs | Changes nothing |
| `stop` | Set runtime/releases false; disable every non-control workflow, including unrecognized ones; cancel queued/running jobs; verify and save receipt | Delete data/secrets or stop the primary website |
| `enable-checks` | Enable test workflows; private repo also enables read-only readiness | Open runtime/release gates or run checks automatically |
| `enable-runtime` | Set runtime true, releases false; enable processing/publishing/reporting profiles and checks; disable release workflows | Enable final submissions, open data, publish key, dispatch a worker or reveal final scores |
| `enable-releases` | Set release gate true; enable only that repo's release profile | Enable scoring, dispatch a release or bypass its clock/integrity guards |

`enable-runtime` deliberately disables releases even if they were previously on.
If both are needed, activate runtime first and releases second. `enable-checks`
does not stop an already active runtime; use `stop` first when starting a controlled
check from standby. Enabling workflows restores their existing **push/schedule**
triggers too. A remaining event-day cron can then fire; "does not dispatch" is not
a promise that enabled scheduled workflows will remain idle.

The retired `release-materials.yml` is never part of an enabling profile. It
cannot publish the starter/guide. The private website owns their delivery.

The controller itself has **no schedule**. Installing/updating its own workflow,
script, or `config/backup-install.json` on main runs **stop**, never activation.
Ordinary documentation/data-state commits do not activate it. This provides an
SSH-only recovery route when API credentials are unavailable; see troubleshooting.

## Command-line route

Use an authenticated GitHub CLI; verify `gh auth status` without printing tokens.
The operator needs Actions write and Contents write for **both named repos**;
the control itself uses each job's automatic `GITHUB_TOKEN`. No new long-lived
secret or organization-wide PAT is required. Publisher-only credentials cannot
administer the private evaluator.

```bash
# Stop both; safe and idempotent.
gh workflow run backup-control.yml -R hulaearth/ai-for-nature-competition --ref main -f mode=stop
gh workflow run backup-control.yml -R hulaearth/ai-for-nature-evaluation --ref main -f mode=stop

# Inspect the runs you actually dispatched; do not infer success from dispatch.
gh run list -R hulaearth/ai-for-nature-competition --workflow backup-control.yml --limit 5
gh run list -R hulaearth/ai-for-nature-evaluation --workflow backup-control.yml --limit 5
gh run watch RUN_ID -R REPOSITORY --exit-status
```

Replace `RUN_ID` and `REPOSITORY` with the actual run and one named repo. Wait for
each required phase before the next; do not fire an unattended chain of dispatches.
GitHub may replace an older pending run in a concurrency group. One operator
should coordinate control changes rather than issuing contradictory commands.

```bash
# Only on explicit organizer activation instruction.
gh workflow run backup-control.yml -R hulaearth/ai-for-nature-competition --ref main \
  -f mode=enable-runtime -f confirmation='ACTIVATE HF BACKUP'
gh workflow run backup-control.yml -R hulaearth/ai-for-nature-evaluation --ref main \
  -f mode=enable-runtime -f confirmation='ACTIVATE HF BACKUP'
```

After completion, `status`/`backup-status.json` should show runtime true, releases
false, expected runtime workflows active. **`all_stopped=false` is expected after
activation**; it is the shutdown acceptance criterion, not an operational health score.

## Before running the evaluator

Use current **main** and preserve its durable state. Do not restore an old ledger
over it or clone participant request branches. Private repo must remain private.

Check the following without exposing values:

- Private secrets **SUBMISSION_PRIVATE_KEY** and **COMPETITION_PUBLISH_TOKEN**;
  competition **HF_SPACE_TOKEN** (preferred) or **HF_TOKEN**. Listing a secret's
  name does not prove scope, expiry, organization approval or correctness.
- RSA public key ID matches private PEM and configs. **RSA decrypts prediction
  envelopes; age decrypts test archives.** Never publish the RSA key as a fallback.
- Event/Space/repo IDs, frozen dataset hash, starter delivery pin, row count,
  caps and metric agree. Current CSV requires **159,150 rows**, each supplied ID
  exactly once, finite scores in `[0,1]`; caps 24 MB CSV / 36 MB envelope.
- Complete private solution/eligibility/reference/attribution and accepted archive;
  do not substitute `legacy-demo/` or `evaluation/scoring.py`. Production is `aifn/`.
- Organization private Actions allowance, concurrency and branch rules permit
  private durable commits and sanitized public writes. No automatic purchase.
- Current native registry is authoritative. Archive excluded rehearsal teams
  through supported organizer controls; do not delete their receipts or reset quota.

### Start and verify worker coverage

```bash
gh workflow run active-worker.yml -R hulaearth/ai-for-nature-evaluation --ref main -f mode=event
```

Event mode accepts startup from 30 minutes before the materials time until
deadline +15 minutes; it waits until materials time and stops at that limit.
With current settings: earliest event dispatch **09:30 German**, processing
from **10:00**, stop **17:45 on 24 October**. Outside that window it exits without
event coverage. A missed 09:47 cron does not replay when enabled later.

For an independent short practice check use `-f mode=rehearsal` (ten minutes).
Do not run repeated ten-minute sessions expecting full-day unattended coverage.
The bounded four-hour event sessions have continuation/recovery jobs. Monitor
actual startup and continuation; a green control is not a worker heartbeat.

Check public GitHub
[site/worker-status.json](https://github.com/hulaearth/ai-for-nature-competition/blob/main/site/worker-status.json):
correct event, `status=running`, recent `updated_at` and `last_successful_poll`.
The worker polls roughly every 15 seconds, health about every minute; live
readiness requires a heartbeat younger than three minutes. A stale old timestamp
does not mean a worker is still running. Poll workflow provides a separate
five-minute event-window fallback after it is enabled.

Use **Trusted private evaluation → process** for a one-off drain, or **sync** to
export current allowlisted config/roster/results. Public feedback publication
may lag due to coalescing/rate limits; private acceptance and original receipt
remain authoritative. Do not upload the same file again merely because HF is slow.

## Website and state cutover

The private website is a separate implementation. **There is no automatic import
of its teams, submissions, receipt timestamps, quotas, selections or jury scores
into this HF ledger.** A shared `row_id,score` CSV format alone does not provide
that migration. See private [website/evaluator handover](https://github.com/hulaearth/ai-for-nature-evaluation/blob/main/handover.md)
for integration boundaries.

Before changing the official route, the organizer must decide and record:

1. When the primary intake pauses, which system is the authoritative receipt
   store, and how already received primary entries remain eligible.
2. Verified mapping from primary team/captain to stable HF accounts. Do not infer
   identity from a display name, create replacement teams blindly or impersonate users.
3. How accepted attempts and final choice carry over without granting extra
   attempts, losing entries, duplicating scores or comparing hidden scores to choose.
4. Whether deadline/access changes are necessary and announced equally before
   private-score disclosure. Preserve original primary receipt evidence.

If no tested adapter exists and time is too short, do not invent one directly
against the production ledger. Keep the primary archive as the record, use a
verified narrower recovery (for example report generation only from compatible
sealed data), or obtain an explicit fair resubmission/incident policy. Document
the limitation. Never silently replace original timestamps with browser times.

For the known HF frontend, use the existing
[Space](https://huggingface.co/spaces/HulaEarth/ai-for-nature-hula-earth) or its
standalone origin. Do not move its OAuth callback to the private website domain
without a tested authentication/routing migration. Browser authentication lasts
about one hour; participants may need to sign in again.

## Final acceptance and arming

Enabling runtime **does not** set `data_ready` or `final_submissions_enabled`.
They remain private scoring controls. Readiness phases are `preflight`, `armed`
and `live`; run the actual hosted check after enabling the checks/runtime profile.
Never create fake passed evidence or bypass an old check just to turn it green.

Known gap: readiness still consumes the former materials-release setup receipt;
the private website owns current materials. A previous armed receipt does not
certify that replacement. Resolve the check/evidence properly for the actual
backup route and preserve remaining acceptance limitations for the organizer.

Minimum participant acceptance: ordinary HF sign-in, confirmed team/captain,
neutral **120-row Practice** upload → Accepted, durable/restart readback, and
current feature/sample access on intended runtime. Practice must use an excluded
organizer team and spends no final attempt. Do not generate mock final standings.

Once approved checks actually pass, set verified data readiness privately and
use `scripts/configure_event.py --enable-final` with current explicit times,
commit, **sync**, verify HF feedback and run armed/live readiness. The helper
keeps finals disabled if that flag is omitted. It refuses event contract changes
after accepted final entries. The [full handover](https://github.com/hulaearth/ai-for-nature-competition/blob/main/HANDOVER.md)
has the exact configuration command. A page button is not backend authorization.

## Data/key delivery is a separate decision

The primary plan is **10:00 data/material access**, advertised work start **11:00**,
test **age-key unlock 13:30**, deadline **17:30**, all **24 October 2026,
Europe/Berlin (UTC+02:00)**. Those schedules are dormant while disabled. Starting
earlier requires an equal organizer announcement; disabling HF does not configure
the private website's releases.

If primary data/key delivery already works, leave both release profiles off.
Use the same verified supplied artifacts; do not publish another dataset version.

If HF download access is needed, private control **enable-releases** enables
`release-hf-data.yml` only. Check current **DATA_RELEASE_HF_TOKEN**, whole-tree
fingerprint (not an old verification receipt), manifest and source licenses.
Run release mode **verify**, then **publish** after 10:00 inside its valid window.
It opens only the fixed HF dataset, not Drive. Ordinary account/anonymous readback
is required. Changing any dataset path can invalidate the frozen release tree.

If HF/GitHub key publication is needed, competition control **enable-releases**
enables `release-test-key.yml` only. Check **TEST_RELEASE_KEY** age identity and
frozen normalization/fingerprint, plus Space credential. Run **verify**, then
**publish** at/after 13:30 inside the allowed window. Inspect per-provider success;
either HF or the independent public GitHub backup can carry the verified identity.
**Never substitute SUBMISSION_PRIVATE_KEY.**

```bash
# Only after explicit decision to activate the release capability.
gh workflow run backup-control.yml -R hulaearth/ai-for-nature-evaluation --ref main \
  -f mode=enable-releases -f confirmation='ACTIVATE HF BACKUP'
gh workflow run backup-control.yml -R hulaearth/ai-for-nature-competition --ref main \
  -f mode=enable-releases -f confirmation='ACTIVATE HF BACKUP'
```

Wait for controls, then dispatch the needed verification/publication separately.
Existing scheduled triggers can also fire once enabled; respect the separate
release decision. Release CLI has no clock override. After expiry, do not weaken
the guard or backdate a receipt; use organizer-approved recovery with preserved
timestamps and exact matching artifacts. Release control changes no final scoring flags.

## Closure, final slides and reporting

Runtime activation enables the private reporting workflow, but **nothing is
generated automatically merely by activating the backup**. Production reporting
requires the compatible sealed selection, successfully published finals, archived
accepted CSVs and matched reporting/reference metadata.

1. After deadline +at least two minutes: reconcile, resolve transient requests,
   explicitly **seal**, then **publish-final** on organizer instruction.
2. Successful final publication automatically calls **Private closing report**.
   It produces the current full library (36 slides with optional real-panel
   maps/context), offline picker, PDF, presenter notes and chart-data archive.
3. Download private **closing-report-PRIVATE** artifact. Keep output private and
   review before projection. Choose/reorder in `jury-slides.html`, export selected
   PDF or present offline. Saved order JSON transfers slide IDs, not mock scores.
4. Drive/Slack are optional separate credentials/steps. Green overall job does
   not prove a `continue-on-error` delivery succeeded. Artifacts expire after
   30 days; retain protected independent copies. Exact map inputs stay private.
5. If only rendering/delivery failed, rerun **Private closing report → production**;
   do not publish finals a second time just to regenerate slides. Check uncertain
   Slack delivery before explicit retry. Official selections/points stay unchanged.

Use [the detailed evaluator/slides guide](https://github.com/hulaearth/ai-for-nature-competition/blob/main/docs/evaluation-and-closing.md)
and private `docs/CLOSING_REPORT.md`, `docs/OFFLINE_PRESENTATION.md`,
`docs/DRIVE_DELIVERY.md`, `docs/SLACK_SETUP.md` and `docs/POINT_MAP_REPORTING.md`.
The short/expanded proposed closing order is not a replacement automatic generator.

## Stop again and prove it

Run control **stop** in **both** repositories. No confirmation is needed. Check:

- `runtime_enabled=false`, `releases_enabled=false`.
- Every non-control workflow has a disabled state, not just skipped jobs.
- `active_runs=[]` and **`all_stopped=true`** in a fresh receipt.
- Both controls themselves remain active, with no schedule.

Cancellation is asynchronous. Controller first requests cancellation, later
force-cancels if needed, and fails visibly if any controlled job still appears
active. If the first stop says incomplete, inspect remaining run IDs, wait for
cancellation to settle and run **stop** again. Do not call a partial stop complete.
Initial installation can show intentionally failed jobs at the new standby guard
or cancelled tests; these are not evidence that a key was released.

Files already published cannot be made secret again by stopping. Snapshot current
private main, accepted archives, receipts/choices and protected keys. Keep the
primary incident record and any approved cutover mapping. No history squashing,
receipt edits, silent quota resets or deletion of accepted CSVs.

## Troubleshooting for an agent

| Problem | Action |
| --- | --- |
| Controller unavailable/disabled | Maintainer: `gh workflow enable backup-control.yml -R REPOSITORY`, then run stop/status. If all repository Actions are globally disabled, an admin must enable Actions; do not change billing or privacy. |
| No GitHub API login, SSH works | To **stop only**, commit a fresh `config/backup-install.json` request on current main. Its push triggers control in stop mode. Confirm bot receipt; do not use this to activate or force-push. Activation needs explicit authenticated control/confirmation. |
| Cannot stop/write receipt | Inspect token Actions/Contents write, org policy, branch rules and exact repo. Fail-closed gates remain false on the installed snapshot; verify actual disabled states before claiming success. |
| Workflow enabled but exits at guard | Correct control profile was not activated, or checkout read standby main. Enable through controller; do not remove guard. |
| Controller enabled runtime but no heartbeat | Activation does not dispatch worker. Check event window, queue/capacity, actual worker run and secrets. Dispatch event or rehearsal explicitly. |
| Key/data not available at planned time | Releases are stopped intentionally. Check independent primary delivery first; use separately approved release profile only if needed. |
| HF UI accepts upload but stays Pending | Check receipt/worker/private checkpoint and HF mirror. Uploaded is not Accepted; do not duplicate. |
| Private website entries missing from HF | No automatic migration exists. Preserve primary archive; apply verified mapping/incident policy, not a fabricated ledger. |
| Guarded time/contract check fails | Verify real current date, event config and data fingerprint. Do not change system clock, trust browser times or weaken frozen checks. |
| Local recovery considered | Existing active worker is restricted to ephemeral Actions checkout and resets it. Do not run it in a human working tree. Use a tested serialized private maintainer route with the same durable state, explicitly stop hosted writers, preserve fingerprints and run the local standby guard first. |

## Required incident record

Before handing back to organizers, leave a private record of: human authorization
and scope; actual UTC/local activation/stop times; both control run IDs and final
flags/states; worker heartbeat; chosen intake/receipt authority; primary archive
snapshot and account/entry mappings; contract/key/reference fingerprints; actual
acceptance/arming status; release actions (or deliberately none); sealed selection;
report artifact/Drive receipt; unresolved checks and the next responsible person.
Never include credential values, private labels or sensitive site coordinates in
chat/public issues. Report verified limitations plainly. Hand back to a single
authoritative platform and require shutdown receipts after backup use.
