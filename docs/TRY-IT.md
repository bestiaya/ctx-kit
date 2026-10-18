# Try a two-chat handoff

This local exercise uses a **synthetic, fictional fixture**. It does not represent a real customer project or a measured productivity gain. You will verify an existing Python CSV command in one chat, leave one feature unfinished, then ask a new chat to take over and finish it. The [fixture files](https://github.com/bestiaya/ctx-kit/tree/main/examples/session-handoff) live in the source checkout; they are not bundled into the generated skills.

## Prepare a temporary Codex project

Run this from the ctx-kit repository root in a macOS or Linux shell with Python 3.9+. Use your Python 3 executable if it has a different name. The package builder refuses to overwrite an existing output. The project and package stay under a new temporary directory; no user-level skill or configuration is changed.

```bash
DEMO_DIR="$(mktemp -d)"
PROJECT_ROOT="$DEMO_DIR/project"
python3 scripts/build_package.py --platform codex --output "$DEMO_DIR/package"
mkdir -p "$PROJECT_ROOT/.agents/skills"
cp -R "$DEMO_DIR/package/skills/ctx-"* "$PROJECT_ROOT/.agents/skills/"
cp -R examples/session-handoff/starter/. "$PROJECT_ROOT/"
cp examples/session-handoff/check_acceptance.py "$PROJECT_ROOT/"
awk '/^```markdown$/{inside=1;next} /^```$/{inside=0} inside{print}' "$DEMO_DIR/package/AGENTS-snippet.md" > "$PROJECT_ROOT/AGENTS.md"
printf 'Open this project: %s\n' "$PROJECT_ROOT"
cd "$PROJECT_ROOT"
python3 unpaid.py invoices.csv
```

The last command should print the three unpaid invoices, with `250`, `500`, and `125` cents in source order. The packaged `AGENTS-snippet.md` names `ctx-checkup`, `ctx-review`, and `ctx-method-doc` as well as the four skills used here, so this setup installs **all eight** skills. In your existing project, merge its fenced block into your existing `AGENTS.md` instead of replacing that file. Check the installed skills in Codex; if your client requires it, reopen the project to load them.

## Chat 1: record the state and hand off

Open `PROJECT_ROOT` as the Codex project and send:

> Use `ctx-kickoff` for this fictional CSV CLI exercise. Verify that `unpaid.py` currently emits only unpaid invoices in CSV source order. Record the decision that `amount_cents` is an exact integer and must never be converted through floating point. The remaining task is to add an optional `--min-cents N` argument: `N` is a nonnegative integer, inclusion is `amount_cents >= N`, and omitting it preserves today's output. Do not implement the option in this chat. Record the verification evidence and remaining task in the project case, then use `ctx-handoff`. Give me the absolute case path and the first action for the successor.

Check that the case identifies the completed verification, the exact-cents decision, and the unfinished filter in its H gap or E task. Keep the absolute case path from the handoff. Do not treat a written handoff as proof that the feature is finished.

## Chat 2: take over and finish

Start a **new chat in the same project**. Send only the path and the continuation request; do not paste Chat 1's transcript or re-explain the decision:

> Use `ctx-takeover` to take over the case at `<absolute case path from Chat 1>`. Continue the first unfinished task, implement it in this project, and run the independent acceptance command below. Update the case with the result and remaining gaps. If the case lacks a required decision, report that gap before changing behavior.

Run the acceptance yourself from the temporary project root (the new chat does not need the shell variables from setup):

```bash
python3 check_acceptance.py ./unpaid.py
```

It should print `PASS: default behavior, inclusive minimum, unpaid filter, order, exact cents, invalid minimum`. This check uses its own CSV, including cents above floating-point's exact-integer range. It tests the recorded decision and the unfinished behavior independently of the implementation. Before Chat 2, failure on the missing `--min-cents` option is expected. Also use `ctx-status` in Chat 2 to check that the case and task board agree; a passing script alone does not verify the handoff records or native skill loading.

You can use your own project instead of the fixture: pick a small real task with one working behavior, one explicit decision that affects the implementation, and one unfinished change with a command you can run independently. Install into that project's `.agents/skills/`, keep its existing `AGENTS.md`, make the first chat record and hand off, and give the second chat only the case path. Keep private project data out of any public issue. Feedback is most useful with the platform, which step failed or felt unclear, the expected and actual result, and whether the acceptance command and case state agreed; use a [GitHub issue](https://github.com/bestiaya/ctx-kit/issues) if you want to share it.

## Claude Code variant

For Claude Code, build with `--platform claude`, copy the generated `skills/ctx-*` directories into the temporary project's `.claude/skills/`, and extract the fenced block from `CLAUDE-snippet.md` into the new project's `CLAUDE.md`. The fixture and acceptance command are the same. Open the temporary project in Claude Code, confirm the skills are visible, then use the two prompts above. Native Claude skill discovery and this two-chat sequence still need separate client verification; a successful Codex exercise does not establish that result.

## Keep or remove the exercise

Your exercise lives only in the temporary directory printed by `printf '%s\n' "$DEMO_DIR"`. Keep it if you want to inspect the case records; when finished, remove that specific directory through your file manager. Do not remove any existing project's configuration or records.
