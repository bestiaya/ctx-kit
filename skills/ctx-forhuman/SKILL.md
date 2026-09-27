---
name: ctx-forhuman
description: 负责人要"给人看的 / for human / 人读版 / 给我一个 html 看看 / 画一页给我看"的文档、页面或流程说明时用;把已有事实源投影成一份人一屏能读懂的件。聊天不用(聊天默认人话);给 agent 的文件不用。Use when the owner asks for a human-readable document/page ("for human", "给人看的", "人读版"); not for chat replies or agent-facing files. Also triggers on "give me an html to look at", "draw me a page", or /ctx-forhuman.
---

# For-human files

> **Speak in the user's language, and write the file in the user's language.** The owner's terms here are bilingual; write whichever form matches the file's language: `for-human` (给人看) / `called … in the case` (案里叫) / `plain-language glossary` (人话词表) / `候认` (nominated, pending the owner's confirmation) / `owner` (负责人); status words **machine-checked** (机器验过) / **awaiting the machine** (等机器) / **failed the machine check** (机器没过线) / **awaiting a person** (等人) / **checked by a person** (人验过) / **not generated** (未生成).

First ask who the reader is: the owner, a client's business people, or a client's engineers; with none named, it is the owner.

1. **No facts of its own**: project from the sources of fact that already exist (md, JSON, case files); mark the first line `> for-human · reader: X · fact source: path · generated: date` (in Chinese, `> 给人看 · 读者:X · 事实源:路径 · 生成:日期`); when a source changes, regenerate the file or mark it stale.
2. **One sentence on the first screen**: what it is, who it is for, how to use it; only then the body.
3. **Explaining a structure or a flow, lead with a top-level diagram**, no more than ten boxes; judgements go in sentences, comparisons in tables, structures in diagrams.
4. **One plain-language sentence per step or layer**: what goes in, what comes out, who checks it, and its status (machine-checked / awaiting the machine / failed the machine check / awaiting a person / checked by a person / not generated); IDs and coined words go in a "called … in the case" column or in brackets; the words come from the project's plain-language glossary, and one it lacks is nominated into it, marked `候认` (pending the owner's confirmation). The glossary is the project's `_ops/人话词表.md`, the path the rule block names; a project that keeps its case library elsewhere (the `ctx-kit case library:` line in its `CLAUDE.md`) keeps the glossary beside that library instead; it is created if it is not there.
5. **The five rules of the rule block 《给负责人的输出》 (output for the owner) apply as they stand** — it is the second rule block in this kit's `CLAUDE-snippet.md`; they are not copied here.
6. **The human-readable layer is one screen at most**; detail stays in the lower half of the same file or in the machine-readable source — give the way in, not the full text.
7. **Form follows the reader**: asked for html, make a single-file offline page (css / js inline, opens on a double-click); for reviewing a list, an md table is enough; a file going out to a client has our IDs taken out.

Three self-checks before handing it over: with the IDs covered it still reads; the first screen answers "what is it, and who is it for"; no whole section is just "none".

Example: an html overview of an asset hierarchy already has one sentence per layer and status colours, but lacks the first-screen sentence and the "called … in the case" column; add those two and it passes.
