# Provenance — every record string on screen 出处件

One row per **record** string. Nothing in that class is written by hand; each row
can be checked against the line it came from.

**★ marks what is new or changed since the third cut.** Sections 1 to 10 are
carried over unchanged — same strings, same Chinese, same line numbers. Sections
11 to 15 are new and cover everything the fourth cut adds.

**Time slice / 时间切面 — frozen, and the same for every row below:**

> **2026-09-06 21:00 (+0800)** — a snapshot of the board and the four live case
> files, copied out at that moment and never written to since. Every line number
> in this file addresses **that snapshot**, not the live library.

★ **What 21:00 is, precisely.** It is the **file-system moment the copy was
taken**: every file in the snapshot has a modification time at or before 21:00,
and the snapshot header records those times one by one. A few of the collected
rows carry a **hand-written clock label that is later** — `21:1x`, `21:2x`,
`21:4x`, `21:5x` — written into the text by the session that wrote the row.
Those are the writer's own clock running ahead of the machine's, not a later
collection moment. Nothing was collected after 21:00; the header is not adjusted
to match the labels, because the header is the reading the file system gives and
the labels are not.

★ **This block is now the only place the exact instant is written down.** The
third cut printed it on screen; the fourth cut does not, and the resident line
under the rail points here instead: `as of one frozen snapshot · timestamp in the
repo`. **This file must therefore be published alongside the film.** If it is
not, the film shows a claim about a snapshot whose timestamp nobody can reach.

Why a snapshot and not the library: the library is written by live sessions and
moves several times an hour. The previous round measured the drift — over two and
a half hours a new row was inserted **at the top** of one inbox, so both "line N"
and "the Nth row" stopped being stable handles. Freezing the files removes the
problem entirely: the numbers below are correct forever, because the thing they
address no longer changes.

**How to re-check a row.** Open the named file in the frozen snapshot at the
stated line and compare it against the Chinese cell. Every English string is a
translation of that cell and adds nothing to it. A checker in this directory does
the mechanical half: it asserts that each Chinese cell below appears **literally**
in the line it claims, and it reproduces every counted and derived string from
scratch.

**Naming.** Files are named by function — board, content-ops case file, feature
case file, knowledge-base case file, video case file — never by case number or
file name, because this file is meant to be publishable alongside the film and
holds itself to the same leak classes as the screen does.

**Quotation.** The Chinese cells here are quoted **verbatim, with no substitution
at all**. Fragments were chosen so that no case number, experiment id, session
id, commit hash, path or version number falls inside a quotation. Where a source
line does carry those tokens, they sit outside the quoted fragment. `S-1` / `S-2`
in one cell are the two films' own labels, not case numbers. ★ The same rule now
covers the board's internal milestone tokens: the milestone headings are quoted
from the word after the token onwards.

---

## 1. The four plates — names (4 strings)

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `Content ops` | 首推与自运营〔短名：运营〕 | board, case table, content-ops row — **line 37** | 2026-09-06 21:00 (+0800) | Public name fixed by the owner; it is the English of the board's own short name. Case number and pen-holder cell not quoted. ★ The case number is replaced on screen by the chip number `01`; see §11. |
| `Feature development` | 功能设计与优化（首发后往哪改）〔短名：功能优化〕 | board, case table, feature row — **line 38** | same | as above; ★ chip number `02` |
| `Knowledge base` | 知识库与内容线〔短名：知识库〕 | board, case table, knowledge-base row — **line 40** | same | as above; ★ chip number `03` |
| `Video` | 外部视角与视频推广〔短名：视频〕 | board, case table, video row — **line 39** | same | as above; ★ chip number `04` |

