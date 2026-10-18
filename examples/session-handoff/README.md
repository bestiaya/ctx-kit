# Fictional handoff fixture

This is synthetic, fictional data and code for a local exercise. It is not a user case, a benchmark, or evidence that context-kit saves time or tokens.

`starter/unpaid.py` already prints unpaid invoices from a CSV in source order, preserving `amount_cents` as an integer. The two-session task is to verify and record that existing behavior, decide that money stays in exact integer cents, hand off with `--min-cents N` still unfinished, then implement that inclusive filter in a new chat. `check_acceptance.py` is a separate behavior check derived from those requirements. It is expected to fail against the starter because the option is not implemented yet.

Follow [Try it](https://github.com/bestiaya/ctx-kit/blob/main/docs/TRY-IT.md) for project-level installation, prompts, acceptance, and cleanup. The generated skill package does not contain this fixture; copy it from the source checkout before opening the temporary project.
