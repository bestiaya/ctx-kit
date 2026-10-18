# ctx-kit

**Keep the decisions. Continue the work in a new chat.**

[中文](README.zh-CN.md) · [Try the example](docs/TRY-IT.md) · [Claude setup](claude/README.md) · [Codex setup](codex/README.md)

Working on a task that takes more than one AI coding session? ctx-kit gives the next session a project record of what you decided, what is finished, what remains, and what needs your approval.

It is a set of file-based workflows for **Claude Code and Codex**. Your work stays in ordinary Markdown in your project.

## Start with one handoff

1. **Start a task.** Use `ctx-kickoff` to record its goal and current plan.
2. **Stop at a useful point.** Use `ctx-handoff` to save the decisions, unfinished work, and next action.
3. **Continue in a new chat.** Use `ctx-takeover` with the case file. Check its understanding, then continue the task.

The record is the handoff: a new chat can read it without requiring the old conversation to be pasted in. `ctx-status` gives you a view across the tasks you have recorded.

**[Try a small, reproducible handoff →](docs/TRY-IT.md)**

The example uses fictional project data and explicit checks. It is a walkthrough, not a benchmark or a claim about every model. You can also try the same steps on one real task in your own project.

## Install

**Ready-to-copy packages:** [Codex ZIP](https://github.com/bestiaya/ctx-kit/releases/download/v0.15.0/ctx-kit-codex-v0.15.0.zip) · [Claude ZIP](https://github.com/bestiaya/ctx-kit/releases/download/v0.15.0/ctx-kit-claude-v0.15.0.zip) · [SHA256SUMS](https://github.com/bestiaya/ctx-kit/releases/download/v0.15.0/SHA256SUMS). Extract the archive and follow `INSTALL.md` inside for project-level installation; no build is needed. The walkthrough fixture is in the source checkout.

Current source version: **v0.15.0**. Requires Python 3.9+ to build the packages; the builder uses only the standard library.

In a macOS or Linux shell:

```bash
git clone https://github.com/bestiaya/ctx-kit.git
cd ctx-kit
python3 scripts/build_package.py --platform codex --output /tmp/ctx-kit-codex
```

Use `--platform claude --output /tmp/ctx-kit-claude` for Claude Code. The output directory must not already exist.

Then follow the [Codex](codex/README.md) or [Claude](claude/README.md) instructions to copy the generated skills into **one project** and merge the provided instruction block. Building a package does not install it or edit your configuration. The [example guide](docs/TRY-IT.md) walks through this in a disposable project.

The generated skills contain their dependencies. Do not copy just the `SKILL.md` entry files from this repository.

**Upgrading from the old Claude plugin?** Plugin distribution and the optional `digest` agent have been removed. Follow the [migration notes](docs/MIGRATION.md) before installing the file-based package.

## What is included

Start with the first four workflows. The others are available when you need them.

| Workflow | Use it to |
|---|---|
| `ctx-kickoff` | Start or find the record for a task |
| `ctx-status` | See progress, open questions, and pending work |
| `ctx-handoff` | Save a handoff or close a completed task |
| `ctx-takeover` | Pick up an existing task in another session |
| `ctx-review` | Request and collect a review when you ask for one |
| `ctx-checkup` | Check collaboration records and available context-usage evidence |
| `ctx-profile` | Manage personal context with explicit save and adaptation steps |
| `ctx-method-doc` | Write practical method documentation |

Each task has one current owner for its record. Pending messages and unresolved items remain in the project files for the next owner to inspect. See the [handbook](docs/HANDBOOK.md) for multi-session work.

## Is it a fit?

Try it if you work across days, replace chats during a project, or need one place to see several tasks. For a short task completed in one chat, you may not need the extra records.

The workflows help an agent maintain and check state; they do not guarantee perfect recall, prevent every mistake, or establish token savings. A successful package build is not proof that a particular client has loaded the skills. The setup guides include checks for that distinction.

The quick-start guide is in English; the shared workflow instructions and detailed handbook currently use Chinese. Client capabilities differ, so a feature such as chat renaming may be unavailable even when the file-based workflow works.

## Tell us where it breaks

After one handoff, tell us: **what did the new session miss, and what did you have to explain again?** A short, redacted [issue](https://github.com/bestiaya/ctx-kit/issues/new?template=feedback.md) is enough. Please keep private conversations and project records out of public reports.

If this is useful for your workflow, **star the repository** to help other developers find it.

[Background](docs/BACKGROUND.md) · [Method](docs/METHOD.md) · [FAQ](docs/FAQ.md) · [Maintenance and verification](docs/MAINTAINING.md) · [MIT license](LICENSE)