## 2. The four plates — what each line is doing (4 strings)

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `Nothing shipped. Public repo 19 commits behind.` | 本任零出门动作，公开仓仍落后主干 19 笔 | board, content-ops row — **line 37**; the same figure is written independently in the feature case file, plan snapshot — **line 15** (主干领先 origin 19 笔) | 2026-09-06 21:00 (+0800) | Version number, commit hashes and the three items awaiting review are outside the quoted fragment and are not on screen. No person is named or implied. |
| `Fourteen changes merged. Picking the next batch.` | 两批十四件已成，合入本地 main ／ 下一批从总账"进以后"32 条挑 5~8 条 | board, feature row — **line 38** (both fragments, same line) | same | Commit hashes, branch name, case number and an internal triage file name are outside the quoted fragments. |
| `Ten entries filed. All ten past the leak check.` | 首批 10 条已进库并全过泄漏闸 | knowledge-base case file, plan snapshot — **line 8** | same | Repository name and commit hash follow the quoted fragment and are not on screen. |
| `Two films at release quality. The second one is being remade.` | 两支片推到可发状态，但整包未交付 ／ S-2 正按 09-06 新论点重做 | board, video row — **line 39** (first fragment); video case file, plan snapshot — **line 19** (second fragment) | same | `S-2` is the second film's label; it is not on screen. Film paths, working-directory names and the owner's instruction are outside the quoted fragments. |

## 3. The time slice's own timestamp — ★ retired from the screen, retained here

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| ★ **not on screen this cut** — was `as of 2026-09-06 21:00 (+0800)` | TAKEN_AT: 2026-09-06 21:00 (+0800) | snapshot header file — **line 1** | 2026-09-06 21:00 (+0800) | None needed. The git head and the pen-holder readings on the following lines of that file are not on screen. |

★ The row is kept, word for word, for two reasons. It is the anchor of every
other row in this file, and it is the thing the on-screen line
`as of one frozen snapshot · timestamp in the repo` points at. The string left
the picture; the fact did not leave the record.

## 4. The counted strings (3 strings) ★ one added

These are **counts, not translations**. Each rule is written so anyone can redo
it; the checker in this directory redoes all three and fails if any number moves.

| On-screen (EN) | What was counted | Source lines | Time slice | De-identification |
|---|---|---|---|---|
| ★ `Board · six cases · five milestones` | **Six** = rows in the board's case table. **Five** = rows in the board's milestone table. Both are plain row counts of a markdown table between its header rule and the blank line that ends it. | board, milestone table — **lines 17 to 21**; board, case table — **lines 35 to 40** | 2026-09-06 21:00 (+0800) | The milestone headings carry the board's internal milestone tokens and the case rows carry case numbers, pen-holder session titles and session ids. **Only the two row counts go on screen.** The word `Board` is our label for the thing being counted, not a translation of the file's own title. |
| `Six cases on the board. Four have a pen-holder.` | **Six** = rows in the board's case table. **Four** = of those rows, the ones whose status cell reads 讨论中 *and* whose pen-holder cell names a session. The other two read 候接手 and their pen-holder cell reads 待继任填 — successor to fill in. | board, case table — **lines 35 to 40** | same | The four pen-holder cells contain session titles and session ids. **Only the fact that they are non-empty goes on screen; no name, no id, and none is quoted here.** |
| ★ `Fourteen messages between these four lines today.` | **The rule, stated so it can be re-run: count rows.** Every row in the Inbox section of the four case files whose date cell **begins with** the slice's date. Some cells carry a clock time after the date, so the date is matched at the *start* of the cell, not against the whole cell. One row = one delivery logged by the receiving case. A reply is its own row. **The same message delivered twice is two rows, because the record writes it as two rows** — one such pair sits in the video case file, and the second row's own disposition cell says as much. Nothing is merged on a judgement about whether two rows "mean the same thing"; a rule that needed that judgement could not be re-run by anyone else. Count: content-ops **8**, feature **2**, video **2**, knowledge-base **2** = **14**. Every one of the 14 was sent by one of these same four lines, which is why the string says "between these four lines". | content-ops case file **lines 143–150**; feature case file **lines 141–142**; video case file **lines 145–146**; knowledge-base case file **lines 85–86** | same | Sender cells carry case numbers and session ids; only the count goes on screen and none is quoted here. Two further cases exist on the board and are **not** in the snapshot, so they are outside the claim — hence "these four lines" rather than "the project". ★ **Why this reads 14 where the third cut printed 13:** the third cut's checker tested the whole date cell against the bare date and so dropped, in silence, the one row whose cell also carries a clock time. That row is in the snapshot, it is dated to the slice, and it is one of these four lines' own inbox rows. It belongs in the count. |

