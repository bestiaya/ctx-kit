#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""takeover-load.py — load one case file the way a takeover reads it (ships with ctx-kit).

What it prints: the header line + all of A~D + from E the table header, every row whose
status is running / awaiting acceptance / queued / to dispatch, and the verdict of the most
recent delivered row + from the inbox (§I) every undisposed row in full plus the last three
disposed ones, each cut to 240 characters; F / G / H come through as their section name and
a line count only. The last line reports the characters loaded, which is the entry-tax base
`ctx-takeover` §2 reads in three bands (<=10,000 green / <=15,000 yellow / above that the
case is slimmed before it changes hands).

Usage:
    python3 takeover-load.py <case file path>

Run it with a real python3: an error mentioning `xcodebuild` or similar means the interpreter
resolved somewhere else (the macOS Xcode shim, for instance) — run it again with a real
python3; the script is not broken.

This file runs at import rather than under an `if __name__ == "__main__"` guard, and that is
deliberate: `scripts/case-lint.py` check 1 reads this file and runs it as it stands, exactly
as it used to run the fenced block this code was lifted out of, so the rule stays written in
one place and the lint reading cannot drift from what a takeover actually loads.

Why it is written the way it is — the notes that used to sit as comments inside the block:

* Columns are located by their header text, never by number (`q`): the column order differs
  from case to case, so a hard-coded column number must be wrong somewhere.
* `W` splits a markdown row on unescaped pipes only: a `\\|` inside a cell is content, not a
  separator (ctx-handoff §4 step 2). The same split is written three more times and the four
  must agree — the length block in ctx-handoff §3, the same block over the whole library in
  ctx-checkup §4, and split_cells in scripts/case-lint.py.
* `M` puts an ellipsis at the cut, or "brief: to be written" comes out as "brief:" and reads
  as the opposite of what it says.
* The status match takes the six status words and nothing else (ctx-kickoff §2), anchored at
  the cell start on both sides. Unanchored, 不在跑 / 未在跑 / "not running" all read as still
  running; 达成 used to be matched too, and it matches 未达成 as happily as 部分达成, so a row
  that failed read as delivered. Same reason on the English side: loose, `done` matches "not
  done" and `delivered` matches "not delivered". Leading punctuation or `**` is allowed, as
  in the inbox rule below.
* The newest delivered row is picked by ID (`E-10b-2` sorts before `E-11`), never by table
  order, so newest-first and oldest-first tables both work.
* A status outside the six words is read as neither live nor finished, so the note says how
  many rows went unread rather than letting them vanish.
* Inbox, disposed = the disposition cell opens with one of the three disposal markers
  (leading punctuation or bold marks allowed); blank, or worded any other way, is still on
  somebody's plate and comes through in full. The rule no longer guesses at what the writer
  meant: the old fallback took "no waiting word in the cell" for settled, and the ways to
  word a cell are endless — "shown to the owner, not sent" holds no waiting word, and that
  live row went missing without a sound. Three agreed openings state the rule in one sentence
  and are what the docs teach anyway.
