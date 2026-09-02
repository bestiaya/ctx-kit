---
name: ctx-checkup
description: 会话缓存周检与案文件回填。用户说"周检""查一下会话花费""哪些会话该收口了""跑一下缓存审计""这周 token 都花哪了"，或显式 /ctx-checkup 时用。跑 cache-audit 判读越线会话，并回填案 G 节的待填档案路径。 Weekly cache audit — use on "weekly checkup", "where did the tokens go", "audit session costs", or /ctx-checkup; runs cache-audit, flags sessions over the pre-registered lines, backfills archive pointers in case files.
---

# 周检：查账 → 判读 → 回填

**开跑前两件，缺一必错**（都实测栽过）：①`date` 查真实时钟——**不许从文件时间戳或账单推日期**，推错会把整批记录盖上错日期；②重新拉一次活会话清单——**会话死活以案/线件头行为准**，登记簿是投影、可能已过期，据它判会把已退役的当活的。

## 1. 跑账

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cache-audit.py" --all
```

脚本纯标准库、零依赖。报 `xcodebuild` 之类的错是解释器被解析到了别处（如 macOS 的 Xcode 垫片）——换一个真实的 python3 再跑，不是脚本坏。非 plugin 方式安装时，把路径换成脚本实际所在位置。
脚本从 cwd 推导项目档案目录；目录对不上就加 `--project <目录>`。

## 2. 判读（预注册判据，判负照报）

| 会话类型 | 判据 | 越线的含义 |
|---|---|---|
| 讨论 / 导师 | 重写占比 **<10%** 且 p50 水位 **<150k** | 钱漏在反复重读上 |
| 执行 | compact 次数 **= 0** 且 峰值水位 **<200k** | 该落盘的没落盘 |

脚本会给越线行打 ⚠️，但**别只转述表格**，逐条给动作：
- 重写占比高 + 水位肥 → **"该 ctx-handoff 了"**；顺手估买断价 `水位×(2+0.1×(N−1))+输出×5`，与"再冷回访一次要付 水位×2"对照，用户一眼就能拍。
- 执行会话 compact >0 → 指出它当时该落盘换生，不是压缩。
- 已收口的老会话本期**新增请求 = 0** → 退役终验通过；>0 就点名"退役未落实"。

## 3. 回填案 G 节
扫案目录（优先 `_ops/CASES/`，否则 `cases/`）里 G 节写着 `(待回填)` 的案，逐个配对：
1. 从案文件的"更新"日期与文件 mtime 取收口时点；
2. 在项目档案目录里找该时点前后有**收口轮账单特征**的会话——单次 `cache_creation` ≈ 该会话水位、且此后再无请求；
3. 配上了就把 jsonl 路径填进 G 节，标"仅备查勿整读"。

两条纪律：
- **jsonl 时间戳是 UTC**，与本地时钟比对前先按本地时区换算（差一个时区就会配错会话）。
- **配不上就留着 `(待回填)` 并说明**。宁可空着，也不许填一个"看起来像"的路径——`ls -t` 自指实测会指到两周前的旧文件。

## 4. 案尺寸检查
口径 = **接手时的实际加载量**（头行 + A~D + E 的活跃行与最新判定 + I），不是"文件多大"，也不是旧口径的"量到 E 为止"。逐案跑 `ctx-takeover` 第 2 节那段提取命令（`F=` 换成各案路径）、`| tail -1` 只取末行那个字符数——**别把提取出来的正文读进上下文**，周检只要数；决策附录 / 实验档案 / TASKBOARD 跳过。

判据（2026-08-24 负责人放宽，原 7,000）：每案 **≤10,000 为绿**，**>15,000 必瘦**。超线逐案报数并点名持笔会话瘦身：C 表旧行上交线级决策档案 / E 的已交货老行滚动归档（见 `ctx-handoff`）/ D 清已了项 / F 编年压缩；历史细节留转录与档案，不留案。

**E 行长度检查（只报不改）**：判定与"对方案的影响"两格各 ≤200 字。全案库跑一遍，超长行按字数倒序列出（案文件 / 行号 / 哪一格 / 字数），报给该案持笔会话自己瘦——**周检不改别人的案**：

```bash
D=_ops/CASES; [ -d "$D" ] || D=cases; python3 - "$D"/*.md <<'PY'
import sys,re
w=[]
for p in sys.argv[1:]:
    L=open(p,encoding='utf-8').read().split('\n')
    P=[i for i,l in enumerate(L) if re.match(r'^##\s+[A-Z]\b',l)]+[len(L)]
    for n,i in enumerate(P[:-1]):
        if L[i].split()[1]!='E': continue
        R=[(k+1,l) for k,l in enumerate(L[i:P[n+1]],i) if l.lstrip().startswith('|')]
        h=[c.strip() for c in R[0][1].strip().strip('|').split('|')] if R else []
        C=[x for x,c in enumerate(h) if '判定' in c or '影响' in c]
        for ln,l in R[2:]:
            c=[x.strip() for x in l.strip().strip('|').split('|')]
            w+=[(len(c[x]),f'{p}:{ln} 「{h[x]}」{len(c[x])} 字') for x in C if x<len(c) and len(c[x])>200]
for n,s in sorted(w,reverse=True): print(s)
print(f'--- 超 200 字的格 {len(w)} 处（只报不改，请写的人自己瘦）---')
PY
```

**拆案提示（只提示、不判负）**：某案 E 行 >30，或近 30 天新增的 C 决议行 >50，就提一句"考虑拆案"。**这两个阈值是经验值、尚未验证**，只当讨论引子，不作判据、不进达成/判负。

## 5. 退役标记补扫
收口时自打标的会话前缀是 `✕`。**崩掉或被弃置的会话不会自己打标**，本步补：
- 列出**既不是任何线的线主、也不是任何案的持笔、也不是任何散活的载体**，且 >1 天没动过、标题又没有 `✕` 前缀的会话；
- 逐个 `set_session_title` 改成 `✕ <原标题>`。**存疑的不动**——宁可漏标，不许把活会话标死。标题工具不可用（纯终端）则本步跳过，并在回复里说明。
- 报数：本期补标 N 个、存疑跳过 M 个（点名）。

## 6. 回复
一张表（会话 / 判据 / 实际读数 / 达成或判负 / 建议动作）+ 一句话总账：本期几个越线、几个建议收口、案尺寸超线几例、G 节回填 x/y、退役终验几例通过。