★ **What `today` means, now that the date is off the screen.** `today` in the
third string is bound to the slice, not to the day a viewer watches the film: it
is "the calendar day the snapshot was taken", i.e. the date in the block at the
top of this file, and the counting rule above is a filter on exactly that date
string, matched at the start of each row's date cell. Nothing on screen dates it any more, which is why this note exists and
why the resident line under the rail sends the viewer here. The same binding
applies to `tonight` in the rewritten verdict (§9).

## 5. The round trip — the verdict that was written (2 strings)

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `Verdict: none of the six got bigger.` | 当时那六案无一变大 | feature case file, experiment ledger, verdict cell — **line 59** | 2026-09-06 21:00 (+0800) | The ledger row's experiment id, its result-file path and the six raw figures are outside the quoted fragment and are not on screen. |
| `Do not say "none got bigger".` | 不许说"无一变大" | feature case file, plan snapshot, item 1 — **line 17** | same | The clause carrying the aggregate figures, the percentage and the affected case's number sits before the quoted fragment and is not on screen. |

## 6. The round trip — the other line checks (3 strings)

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `A relayed number doesn't get printed until I've re-run it myself.` | 转述来的读数一律自己复现再印 | content-ops case file, plan snapshot — **line 12** | 2026-09-06 21:00 (+0800) | None inside the fragment. The neighbouring clause names the other line by function only. |
| `Caught a line that would have gone out wrong.` | 抓到一句会印错的话 | content-ops case file, chronicle, 17:3x entry — **line 72** | same | The version number of the release note it was headed for sits earlier in the line and is not on screen. |
| `"None got bigger" is false. One case went 11,242 → 11,244 — two characters bigger.` | 对方"无一变大"为假 ／ 11,242 → 11,244，多 2 字符 | content-ops case file, chronicle — **line 72** (both fragments, same line) | same | The affected case's number sits between the two fragments and is replaced on screen by "one case". Both figures are character counts, same unit, quoted as written; no ratio is derived from them. |

## 7. The round trip — the root cause (1 string)

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `Root cause, found line by line: the new build adds an ellipsis, +1 character per truncated cell.` | 逐行比对定位根因 = 新版给截断格补省略号、每格 +1 | content-ops case file, chronicle — **line 72** | 2026-09-06 21:00 (+0800) | None inside the fragment. "the new build" renders 新版, which in the record is a branch of the loader; the branch name is not on screen. |

## 8. The round trip — the message that crossed (2 strings)

Both are cells of the **feature line's own inbox row**, i.e. the receiving end's
record of what arrived. ★ Its "from" cell is now on screen too; see §12.

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `Two read-only findings: your verdict "none got bigger" has a counter-example. One case is 2 characters bigger — the ellipsis this batch added, +1 per truncated cell.` | 两条只读发现 ／ 判定里"无一变大"有反例 ／ 多 2 字符，根因是本批新加的省略号（每截断格 +1） | feature case file, Inbox, row dated 2026-09-06, incoming cell — **line 141** (all three fragments, same line) | 2026-09-06 21:00 (+0800) | The experiment id and the affected case's number sit between the fragments and are dropped; "your verdict" and "one case" stand in their place. The second of the two findings, which names an internal file and line, is not on screen. The sender's session title and id are in the row's "from" cell — ★ that cell is now rendered as an address, with the id dropped; see §12. |
| `They said outright: no chasing, no follow-up. The call is ours.` | 对方明言不催不跟进，处置归本案 | feature case file, Inbox, same row, incoming cell — **line 141** | same | None inside the fragment. Rendered from the receiving line's own point of view, which is how the record writes it. |

## 9. The round trip — the re-measure and the rewrite (2 strings)

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `Re-measured. Same six cases, the loader before and after. Every row and the total match theirs exactly.` | 用 origin/main 版与工作树版装载器同批重跑六案，六行与合计与对方完全一致 | feature case file, Inbox, same row, disposition cell — **line 141** | 2026-09-06 21:00 (+0800) | The branch name and the working-tree wording are rendered as "before and after"; the six raw figures that follow are not on screen. |
| `"None got bigger", as a general claim, was disproved tonight. Re-measured here.` | "无一变大"作为通则于 09-06 晚被证否，本案已复量 | feature case file, experiment ledger, same row as §5 — **line 59** | same | The experiment id is dropped. This fragment sits immediately after the original verdict inside the same cell, which is what makes the rewrite visible in the record rather than only asserted. ★ `tonight` renders 09-06 晚 and is bound to the slice, like `today`; see §4. |

