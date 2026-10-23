# Participant materials: 10:00 German time

> **Retired controller — 23 October 2026.** The current
> `release-materials.yml` is an informational manual job; it does not execute the
> release described below. Starter delivery moved to the event website. See
> [HANDOVER.md](../HANDOVER.md#current-activation-gaps) for the unresolved 10:00/11:00
> timing and readiness migration. The remaining text describes the former setup
> and is retained for maintainers considering a deliberate port. Do not rely on
> these warm-ups, token or an old armed receipt for the current website release.

On **Saturday 24 October 2026 at 10:00 Europe/Berlin (08:00 UTC)** the guarded job opens `hulaearth/ai-for-nature-codebase`, pinned tag `hackathon-2026`, and publishes its release receipt.

The organizer explicitly opened `hulaearth/ai-for-nature-competition` and `HulaEarth/ai-for-nature-hula-earth` early for the colleague rehearsal. The registration and technical pages stay public. The updated participant PDF is held in the private starter and published on the Space only at 10:00; verification never uploads the PDF or opens the starter early.

The advance Drive folder stays data-only. Its restricted holding copy of the guide
does not need public access. Modeling, data analysis and AI-agent modeling start
at **11:00**, test inputs unlock at **13:30**, and submissions close at **17:30**.
The private evaluation repository is never a visibility-change target.

## One-time setup

Create an expiring fine-grained GitHub token with resource owner `hulaearth`,
**only the competition and codebase repositories**, Administration read/write
and Contents read. Administration is required to change repository visibility.
Do not grant access to the evaluation repository. If Hula requires approval,
approve this token before rehearsal. An expiry after the event and before the
end of October is sufficient.

Add it to the competition repository's **Actions repository secret** named
`MATERIALS_RELEASE_TOKEN`. It is separate from the scorer's publisher token.
The existing `HF_TOKEN` / `HF_SPACE_TOKEN` is reused. Do not put credentials in
HF Static Space secrets, issues, files, shell arguments or chat.

Run **Release participant materials at 10 German time**, mode **verify**. It
checks the exact frozen guide in the private starter at the pinned commit, the starter tag and current main-branch
plan, and performs same-value visibility updates to verify permission while
preserving the approved current visibility. It records `materials-release-setup.json` on HF.
Require `armed=true`, the expected release time and current source commit.
A missing token records `armed=false`; merely committing the job does not arm it.

Verify mode also runs after successful page deployments. It does not publish
the materials-release receipt and cannot open access early.

## On the day

Warm-up triggers at 09:17, 09:32 and 09:47 German time wait for 10:00; retries
at 10:02, 10:07 and 10:12 are idempotent. Every publication is server-time and
year/date bounded. Rechecking main stops a stale plan. After a partial release,
a retry completes the remaining steps rather than changing the frozen version.

GitHub scheduling can be delayed or dropped. An organizer should check that a
warm-up is running before 10:00. Manual dispatch in **publish** mode during the
last hour remains time-guarded. If both providers fail, use the prepared local
guide/starter copy and announce access equally; record the incident. Do not
make the scorer public as a workaround.

The public `materials-release.json` receipt enables the starter button even
after later scorer syncs. Ordinary page deployments retain this endpoint and
the separate test-key release files. Starter repository visibility enforces
its embargo; hiding a link or changing a browser clock does not.

After release, test the guide download and pinned starter using an ordinary
participant account. Revoke the materials token after the event. Team approval,
fairness decisions, sealing/final score publication and jury decisions remain
explicit organizer actions.

[GitHub scheduling limits](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
and [repository visibility permissions](https://docs.github.com/en/rest/repos/repos#update-a-repository).
