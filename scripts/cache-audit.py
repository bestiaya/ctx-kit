#!/usr/bin/env python3
"""cache-audit.py — claude CLI 会话缓存周检（ctx-kit 配套）

预注册判据（周检口径，判负照报）：
  - 讨论/导师会话：重写占比 <10% 且 水位 p50 <150k
  - 执行会话：compact 次数 = 0 且 水位峰值 <200k
  - 任何越线行尾标 ⚠️

口径：
  - 当量 = input×1 + cache_read×0.1 + cache_write×2 + output×5（写按 1h 桶 2× 实测价）
  - 重写事件 = 非首条请求 且 单次 cache_write >150k 且 读量塌缩到既有上下文一半以下
    （读量仍≈既有上下文的是"大块新料首次入场"，不是整段冷重写，不计）
  - 已知盲区：compact 摘要请求不落账在 jsonl，本表不含其成本
  - jsonl 时间戳为 UTC，与本地钟表比对前先按本地时区换算

用法：
  python3 cache-audit.py <jsonl路径...>              # 指定会话
  python3 cache-audit.py --all [最小MB]              # 扫当前项目（默认 >2MB）
  python3 cache-audit.py --project <目录> --all      # 指定项目目录
项目目录默认从 cwd 推导：~/.claude/projects/ + cwd 中非字母数字字符全部替换为 '-'。
"""
import json, sys, glob, os, re, datetime, statistics

PROJ = (
    os.path.expanduser("~/.claude/projects/")
    + re.sub(r'[^A-Za-z0-9]', '-', os.getcwd())
    + "/"
)


def pt(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def audit(fp):
    main, compacts = {}, 0
    with open(fp, errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") == "system" and o.get("subtype") == "compact_boundary":
                compacts += 1
            if o.get("type") != "assistant" or o.get("isSidechain"):
                continue
            m = o.get("message") or {}
            u = m.get("usage") or {}
            mid = m.get("id")
            if not mid or not o.get("timestamp"):
                continue
            rec = dict(
                ts=o["timestamp"],
                it=u.get("input_tokens", 0) or 0,
                cr=u.get("cache_read_input_tokens", 0) or 0,
                cc=u.get("cache_creation_input_tokens", 0) or 0,
                ot=u.get("output_tokens", 0) or 0,
            )
            if mid not in main or rec["ot"] > main[mid]["ot"]:
                main[mid] = rec
    rows = sorted(main.values(), key=lambda r: r["ts"])
    if not rows:
        return None
    ctx = [r["it"] + r["cr"] + r["cc"] for r in rows]
    # 重写 = 大额写入 且 读量塌缩到既有上下文一半以下（只剩共享头部）。
    # 若读量仍≈既有上下文，是"大块新料首次入场"，不算重写。
    rewrites = [
        r
        for i, r in enumerate(rows)
        if i > 0 and r["cc"] > 150_000 and r["cr"] < ctx[i - 1] * 0.5
    ]
    eq = sum(r["it"] + 0.1 * r["cr"] + 2 * r["cc"] + 5 * r["ot"] for r in rows)
    rw = sum(r["cc"] for r in rewrites) * 2
    return dict(
        file=os.path.basename(fp),
        n=len(rows),
        days=(pt(rows[-1]["ts"]) - pt(rows[0]["ts"])).days,
        p50=int(statistics.median(ctx)),
        peak=max(ctx),
        eq_m=eq / 1e6,
        rewrites=len(rewrites),
        rw_share=(rw / eq * 100) if eq else 0.0,
        compacts=compacts,
    )


def main():
    args = sys.argv[1:]
    proj = PROJ
    if "--project" in args:
        i = args.index("--project")
        proj = os.path.expanduser(args[i + 1]).rstrip("/") + "/"
        args = args[:i] + args[i + 2:]
    if not args or args[0] == "--all":
        minmb = float(args[1]) if len(args) > 1 else 2.0
        files = [f for f in glob.glob(proj + "*.jsonl") if os.path.getsize(f) > minmb * 1e6]
        print(f"# 项目目录: {proj}")
    else:
        files = args
    hdr = f"{'会话':34} {'请求':>5} {'天':>3} {'p50水位':>9} {'峰值':>9} {'花费M':>7} {'重写':>4} {'重写占比':>7} {'压缩':>4}"
    print(hdr)
    for fp in sorted(files, key=os.path.getmtime, reverse=True):
        r = audit(fp)
        if not r:
            continue
        flag = " ⚠️" if (r["rw_share"] >= 10 or r["p50"] >= 150_000 or r["compacts"] > 0) else ""
        print(
            f"{r['file'][:34]:34} {r['n']:>5} {r['days']:>3} {r['p50']:>9,} {r['peak']:>9,}"
            f" {r['eq_m']:>7.1f} {r['rewrites']:>4} {r['rw_share']:>6.0f}% {r['compacts']:>4}{flag}"
        )


if __name__ == "__main__":
    main()