## 10. The round trip — the receipt back (2 strings)

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `Independently re-measured your six rows — every row and the total match.` | 独立复量本案那六行对跑读数，逐行与合计全部吻合 | content-ops case file, Inbox, row dated 2026-09-06 carrying the receipt, incoming cell — **line 149** | 2026-09-06 21:00 (+0800) | The six raw pairs, the total and the percentage follow the fragment and are not on screen. The sender's session title and id are in the "from" cell — ★ that cell is now rendered as an address, with the id dropped; see §12. |
| `arrived after close-out` | 收口后到件 | content-ops case file, Inbox, same row, "from" cell — **line 149** | same | The rest of that cell is the sender's case number, session title and session id; only the three-character state marker is quoted and put on screen. `close-out` is the product's own published English for 收口. ★ In this cut the same four words are the tail of the address line in §12 rather than a standalone tag; the source and the wording are unchanged. |

---

# ★ New this cut

## 11. The numbering map — `01` to `06`

The two digits on every chip and every rail plate are **ours**. They are a
de-identification device: they let one record be pointed at from another (an
inbox row can say who it came from) without the internal case number ever
reaching the screen. The map is fixed for the whole film and is published here so
that anyone holding the snapshot can resolve it.

| On screen | Which row of the board's case table | Named on screen? | Why |
|---|---|---|---|
| `01` | the content-ops row — **line 37** | yes, `Content ops` | one of the two lines the film is about |
| `02` | the feature row — **line 38** | yes, `Feature development` | the other one |
| `03` | the knowledge-base row — **line 40** | yes, `Knowledge base` | its case file is in the snapshot, so its plate can say what it is doing |
| `04` | the video row — **line 39** | yes, `Video` | same |
| `05` | the first row of the case table — **line 35** | **no** | its case file is not in the snapshot; only the board row is, so the chip is drawn and numbered and says nothing |
| `06` | the second row of the case table — **line 36** | **no** | same |

Order: `01` to `04` follow the order the four plates already had on the rail in
the third cut, which is the order the film needs, not the order the board's table
happens to use. `05` and `06` were then given to the two remaining rows in table
order. Nothing about the numbering is a claim; it is a legend.

**What the numbers replace.** Six case numbers, on the board and in the "from"
cell of every inbox row. The checker's leak gate now fails if any of those
internal spellings reaches an on-screen string.

## 12. The two address headers (2 strings)

Each is the **"from" cell of a real inbox row**, written by the receiving case,
de-identified by three fixed substitutions: the case number becomes the chip
number from §11; the session id (`@` and eight hex characters) is dropped; the
session title is reduced to the sequence number it begins with.

| On-screen (EN) | Source text (ZH, verbatim) | Source line | Time slice | De-identification |
|---|---|---|---|---|
| `from: Content ops (01) · session 16` | 运营线（16- | feature case file, Inbox, row dated 2026-09-06, **"from" cell** — **line 141** | 2026-09-06 21:00 (+0800) | The case number precedes the fragment and becomes `(01)`; the fragment stops immediately before the case number embedded in the session title; the session id that closes the cell is dropped. 运营线 is the board's own short name for that line and is rendered `Content ops`, exactly as on its plate. **What is kept: the fact that it came from line 01, and the session's sequence number.** |
| `from: Feature development (02) · session 19 · arrived after close-out` | （19- ／ 功能优化 ／ 收口后到件 | content-ops case file, Inbox, row dated 2026-09-06 carrying the receipt, **"from" cell** — **line 149** (all three fragments, same line) | same | Same three substitutions. 功能优化 is the board's own short name for that line and is rendered `Feature development`, exactly as on its plate. 收口后到件 is the state marker already used in the third cut; it is now the tail of this line instead of a separate tag. The case number and the session id are dropped. |

