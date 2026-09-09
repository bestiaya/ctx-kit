#!/usr/bin/env python3
"""ctx-watermark.py — context watermark doorbell for claude CLI sessions (ships with ctx-kit)

What it is for
  A UserPromptSubmit hook. Once per turn, before the model reads the prompt, this script looks
  up how much context the session is already carrying and — only when that number is past the
  yellow or the red line — prints one line for the owner and one for the model. Under the line
  it prints nothing at all, so a session nowhere near full pays no attention tax and no tokens.
  The session gets a reading of itself; deciding what to do with it stays with the owner.

The measure, the same one in three places
      watermark = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
  read off the last main-thread assistant record in the session transcript. output_tokens is
  not part of it. The same three-term sum is what:
    - scripts/cache-audit.py in this kit prints as its `ctx` column (the weekly checkup), and
    - the claude CLI status line calls `used_percentage`, which its documentation defines with
      exactly these three terms and explicitly without output_tokens.
  So the doorbell, the weekly checkup and the built-in status line all quote the same number.
  This script deliberately invents no fourth measure, and reports absolute tokens, not a
  percentage (a 200k window and a 1M window would not be comparable as percentages).

What it reads
  Only two things per transcript record: what kind of record it is, and the usage numbers.
  No conversation text is read, parsed or printed. Sidechain records are skipped: a subagent's
  bill is not this session's watermark. The transcript is written asynchronously, so the number
  can lag the live conversation by at most one turn — late is fine here, wrong is not.

How it reads it
  From the tail, in widening windows (64KB, 256KB, 1MB, 4MB, 8MB cap), stopping at the first
  main-thread assistant record that carries usage numbers. Session logs reach tens of MB; this
  hook fires every single turn under a 30 second timeout, so parsing the whole file the way the
  weekly checkup does is not an option here. A window that is already parsed is not parsed again.

Thresholds
  CTXKIT_WATERMARK_YELLOW / CTXKIT_WATERMARK_RED, in tokens, `400000` and `400k` both accepted.
  Anything unparseable or non-positive falls back to the defaults below, quietly. Set them in
  settings.json under `env` to move a line without touching this file. Red is tested first, so
  the two can be set in any order without producing a confusing reading.
  The defaults are a spending preference, not a price tier and not a quality cliff: the whole 1M
  window bills at the standard rate and nothing steps up at 200k, so these lines are meant to be
  moved rather than obeyed. Where they sit is measured, not guessed: of nine sessions audited
  on 2026-09-07, all nine peaked past 300k, four past 400k and one past 500k, so the old 300k
  yellow rang on every one of them with work still left in them. What they buy and what staying
  costs: 04-HANDBOOK.

Failure posture
  A doorbell may never break the turn it rings in. Missing file, unreadable file, half-written
  JSON, no usage anywhere, junk on stdin, junk in the environment — every one of them means
  zero bytes on stdout and exit code 0. This script has no failing exit code and no error
  message; if something is wrong, the bell simply does not ring.

Exit codes
  0  always.
"""
import json, os, sys

YELLOW_DEFAULT = 400000
RED_DEFAULT = 500000

# Every line this script prints starts with this, in both channels, so it is greppable in a
# transcript, in a stream-json log, and in the owner's terminal.
PREFIX = "[ctx-kit watermark]"

# What the model is told to do about the reading. The durable version of this lives in the
# rule block (CLAUDE-snippet.md); this sentence is here so the reminder still works for someone
# who installed the plugin and never pasted the rules.
#
# It is written as something the model can actually check. "Say it once per band" on its own does
# not hold up: this hook has no memory between turns and rings again on every turn the session is
# over the line, so the only record of what was already said is the conversation itself. Naming
# the band inside the sentence is what makes the check answerable -- "have I already said yellow?"
# is a question about the visible transcript; "have I already said this?" is not.
def action(band):
    """What to do about a `band` reading, phrased so the model can check it against the thread."""
    return (
        "Report this once per band: look back over your own earlier replies in this session -- if "
        "you have already passed a %s reading to the owner, say nothing about it this turn. If you "
        "have not, tell the owner in one sentence and offer /ctx-handoff, then stay quiet until the "
        "band changes. Never act unasked." % band
    )

# Tail windows, in bytes: 64KB, 256KB, 1MB, 4MB, and an 8MB cap. Past the cap the answer is
# "no reading", not "read the whole file".
WINDOWS = (64 * 1024, 256 * 1024, 1024 * 1024, 4 * 1024 * 1024, 8 * 1024 * 1024)

USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def parse_threshold(raw, default):
    """A threshold from the environment. '250000' and '250k' both mean 250000.

    The number in that example is deliberately not one of the lines this script ships with:
    an example that happens to read like a default gets quoted as one.

    Anything else — empty, misspelled, negative, zero — falls back to `default` without a
    word, because a typo in a config file must not silence the doorbell or crash the turn.
    """
    if raw is None:
        return default
    text = str(raw).strip().lower().replace("_", "").replace(",", "")
    multiplier = 1
    if text.endswith("k"):
        text, multiplier = text[:-1].strip(), 1000
    try:
        value = int(round(float(text) * multiplier))
    except Exception:
        return default
    return value if value > 0 else default


def watermark_of(piece):
    """The three-term sum for one transcript line, or None if this is not a line we count.

    Not counted: blank lines, a half-written line at the tail, anything that is not an
    assistant record, sidechain (subagent) records, and records carrying none of the three
    usage numbers.
    """
    piece = piece.strip()
    if not piece.startswith(b"{"):
        return None
    try:
        record = json.loads(piece)
    except Exception:
        return None
    if not isinstance(record, dict):
        return None
    if record.get("type") != "assistant" or record.get("isSidechain"):
        return None
    message = record.get("message")
    usage = message.get("usage") if isinstance(message, dict) else None
    if not isinstance(usage, dict):
        return None
    total, found = 0, False
    for key in USAGE_KEYS:
        value = usage.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        total += int(value)
        found = True
    return total if found else None


def last_watermark(path):
    """The newest main-thread watermark in `path`, read from the tail. None if there is none."""
    size = os.path.getsize(path)
    if size <= 0:
        return None
    parsed = 0  # trailing pieces already looked at, so a wider window does not redo them
    with open(path, "rb") as handle:
        for window in WINDOWS:
            start = max(0, size - window)
            handle.seek(start)
            # Read against the size taken above, so every window is a suffix of the same byte
            # range even if the session appends to the file while this runs.
            pieces = handle.read(size - start).split(b"\n")
            if start > 0:
                pieces = pieces[1:]  # the first piece is the tail half of an earlier line
            fresh = pieces[: len(pieces) - parsed] if parsed else pieces
            for piece in reversed(fresh):
                tokens = watermark_of(piece)
                if tokens is not None:
                    return tokens
            if start == 0:
                return None  # the whole file has been read
            parsed = len(pieces)
    return None  # past the 8MB cap without a usable record


def render(tokens, band, line):
    """The one line both channels carry, e.g.
    `[ctx-kit watermark] 513k / red 500k — time to close out (/ctx-handoff)`."""
    return "%s %dk / %s %dk — time to close out (/ctx-handoff)" % (
        PREFIX, round(tokens / 1000.0), band, round(line / 1000.0)
    )


def main():
    payload = json.loads(sys.stdin.read())
    path = payload.get("transcript_path") if isinstance(payload, dict) else None
    if not isinstance(path, str) or not path:
        return
    tokens = last_watermark(os.path.expanduser(path))
    if tokens is None:
        return

    yellow = parse_threshold(os.environ.get("CTXKIT_WATERMARK_YELLOW"), YELLOW_DEFAULT)
    red = parse_threshold(os.environ.get("CTXKIT_WATERMARK_RED"), RED_DEFAULT)
    if tokens >= red:
        band, line = "red", red
    elif tokens >= yellow:
        band, line = "yellow", yellow
    else:
        return  # under the line: not one byte

    reading = render(tokens, band, line)
    # Two channels on purpose: `systemMessage` is the one the owner sees in the terminal (and
    # arrives as an informational message in stream-json), `additionalContext` is the one the
    # model reads. Neither one alone would reach both.
    #
    # No trailing newline, and nothing may wrap or re-echo this: claude CLI treats stdout that
    # starts with `{` and ends with `}` as JSON, and stdout it fails to parse is dropped whole
    # with a hook error instead of reaching either reader.
    sys.stdout.write(json.dumps({
        "systemMessage": reading,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reading + ". " + action(band),
        },
    }))


if __name__ == "__main__":
    try:
        main()
        sys.stdout.flush()
    except Exception:
        # Silence, not a stack trace, not a failing exit code. If stdout itself is gone, point
        # it at the void so the interpreter's own shutdown flush cannot fail the exit code.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except Exception:
            pass
    sys.exit(0)