* A row whose cell count differs from the header row's has a bare `|` somewhere in its own
  text: every column past that point is out of step, so the cell sitting at the disposition
  position is a fragment of somebody's sentence and nothing in that row can be trusted by
  position. Measured on one 8-column row carrying one `\\|`: the old split cut at every `|` it
  saw and made 9 cells of it, against the 8 case-lint counted, which is how a correctly
  written row came to be read as malformed. Do not guess which fragment was meant — take the
  row as undisposed, load it whole, and count it in the note (measured: two live rows whose
  disposition column came out as "#" while the real cell said "for my successor to deal
  with"). Dropping a live obligation costs far more than carrying one settled row.
* The 240-character cap is on the whole rendered row, not per cell: a settled row is a
  reminder, and 200 a cell over 6 cells is 1,200 characters of it.
* The inbox is read newest-last, because it is append-only.
"""
import sys,re
L=open(sys.argv[1],encoding='utf-8').read().split('\n')
P=[i for i,l in enumerate(L) if re.match(r'^##\s+[A-Z]\.?(\s|$)',l)]+[len(L)]
S={L[i].split()[1].rstrip('.'):(i,P[n+1]) for n,i in enumerate(P[:-1])}
W=re.compile(r'(?<!\\)\|')
def z(r):  # the cells of one markdown row
    p=[c.strip() for c in W.split(r.strip())]
    if p and not p[0]: p=p[1:]
    if p and not p[-1]: p=p[:-1]
    return p
q=lambda w:next((i for i,x in enumerate(h) if re.search(w,x,re.I)),-1)
g=lambda r,i:(z(r)+['']*9)[i]; M=lambda s,n=200:s[:n]+('…' if len(s)>n else '')
T=lambda r:'|'+'|'.join(M(c) for c in z(r))+'|'
o=L[:P[0]]
for k in 'ABCD':
    if k in S: o+=L[S[k][0]:S[k][1]]
if 'E' in S:
    a,b=S['E']; R=[l for l in L[a:b] if l.lstrip().startswith('|')]; D=R[2:]
    h=z(R[0]) if R else []
    j,v=q('状态|status'),q('判定|verdict')
    m=lambda p:[r for r in D if re.search(p,g(r,j),re.I)]
    A=m(r'^\W*(在跑|待验收|排队|待派|running|awaiting acceptance|queued|to dispatch)')
    F=m(r'^\W*(已交货|已完|delivered|done)')
    o+=[L[a],'']+R[:2]+[T(r) for r in A]
    if F:
        y=lambda r:[(1,int(t)) if t.isdigit() else (0,t) for t in re.findall(r'\d+|[a-z]+',g(r,1 if j==0 else 0))]
        N=max(F,key=y) if any(y(r) for r in F) else F[-1]
        o+=[f'latest delivered {M(g(N,1 if j==0 else 0),80)} | verdict {M(g(N,v) if v>=0 else "see that row in the case")}']
    if not A+F: o+=D[-3:]+['<!-- status column did not match (column missing, or wording outside the vocabulary); last 3 rows kept, scan E by hand -->']
    O=[r for r in D if r not in A+F]
    e=f'. Status outside the six words on {len(O)} row{"s" if len(O)>1 else ""}, read as neither live nor finished - scan those by hand' if O and A+F else ''
    o+=[f'<!-- E {len(D)} rows: all {len(A)} active rows + 1 latest verdict; the rest, and anything past 200 chars, stay in the case - fetch on target{e} -->']
for k in 'FGH':
    if k in S: o+=['',f'{L[S[k][0]]}  <- not loaded ({S[k][1]-S[k][0]-1} lines), fetch on target']
if 'I' in S:
    a,b=S['I']; K=[i for i in range(a,b) if L[i].lstrip().startswith('|')]
    h=z(L[K[0]]) if K else []; d=q('处置|disposition') if K else -1
    if d<0: o+=['']+L[a:b]+(['<!-- inbox: no disposition column in the header row; whole inbox loaded, sort it out by hand -->'] if K else [])
    else:
        n=re.compile(r'^\W*(已办|不办|已转|done|dropped|moved)',re.I)
        x=lambda r:len(z(r))!=len(h)
        u=lambda r:x(r) or not n.match(g(r,d))
        D=K[2:]; U=[i for i in D if u(L[i])]; V=[i for i in D if not u(L[i])]; C=V[-3:]; X=[i for i in D if x(L[i])]
        o+=['']+[M(T(L[i]),240) if i in C else L[i] for i in range(a,b) if i not in D or i in U or i in C]
        if X or len(V)>len(C) or any(len(T(L[i]))>240 for i in C):
            w=f', the other {len(V)-len(C)} left in the case' if len(V)>len(C) else ''
            s=f' + the last {len(C)} of {len(V)} disposed, each cut to 240 chars{w}' if V else ''
            y=f' Cell count off the header on {len(X)} of them (a bare | inside a cell — \\| is content and does not split): loaded whole as undisposed, go and check those against the case.' if X else ''
            o+=[f'<!-- inbox {len(D)} rows: all {len(U)} undisposed in full{s} - fetch on target. Undisposed = a blank disposition cell, or one not opening with done / dropped / moved to.{y} -->']
t='\n'.join(o);print(t);print(f'\n=== characters loaded this time: {len(t)} ===')