**Why this is not a fiction.** An earlier suggestion was to put an invented
address on screen so that nothing real would be shown. That was rejected: this
film's only rule is that its words are true, and an invented address is the one
kind of string that can never be checked against anything. De-identifying a real
cell keeps it checkable — both rows above resolve to a line in the snapshot, and
the checker asserts it on every run.

## 13. `pen-holder at arrival: none` (1 string, derived)

Not a translation. It is read off three rows of the **content-ops line's own
chronicle**, in the frozen snapshot, in this order:

| # | What the row records | Source line | Chinese fragment quoted |
|---|---|---|---|
| i | the pen-holder session takes its closing measurement at 18:1x | content-ops case file, chronicle — **line 67** | 2026-09-06 18:1x **收口最后量 |
| ii | the receipt arrives at 18:2x and is logged as having arrived after close-out | content-ops case file, chronicle — **line 66** | 2026-09-06 18:2x 收口后到件 |
| iii | the next pen-holder signs on at 21:0x | content-ops case file, chronicle — **line 65** | 2026-09-06 21:0x **接手 |
| iv | *(corroborating, added this cut)* the close-out itself at 18:0x, where the outgoing session is recorded as retired | content-ops case file, chronicle — **line 69** | 2026-09-06 18:0x **收口（ |

**The derivation.** Close-out at 18:0x–18:1x; arrival at 18:2x; the next
pen-holder at 21:0x. The receipt landed inside a gap of roughly three hours in
which the case had no pen-holder. That, and only that, is what the string says.

**Time slice:** 2026-09-06 21:00 (+0800) — the snapshot was taken after all four
rows were written, so all four are inside it.

**De-identification.** Rows i to iv all carry session titles and session ids in
the parts of the line that are **not** quoted; each fragment stops before them.
No time of day reaches the screen either — the record's own `18:1x` style already
blurs the minutes, and even so the film prints none of it.

**The nuance this string must not be read as hiding.** The retiring session did
come back and write a disposition into that inbox row after close-out; the row is
handled, and the film does not draw it as unhandled. "No pen-holder" is a
statement about the case's pen at the moment of arrival — which is what rows i to
iii fix — not a claim that nobody ever dealt with it.

## 14. The milestone labels (5 strings, editorial)

Ours, not translations: each is a short English rendering of **the milestone's
own name**, which the board writes in its **number column**, immediately after
the internal milestone token — the token dropped, the ordinal kept.

★ **Which column, exactly** (corrected 09-07). The board's milestone table has
four columns: number, "what is true once this is taken", status, and who is
pushing it. What these five labels render is the **name in the number column**.
The column headed "what is true once this is taken" holds the row's acceptance
sentence; it is **not** rendered and **not** on screen, and no earlier wording in
this file should be read as saying otherwise.

They are listed here with the Chinese they render and the line they render it
from, so the rendering can be judged even though it is not a record string.

| On screen | Chinese rendered (ZH, verbatim — the name in the number column, token not quoted) | Source line | Time slice |
|---|---|---|---|
| `Milestone 1 · the tool exists` | 工具就绪 | board, milestone table — **line 17** | 2026-09-06 21:00 (+0800) |
| `Milestone 2 · polished and published` | 打磨发布 | board, milestone table — **line 18** | same |
| `Milestone 3 · real users` | 有人真用得上 | board, milestone table — **line 19** | same |
| `Milestone 4 · portable` | 可移植 | board, milestone table — **line 20** | same |
| `Milestone 5 · knowledge base live` | 知识库上线 | board, milestone table — **line 21** | same |

**De-identification.** Each row's internal token sits immediately before the
quoted fragment and is not quoted, not rendered and not on screen. The rest of
each row — the acceptance sentence, the status, and the case numbers in the
"who is pushing it" column — is not on screen either. The ordinal (`1` to `5`) is
the row's position in the table and carries nothing private.

**Deliberately not rendered: the status column.** Each milestone row records
whether it is met, in flight or on hold. Putting three of those on screen would
be three more claims for a shot that exists to show shape, so the bands are drawn
with a uniform marker that encodes nothing.

## 15. The drawn relation — which case hangs under which milestone

