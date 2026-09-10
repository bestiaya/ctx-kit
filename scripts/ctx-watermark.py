#!/usr/bin/env python3
"""ctx-watermark.py — context watermark doorbell for claude CLI sessions (ships with ctx-kit)

What it is for
  A UserPromptSubmit hook. Once per turn, before the model reads the prompt, this script looks
  up how much context the session is already carrying and — only when that number is past the
  yellow or the red line — prints one line for the owner and one for the model. Under the line
  it says nothing about the watermark, so a session nowhere near full pays no attention tax and
  no tokens for it. The session gets a reading of itself; deciding what to do with it stays with
  the owner.

  Two further readings ride on the same run, and neither one sets a line either:
    - when the bell rings, one more line saying by which route this context filled up, taken
      from cache-audit.py's own split so the doorbell and the weekly checkup cannot disagree.
      No bell, no make-up line: a quiet session is not parsed in full. The bell fires on the
      watermark and on nothing else — the make-up rides on it and can never ring it, however
      large any one route in it grows;
    - a session that started before the ctx-kit files it is running were last written gets told
      so, whatever its watermark. That one is not about spending — the fixes made since a long
      session opened reach new sessions and not it, and until now nothing said so. This script
      keeps no state between turns, so it prints that line on every turn the comparison holds;
      saying it only once is the session's own obligation, the same look-back the watermark
      bands ask for, and `CTXKIT_UPDATE_HINT=off` switches the line off outright.

The measure, the same one in three places
      watermark = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
  read off the last main-thread assistant record in the session transcript. output_tokens is
  not part of it. The same three-term sum is what:
    - scripts/cache-audit.py in this kit prints in its `p50 ctx` and `peak` columns (the
      weekly checkup), and
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

Where the installed files are
  Three places in one fixed order: `${CLAUDE_PLUGIN_ROOT}` when it is set — a plugin install
  sets it, and it is then the answer, found files or not — then `${CLAUDE_CONFIG_DIR}`, which
  is where a manual install lives for anybody who keeps their claude CLI configuration
  somewhere other than the default, then `~/.claude`, where the README's manual-install step
  puts the same tree. Underneath whichever one answers, the newest mtime among
  `skills/ctx-*/SKILL.md` and the kit's own files, each named rather than globbed, is taken as
  "when this machine's copy was last written" — a `scripts/*.py` glob would have read somebody
  else's script in that same directory as a ctx-kit update. Nothing there to stat means no
  reading and nothing printed, which is also what makes this quiet for anybody who keeps the
  kit somewhere else entirely.
  `CTXKIT_UPDATE_HINT=off` turns that reading off for good, which the two watermark lines do
  not need because they can be moved instead.

Failure posture
  A doorbell may never break the turn it rings in. Missing file, unreadable file, half-written
  JSON, no usage anywhere, no timestamp, no installed copy to compare against, junk on stdin,
  junk in the environment — every one of them means one reading fewer, and where none is left,
  zero bytes on stdout. Exit code 0 either way. This script has no failing exit code and no
  error message; if something is wrong, the bell simply does not ring.

Exit codes
  0  always.
"""
import datetime, glob, json, os, sys

YELLOW_DEFAULT = 400000
RED_DEFAULT = 500000

# Every watermark line this script prints starts with this, in both channels, so it is
# greppable in a transcript, in a stream-json log, and in the owner's terminal.
PREFIX = "[ctx-kit watermark]"

# The other reading gets its own mark rather than borrowing the one above: the docs define the
# watermark as "the reading on the line starting [ctx-kit watermark]", and a line that is not a
# watermark must not answer to that description. Greppable on its own terms.
UPDATE_PREFIX = "[ctx-kit update]"

# What counts as "this machine's copy of ctx-kit", under whichever root is found below. The
# scripts are named one by one rather than globbed: `scripts/*.py` also matches whatever else
# the owner keeps in `~/.claude/scripts/`, and editing one of those is not a ctx-kit update.
INSTALLED = (
    ("skills", "ctx-*", "SKILL.md"),
    ("scripts", "cache-audit.py"),
    ("scripts", "ctx-watermark.py"),
    ("scripts", "case-lint.py"),
)

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


# Said once per session, not once per band: the fact does not change while the session lives.
# "Once" is the session's obligation and not this script's: the hook keeps nothing between
# turns and re-prints the line on every turn the comparison holds, exactly as it re-prints a
# band. The look-back below is the whole of the mechanism -- and a compact is what removes the
# replies it looks back over, so a compacted session honestly has nothing to find and may say
# it again. Anybody who would rather not have the line at all sets CTXKIT_UPDATE_HINT=off.
UPDATE_ACTION = (
    "Say this once per session: look back over your own earlier replies in this session -- if "
    "you have already told the owner that this session predates the installed files, say "
    "nothing about it this turn. It is a fact to pass on, not something to act on: do not "
    "reinstall anything and do not close the session over it."
)


def update_wanted():
    """Whether the staleness line is wanted at all. Anything but an off word means yes.

    The two watermark lines need no such switch: they can be moved out of the way instead.
    This one has no line to move — it holds for the whole life of a session that opened before
    the last install — so without a switch a long session would carry it every turn to its end.
    """
    text = str(os.environ.get("CTXKIT_UPDATE_HINT", "")).strip().lower()
    return text not in ("off", "0", "no", "false")


