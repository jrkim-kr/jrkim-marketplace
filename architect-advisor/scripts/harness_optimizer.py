#!/usr/bin/env python3
"""
architect-advisor self-audit (W3.3 — harness-optimizer).

Reads usage data accumulated under architect-advisor/_meta/usage.jsonl and
produces a monthly report at architect-advisor/_meta/audit-YYYY-MM.md.

Looks at:
  - Trigger frequency per sub-skill (decompose / decision / adr / audit /
    err-pattern / portfolio)
  - User accept vs revert ratio (if logged)
  - Average iteration count for arch-audit (santa-method)
  - Average council vote spread (4-vote vs 2-vote degraded)
  - Flag sub-skills with anomalies (over-triggered / never-used / high revert)

The report is advisory only — the user decides whether to adjust thresholds
or disable a skill. No automatic configuration changes happen here.

Usage:
    python3 scripts/harness_optimizer.py                 # current month
    python3 scripts/harness_optimizer.py --month 2026-04 # specific month
    python3 scripts/harness_optimizer.py --usage-jsonl <path>  # custom log

Logging input format (one JSON record per line):
    {
      "ts": 1234567890,
      "skill": "arch-audit",
      "outcome": "success" | "warning" | "error" | "user_revert",
      "iter": 2,                  # optional, e.g. santa-method iteration count
      "votes": {"A":3,"B":1},     # optional, council vote distribution
      "lite_mode": false           # optional
    }

This script is idempotent — re-running for the same month overwrites the
report file.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from lib.advisor_paths import resolve_layout  # noqa: E402


KNOWN_SKILLS = {
    "arch-decompose",
    "arch-council",
    "arch-adr",
    "arch-audit",
    "arch-err-pattern",
    "arch-portfolio",
}


def main() -> int:
    p = argparse.ArgumentParser(description="architect-advisor self-audit (monthly)")
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--month", default=None, help="YYYY-MM (default: current)")
    p.add_argument("--usage-jsonl", default=None, help="override usage log path")
    p.add_argument("--json", action="store_true", help="emit JSON instead of writing markdown")
    args = p.parse_args()

    layout = resolve_layout(args.root)
    usage_path = Path(args.usage_jsonl) if args.usage_jsonl else (layout.meta_dir() / "usage.jsonl")
    target_month = args.month or _dt.date.today().strftime("%Y-%m")

    if not usage_path.is_file():
        sys.stderr.write(
            f"[harness-optimizer] no usage log at {usage_path}\n"
            "Sub-skills should append records here on every invocation.\n"
        )
        return _emit_empty_report(layout, target_month, args.json)

    records = _load_records(usage_path, target_month)
    summary = _summarize(records)

    if args.json:
        print(json.dumps({"month": target_month, **summary}, ensure_ascii=False, indent=2))
        return 0

    report_path = layout.meta_dir() / f"audit-{target_month}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_markdown(target_month, summary, len(records)), encoding="utf-8")
    print(f"✅ self-audit report: {report_path.relative_to(layout.project_root)}")
    return 0


def _load_records(path: Path, month: str) -> list[dict]:
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = rec.get("ts")
        if not isinstance(ts, (int, float)):
            continue
        rec_month = _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).strftime("%Y-%m")
        if rec_month == month:
            out.append(rec)
    return out


def _summarize(records: list[dict]) -> dict:
    by_skill_count: Counter = Counter()
    by_skill_outcomes: dict[str, Counter] = defaultdict(Counter)
    audit_iters: list[int] = []
    decision_lite_count = 0
    decision_full_count = 0

    for r in records:
        skill = r.get("skill", "unknown")
        by_skill_count[skill] += 1
        by_skill_outcomes[skill][r.get("outcome", "unknown")] += 1

        if skill == "arch-audit" and isinstance(r.get("iter"), int):
            audit_iters.append(int(r["iter"]))
        if skill == "arch-council":
            if r.get("lite_mode"):
                decision_lite_count += 1
            else:
                decision_full_count += 1

    flags: list[str] = []
    total = sum(by_skill_count.values()) or 1

    for s in KNOWN_SKILLS:
        if by_skill_count.get(s, 0) == 0:
            flags.append(f"{s} 사용 0회 — skill 신호 적합성 또는 사용자 인지 점검")
        share = by_skill_count.get(s, 0) / total
        if share > 0.5:
            flags.append(f"{s} 비중 {share:.0%} — 트리거 과민 가능, description 재조정 검토")

    revert_ratios: dict[str, float] = {}
    for s, outcomes in by_skill_outcomes.items():
        n = sum(outcomes.values())
        if n == 0:
            continue
        revert = outcomes.get("user_revert", 0)
        ratio = revert / n
        revert_ratios[s] = ratio
        if ratio >= 0.3:
            flags.append(f"{s} user_revert 비율 {ratio:.0%} — 결과 품질 저하 의심")

    return {
        "total_invocations": sum(by_skill_count.values()),
        "by_skill": dict(by_skill_count),
        "by_skill_outcomes": {s: dict(c) for s, c in by_skill_outcomes.items()},
        "audit_iter_avg": round(statistics.mean(audit_iters), 2) if audit_iters else None,
        "audit_iter_max": max(audit_iters) if audit_iters else None,
        "decision_lite_share": (
            round(decision_lite_count / max(decision_lite_count + decision_full_count, 1), 2)
        ),
        "revert_ratios": {s: round(v, 2) for s, v in revert_ratios.items()},
        "flags": flags,
    }


def _render_markdown(month: str, summary: dict, sample_size: int) -> str:
    lines = [
        f"# architect-advisor 자가 감사 — {month}",
        "",
        f"> harness-optimizer가 자동 생성. 입력 표본: {sample_size}건. **권고일 뿐 자동 변경 없음.**",
        "",
        "## 사용량",
        "",
        "| Skill | 호출 | success | warning | error | user_revert |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    by_skill = summary["by_skill"]
    by_outcomes = summary["by_skill_outcomes"]
    for s in sorted(KNOWN_SKILLS):
        counts = by_outcomes.get(s, {})
        lines.append(
            f"| {s} | {by_skill.get(s, 0)} | {counts.get('success', 0)} "
            f"| {counts.get('warning', 0)} | {counts.get('error', 0)} | {counts.get('user_revert', 0)} |"
        )
    lines.extend([
        "",
        "## arch-audit santa-method 수렴성",
        "",
        f"- 평균 iteration: {summary['audit_iter_avg']}",
        f"- 최대 iteration: {summary['audit_iter_max']}",
        "",
        "## arch-council 모드",
        "",
        f"- lite (2-voice) 비율: {summary['decision_lite_share']:.0%}",
        "",
        "## 권고 (Flags)",
        "",
    ])
    if summary["flags"]:
        for f in summary["flags"]:
            lines.append(f"- ⚠️ {f}")
    else:
        lines.append("- ✅ 이상 신호 없음")
    lines.extend([
        "",
        "## 다음 행동 후보 (사용자 결정)",
        "",
        "- 트리거 과민 skill의 description에 NOT-trigger 케이스 추가",
        "- user_revert 높은 skill의 acceptance criteria 재검토",
        "- audit iteration 평균이 2.5 초과면 santa-method rubric 항목을 도메인별 reduce",
        "- 0회 사용 skill을 임시 비활성화하거나 별칭 추가",
        "",
    ])
    return "\n".join(lines)


def _emit_empty_report(layout, month: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"month": month, "total_invocations": 0, "flags": ["no usage log"]}, ensure_ascii=False, indent=2))
    else:
        report_path = layout.meta_dir() / f"audit-{month}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            f"# architect-advisor 자가 감사 — {month}\n\n"
            "> 입력 표본 0건. 사용 로그(`architect-advisor/_meta/usage.jsonl`)가 비어있음.\n"
            "> 각 sub-skill에서 호출 시 다음을 한 줄 append하도록 구현되면 다음 달부터 데이터가 쌓입니다.\n\n"
            "```json\n"
            "{\"ts\": 1234567890, \"skill\": \"arch-council\", \"outcome\": \"success\"}\n"
            "```\n",
            encoding="utf-8",
        )
        print(f"⚠️  empty report written: {report_path.relative_to(layout.project_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