The establishing shot draws each case chip **inside the band of the milestone it
is filed under**. That placement is **not decoration**: it reproduces the
milestone column of the board's case table, one row per case.

| Source | What is read | Time slice |
|---|---|---|
| board, case table, third column of **lines 35 to 40** | for each of the six case rows, the set of milestone rows it is filed under | 2026-09-06 21:00 (+0800) |

The cells themselves are **not quoted here and not on screen**, because they are
written with the board's internal milestone tokens. The checker parses the column
instead and asserts that the set of placements the storyboard draws — eight of
them, over six chips and five bands — is exactly the set the board's own column
gives. If a placement is added, removed or moved, the run fails.

Two consequences worth stating, since a viewer can see both:

- ★ **Two chips appear in two bands each** (corrected 09-07). **Two cases — the
  ones this film numbers `02` and `05` — are each filed under two milestones**,
  so two chips are drawn twice, each with the same number both times: `02` in
  bands 2 and 3, `05` in bands 1 and 2. Six chips and eight placements is the
  arithmetic of exactly that: 6 + 2 = 8. The number is what makes each repeat
  legible rather than confusing, which is most of the argument for numbering the
  chips at all.
- **Eight placements, six chips.** The line at the top of the shot counts cases
  and milestones, not placements, and both of its numbers can be counted off the
  picture: six distinct chip numbers, five bands.

---

## 16. Strings on screen that are **not** record strings

Listed here so the file is exhaustive, not because they have sources in the
snapshot. They are argued in `material.md` §d, one shot named per row.

| String | Class | Where it comes from |
|---|---|---|
| the four cards (opening / mechanism / closing / sign-off) | editorial | written by the owner, used verbatim. ★ One word of the opening card changed this cut, by the owner's ruling |
| `Messages translated from the original Chinese · originals in the repo` — **not in the published film; removed 2026-09-07** | editorial | It was lifted verbatim from the subtitle script and stood in the fourth cut. The owner had it taken out of the picture, and the cut published is the one without it. Two consequences worth stating plainly: the film no longer says in frame that the messages are translated — **the post carrying the film says so in its caption instead, and the Chinese originals are in this file, one to a row**; and the film's other resident line, `as of one frozen snapshot · timestamp in the repo`, is untouched, so this file is still what the picture points at. Nothing else in the film changed: measured on the delivered cuts, the only pixels that differ are the strip this line occupied. |
| `Inbox`, `Experiment ledger` | editorial | the product's published English section names |
| `ctx-kit`, `~/demo` | editorial | the product's own name; a fictional placeholder path |
| ★ the five `Milestone n · …` labels | editorial | ours; the rendering and its source are in §14 |
| ★ `01` to `06` | editorial | ours; the map is in §11 |
| ★ `as of one frozen snapshot · timestamp in the repo` | editorial | ours; it points at the time-slice block at the top of this file, which is why this file has to travel with the film |
| the two install commands, `+ one paste (see README)` | editorial | the **public** repository's README, which is where the film sends the viewer — not the snapshot |
| the repository URL on the end card | editorial | the repository's own address; it is not quoted from anything. **Corrected 2026-09-07**: this row previously sourced the URL to the README along with the install commands. It is not there — the README's only ctx-kit link is the issues page. The install commands and the paste do come from the README; the address does not, and saying so was wrong. Left visible rather than quietly rewritten, on the same rule as the two retracted readings above. |

## 17. Two honest limits

1. The snapshot proves **who holds the pen on each case at the slice**. It does
   not record which sessions were live at that instant, and nothing on screen
   says four sessions were running at once. The count line says what the snapshot
   can carry and stops there.
2. ★ With the timestamp off the screen, **the film no longer dates itself in
   frame**. Two on-screen strings are time-relative — `today` in the count line
   and `tonight` in the rewritten verdict — and one plate line
   (`Public repo 19 commits behind.`) stopped being true within an hour of the
   slice being taken. All three are bounded by the time-slice block at the top of
   this file and by nothing else. That is a real reduction in what the picture
   alone can prove, taken deliberately, and it is the reason `report.md` §4 makes
   publishing this file a condition of delivery rather than a nicety.