def installed_root():
    """Which directory to look under for this machine's copy of ctx-kit. Always answers.

    Three places in one fixed order — `CLAUDE_PLUGIN_ROOT`, then `CLAUDE_CONFIG_DIR`, then
    `~/.claude` — the same order every other place in this kit resolves an install root.
    `CLAUDE_PLUGIN_ROOT` is set only by a plugin install, and where it is set it is the
    answer whether or not anything is found underneath it — falling back from it would mean
    reading one install's mtime against another install's files. `CLAUDE_CONFIG_DIR` is set
    by anybody who keeps their claude CLI configuration somewhere other than `~/.claude`,
    and it moves the manual install with it; reading `~/.claude` for one of them would be
    reading a directory that is not their install at all. Whether the directory it names
    holds anything is the next function's question, not this one's.
    """
    return (os.environ.get("CLAUDE_PLUGIN_ROOT")
            or os.environ.get("CLAUDE_CONFIG_DIR")
            or os.path.expanduser("~/.claude"))


def installed_at():
    """The newest mtime among the installed ctx-kit files, or None if there are none to stat."""
    root = installed_root()
    newest = None
    for parts in INSTALLED:
        for path in glob.glob(os.path.join(root, *parts)):
            try:
                stamp = os.path.getmtime(path)
            except OSError:
                continue
            if newest is None or stamp > newest:
                newest = stamp
    return newest


def started_at(path):
    """When this session began: the timestamp on the first record in the log that carries one.

    Read from the head, one window, because the first record is the first record. A log whose
    opening 64KB carries no timestamp this script can parse gets no reading — silence rather
    than a guess, the same posture as everywhere else here.
    """
    try:
        with open(path, "rb") as handle:
            head = handle.read(64 * 1024)
    except OSError:
        return None
    for piece in head.split(b"\n"):
        piece = piece.strip()
        if not piece.startswith(b"{"):
            continue
        try:
            stamp = json.loads(piece).get("timestamp")
            return datetime.datetime.fromisoformat(
                str(stamp).replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
    return None


def clock(stamp):
    """A moment, in the reader's own timezone: the log writes UTC, the owner does not live in it."""
    return datetime.datetime.fromtimestamp(stamp).strftime("%Y-%m-%d %H:%M")


def update_reading(path):
    """One line if this session opened before the installed files were last written, else None.

    Only the plain fact and its two moments. What it does not say is how far behind the session
    is or whether that matters: this script has no way of knowing which files changed, and an
    mtime moves for a re-copy as readily as for a fix.
    """
    installed = installed_at()
    started = started_at(path)
    if installed is None or started is None or installed <= started:
        return None
    return (
        "%s this session started %s, and the ctx-kit files it is running were last written %s"
        " -- whatever changed since reaches new sessions, not this one"
        % (UPDATE_PREFIX, clock(started), clock(installed))
    )


def make_up_reading(path):
    """One line saying by which route this context filled up, or None.

    The split is cache-audit.py's, loaded from beside this script, so the doorbell and the
    weekly checkup quote one function rather than two that drift. Anything missing — no
    cache-audit.py next door, an unreadable log, a log with nothing countable in it — returns
    None and the doorbell says nothing about the make-up.

    Cost: this parses the whole log, where the rest of this script reads only its tail. It is
    called only on a turn the bell already rings on, which is at most once per band per
    session, so a session under the line still pays for nothing but the tail read.
    """
    try:
        import importlib.util
        source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache-audit.py")
        spec = importlib.util.spec_from_file_location("ctxkit_cache_audit", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        made = module.make_up(path)
        whole = sum(made[k] for k in module.MAKEUP)
        if not whole:
            return None
        share = lambda key: 100.0 * made[key] / whole
        return (
            "%s what filled it, this log on its own: self %.0f%% (of the whole, %.0f%% is"
            " prompts written for a subagent), echo %.0f%%, reports %.0f%%, replies %.0f%%,"
            " other %.0f%%, out of %s characters -- the system prompt and the tool definitions"
            " are paid every turn and are outside this split"
            % (PREFIX, share("self"), share("dispatch"), share("echo"), share("reports"),
               share("replies"), share("other"), format(whole, ","))
        )
    except Exception:
        return None


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
    path = os.path.expanduser(path)

    readings, actions = [], []  # what the owner is shown, and what the session is to do

    tokens = last_watermark(path)
    if tokens is not None:
        yellow = parse_threshold(os.environ.get("CTXKIT_WATERMARK_YELLOW"), YELLOW_DEFAULT)
        red = parse_threshold(os.environ.get("CTXKIT_WATERMARK_RED"), RED_DEFAULT)
        band = line = None
        if tokens >= red:
            band, line = "red", red
        elif tokens >= yellow:
            band, line = "yellow", yellow
        if band:  # under the line: not one byte about the watermark
            readings.append(render(tokens, band, line))
            actions.append(action(band))
            # Rides along with the bell and never on its own: this is the same reading, said
            # in more detail, and it carries no instruction of its own.
            made = make_up_reading(path)
            if made:
                readings.append(made)

    update = update_reading(path) if update_wanted() else None
    if update:
        readings.append(update)
        actions.append(UPDATE_ACTION)

    if not readings:
        return

    reading = "\n".join(readings)
    # Two channels on purpose: `systemMessage` is the one the owner sees in the terminal (and
    # arrives as an informational message in stream-json), `additionalContext` is the one the
    # model reads. Neither one alone would reach both. The model gets the owner's text
    # verbatim, then what to do about it, so the two readers are never told different things.
    #
    # No trailing newline, and nothing may wrap or re-echo this: claude CLI treats stdout that
    # starts with `{` and ends with `}` as JSON, and stdout it fails to parse is dropped whole
    # with a hook error instead of reaching either reader.
    sys.stdout.write(json.dumps({
        "systemMessage": reading,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reading + "\n" + "\n".join(actions),
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
