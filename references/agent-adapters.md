# Agent installation and native scheduling

The contract is capability-based: a host must be able to read/write vault files and run
Python 3.11+ for deterministic helpers. Source extraction and unattended scheduling are
additional capabilities. Do not claim every installation or every product edition has them.

## Installing the entry skill

Install the **whole** `llm-wiki/` directory, including scripts, templates, references and
operations, through the host's supported skill mechanism. Copying only `SKILL.md` is
insufficient. Read host documentation or discover its current skill roots when needed;
do not infer a global directory from the agent's name alone.

Initialization installs the five operation skills into the two vault-local directories
requested by this design: `.claude/skills/` and `.agents/skills/`. Short `CLAUDE.md` and
`AGENTS.md` entries point to shared vault rules. Other agents may load those files, load
only the installed entry skill, or need their own skill directory selected explicitly.

| Host | File adaptation | Scheduling adaptation |
|---|---|---|
| Claude Code | Vault `CLAUDE.md` and `.claude/skills/`; verify discovery in the current product | Inspect native scheduling available in this edition; ensure the execution environment can access local vault files |
| Codex | Vault `AGENTS.md` and `.agents/skills/`; respect the current host's skill roots | Discover native automation tools; use their actual schemas and inspect existing jobs before creating one |
| OpenClaw | Discover the active workspace; its skill directory may be supplied as an explicit installer target | Discover the native automation/cron tool and authorized delivery channel; inspect job status and delivery settings |
| Hermes | Use the active profile's skill system; a default home path is not proof of the active profile | Discover the installed scheduler tools and gateway delivery capabilities; pass native job identifiers back to the binding helper |
| Other hosts | Load the entry skill or use a confirmed skill-directory target | Require real scheduling, file access, channel delivery and no-change suppression; otherwise provide on-demand operation |

Official references checked during development on 2026-09-12:

- [OpenClaw skill loading](https://docs.openclaw.ai/tools/skills) describes workspace and
  project agent skill locations; check the installed version and workspace selection.
- [OpenClaw automations](https://docs.openclaw.ai/automation/cron-jobs) describes native
  automation facilities. Discover tool schemas at runtime rather than embedding an API version.
- [Hermes skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/)
  describes the skill system and update behavior; respect profile-specific configuration.
- [Claude Code scheduling](https://code.claude.com/docs/en/scheduled-tasks) distinguishes
  cloud, desktop and session scheduling. A cloud job without local files cannot maintain
  this local vault; a session-bound job may stop when its execution session stops.
- The Codex desktop host's available `automation_update` capability is authoritative
  for that host. Its availability here does not imply that another Codex environment has it.

## Installation verification

Use `skill_install` preview with discovered directories. The helper stages a plan and
checks file ownership hashes before writing; it does not overwrite changed or conflicting
skills. Use the host's native manager for managed installations if it requires one.
After installation, inspect all five skills and resolve their references to the hidden
runtime. Ask the host to list/reload skills if required, then verify actual discovery.
Installing into an unrelated agent's global profile needs explicit scope from the user.

Default vault-local links survive moving the whole vault. Recheck custom external
destinations after a move. Installed runtime copies are refreshed from the entry skill
bundle; user-edited runtime files cause a collision instead of being silently replaced.

## Scheduling handoff

1. Read the user's intended local times, timezone and recipient/channel. Do not guess
   work-end, email addresses, chat IDs or which local account should receive a message.
2. Discover native scheduling and delivery schemas. Check persistence, local file access,
   and no-change suppression. Source examples do not authorize subscriptions.
3. Inspect existing native jobs and local bindings; match this vault and destination.
   Use `schedule_plan` to get normalized schedule fields and a cohesive job prompt.
4. Create or update the actual native job using current tool arguments. Explicitly set
   the timezone or convert through the native supported mechanism; do not trust its default.
5. After verified success, call `schedule_bind` with the plan, host identity and returned
   IDs. Only then describe it as active. If unavailable, record that state and the limitation.
6. At each run, reconcile prior unacknowledged delivery, process pending cognition reviews,
   prepare new content and suppress output when empty. Deliver only to the configured target.
7. Keep actual native pause/resume/reschedule state in agreement with the local binding.

The skill does not install a scheduler, start a background process, assume a messaging
service, or write raw recurring-task directives into chat. If a host lacks delivery receipts
or quiet-success behavior, explain the practical limit instead of pretending equivalent support.
