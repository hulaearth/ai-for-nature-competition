# Backup platform operating instructions

The private event website is primary. GitHub/Hugging Face automation is in standby
by organizer instruction. Read `BACKUP_ACTIVATION.md` before operational work.

- Do not enable workers, releases, deployment or notifications just because old
  docs mention an event-day schedule. Existing timers are disabled intentionally.
- An explicit human request to activate the backup authorizes the requested
  scope; proceed using the documented controller rather than asking repeatedly.
  Keep runtime and releases separate and preserve deadline/integrity guards.
- Operate both repositories as required. Verify actual workflow states and runs;
  shutdown requires fresh `all_stopped=true`, not merely a committed flag.
- Preserve private ledger, original receipts, accepted files, quotas and sealed
  choices. Primary website state is not imported automatically. No invented
  migration, identity mapping, timestamps or readiness proofs.
- Do not expose RSA/private keys, hidden labels, coordinates or credentials.
- Routine validation should run locally while standby remains in force. Updating
  the control script/workflow on main automatically runs stop; it never activates.
- `HANDOVER.md` and `docs/evaluation-and-closing.md` describe retained capabilities;
  current standby policy and `BACKUP_ACTIVATION.md` take operational precedence.
