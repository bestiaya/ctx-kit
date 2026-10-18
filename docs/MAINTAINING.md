# Maintenance and verification

Run these from the repository root with Python 3.9+:

```bash
python3 scripts/check_kit.py
python3 -m unittest discover -s tests -v
python3 scripts/build_package.py --platform codex --output /tmp/context-kit-codex-check
python3 scripts/build_package.py --platform claude --output /tmp/context-kit-claude-check
```

Each package output must be new. Building validates and copies the publication inputs; it does not install skills, change user configuration, create a task, or claim ownership of existing work.

Before a public commit, stage only the intended source paths and run:

```bash
python3 scripts/check_public.py
```

This checks tracked/indexed files for private paths and recognizable credential material. It excludes ignored local records and is a focused guard, not a guarantee that every secret is detectable. Keep real cases, transcripts, user profiles, local configuration, and credentials out of public commits.

## Repository layout

- `docs/`: background, method, handbook, FAQ, migration and onboarding.
- `workflows/`: shared workflow instructions, maintained once.
- `templates/`: task boards, cases, handoffs and review records.
- `claude/` and `codex/`: platform setup and evidence boundaries.
- `scripts/` and `tests/`: standard-library packaging, checking and profile/history tools.
- `examples/`: fictional, reproducible walkthrough fixtures, separate from live project records.

The builder copies shared dependencies into each generated skill. Edit the source, rebuild, and replace an explicitly selected installation; do not maintain generated copies independently.

## Verification boundaries

Source links and portable packages are checked separately from a live client's discovery, tool permissions, and workflow behavior. To validate an installation, use a disposable project: create a task, save an unfinished item, hand it off, open a new chat, take it over, and check the recovered state and actual result.

The historic Claude measurements do not establish current Codex costs. Fixed token or time thresholds are not automatic handoff rules. See [Claude evidence](../claude/EVIDENCE.md) and [Codex evidence](../codex/EVIDENCE.md) for measured results and open questions.

For existing installations and retired components, use the [migration notes](MIGRATION.md).
