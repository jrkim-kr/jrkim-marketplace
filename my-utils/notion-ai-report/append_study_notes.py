#!/usr/bin/env python3
"""
범용 AI 리포트 학습 노트 → Notion 본문 추가

보고서별 학습 노트 JSON 파일을 읽어 6섹션 구조의 Notion 블록으로 변환하고
기존 페이지에 추가한다.

Usage:
    python3 append_study_notes.py --page-id PAGE_ID --input study_notes.json
    python3 append_study_notes.py --input study_notes.json   # page_id from JSON
    python3 append_study_notes.py --input study_notes.json --dry-run  # 블록만 생성, API 호출 안함
"""

import sys
import os
import re
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from create_notion_page import (
    rt, callout_block, toggle_block, heading_block, quote_block,
    paragraph_block, bullet_block, numbered_block, todo_block,
    divider_block, table_block, append_blocks,
)


# ─── Rich Text Parser ───

def parse_rt(text):
    """Parse **bold** and *italic* markers into rt() list.

    Examples:
        "plain text"                → [rt("plain text")]
        "some **bold** text"        → [rt("some "), rt("bold", bold=True), rt(" text")]
        "**all bold**"              → [rt("all bold", bold=True)]
    """
    if not text:
        return []
    parts = []
    # Split by **bold** first
    segments = re.split(r"(\*\*.*?\*\*)", text)
    for segment in segments:
        if segment.startswith("**") and segment.endswith("**"):
            inner = segment[2:-2]
            if inner:
                parts.append(rt(inner, bold=True))
        else:
            # Split by *italic*
            sub_segments = re.split(r"(\*.*?\*)", segment)
            for sub in sub_segments:
                if sub.startswith("*") and sub.endswith("*") and len(sub) > 2:
                    inner = sub[1:-1]
                    if inner:
                        parts.append(rt(inner, italic=True))
                elif sub:
                    parts.append(rt(sub))
    return parts if parts else [rt("")]


def _build_detail_blocks(details):
    """Convert a details array into Notion blocks.

    Each element in details can be:
    - str                         → paragraph
    - {"paragraph": "text"}       → paragraph
    - {"numbered": ["a", "b"]}    → numbered_list_items
    - {"bullet": ["a", "b"]}      → bulleted_list_items
    - {"table": {"headers": [...], "rows": [...]}} → table
    """
    blocks = []
    for item in details:
        if isinstance(item, str):
            blocks.append(paragraph_block(parse_rt(item)))
        elif isinstance(item, dict):
            if "paragraph" in item:
                blocks.append(paragraph_block(parse_rt(item["paragraph"])))
            elif "numbered" in item:
                for li in item["numbered"]:
                    blocks.append(numbered_block(parse_rt(li)))
            elif "bullet" in item:
                for li in item["bullet"]:
                    blocks.append(bullet_block(parse_rt(li)))
            elif "table" in item:
                t = item["table"]
                blocks.append(table_block(t["headers"], t["rows"]))
    return blocks


def _build_question_toggle(q_data):
    """Build a toggle block for a single Q&A entry.

    q_data schema:
    {
      "q": "Question text with **bold**",
      "answer": "Key answer (quote)",
      "details": [...],       # optional
      "pm_summary": "PM 한 줄"  # optional
    }
    """
    children = []
    if q_data.get("answer"):
        children.append(quote_block(parse_rt(q_data["answer"])))
    if q_data.get("details"):
        children.extend(_build_detail_blocks(q_data["details"]))
    if q_data.get("pm_summary"):
        children.append(callout_block(
            [rt("PM 정리: "), rt(q_data["pm_summary"], bold=True)],
            icon="💬",
        ))
    return toggle_block(parse_rt(q_data["q"]), children=children)


# ─── Section Builders ───

def build_section_1(data):
    """① 한 문장 정의"""
    blocks = []
    blocks.append(heading_block(1, [rt("📘 AI 리포트 학습 노트")]))
    blocks.append(paragraph_block())
    blocks.append(callout_block(parse_rt(data["definition"]), icon="💡"))
    if data.get("quick_summary"):
        blocks.append(callout_block(parse_rt(data["quick_summary"]), icon="⚡"))
    blocks.append(divider_block())
    return blocks


def build_section_2(data):
    """② 고정 프레임 질문 (Layer 1)"""
    blocks = []
    cat_label = data.get("category_label", "")
    blocks.append(heading_block(2, [
        rt("② 고정 프레임 질문 "),
        rt(f"(카테고리: {cat_label})", italic=True),
    ]))
    if data.get("intro"):
        blocks.append(paragraph_block(parse_rt(data["intro"])))
    for q in data.get("questions", []):
        blocks.append(_build_question_toggle(q))
    if data.get("compression"):
        blocks.append(callout_block(parse_rt(data["compression"]), icon="🎯"))
    blocks.append(divider_block())
    return blocks


def build_section_3(data):
    """③ 보고서 고유 질문 (Layer 2)"""
    blocks = []
    blocks.append(heading_block(2, [
        rt("③ 보고서 고유 질문 "),
        rt("(PDF 파생)", italic=True),
    ]))
    blocks.append(callout_block(
        [rt("도출 기준: ", bold=True),
         rt("차별화"), rt(" (독자적 시각)  |  ", italic=True),
         rt("반직관"), rt(" (통념과 다른 주장)  |  ", italic=True),
         rt("실행"), rt(" (바로 적용 가능)", italic=True)],
        icon="📌",
    ))
    for q in data.get("questions", []):
        q_type = q.get("type", "")
        prefix = f"[{q_type}] " if q_type else ""
        q_copy = dict(q)
        q_copy["q"] = f"**{prefix}**{q.get('q', '')}"
        blocks.append(_build_question_toggle(q_copy))
    blocks.append(divider_block())
    return blocks


def build_section_4(data):
    """④ 사고 프레임 & 판단 기준"""
    blocks = []
    blocks.append(heading_block(2, [rt("④ 사고 프레임 & 판단 기준")]))
    if data.get("before_after"):
        blocks.append(table_block(
            ["Before", "After"],
            data["before_after"],
        ))
    if data.get("pm_role_change"):
        blocks.append(callout_block(parse_rt(data["pm_role_change"]), icon="👤"))
    if data.get("criteria_heading"):
        blocks.append(heading_block(3, parse_rt(data["criteria_heading"])))
    for c in data.get("criteria", []):
        blocks.append(bullet_block(parse_rt(c)))
    if data.get("key_insight"):
        blocks.append(callout_block(parse_rt(data["key_insight"]), icon="⚠️"))
    blocks.append(divider_block())
    return blocks


def build_section_5(data):
    """⑤ PM 체크리스트"""
    blocks = []
    blocks.append(heading_block(2, [rt("⑤ PM 체크리스트")]))
    for item in data.get("items", []):
        blocks.append(todo_block(parse_rt(item)))
    blocks.append(divider_block())
    return blocks


def build_section_6(data):
    """⑥ 적용 & 결론"""
    blocks = []
    blocks.append(heading_block(2, [rt("⑥ 적용 & 결론")]))

    # PoC toggle
    if data.get("poc"):
        poc = data["poc"]
        poc_children = []
        if poc.get("areas"):
            poc_children.append(paragraph_block([rt("적용 영역:", bold=True)]))
            for a in poc["areas"]:
                poc_children.append(bullet_block(parse_rt(a)))
        if poc.get("reasons"):
            poc_children.append(paragraph_block([rt("PoC에 적합한 이유:", bold=True)]))
            for r in poc["reasons"]:
                poc_children.append(bullet_block(parse_rt(r)))
        if poc.get("risk"):
            poc_children.append(callout_block(parse_rt(poc["risk"]), icon="⚠️"))
        blocks.append(toggle_block([rt("PoC 적용 가능 영역", bold=True)], children=poc_children))

    # Positioning toggle
    if data.get("positioning"):
        pos = data["positioning"]
        pos_children = []
        for p in pos.get("items", []):
            pos_children.append(bullet_block(parse_rt(p)))
        if pos.get("label"):
            pos_children.append(callout_block(parse_rt(pos["label"]), icon="📍"))
        blocks.append(toggle_block([rt("다른 보고서와의 포지셔닝", bold=True)], children=pos_children))

    # Judgment
    if data.get("judgment"):
        j = data["judgment"]
        blocks.append(heading_block(3, [rt("나의 판단")]))
        if j.get("trust"):
            blocks.append(paragraph_block([rt("👍 신뢰하는 부분: ", bold=True), rt(j["trust"])]))
        if j.get("doubt"):
            blocks.append(paragraph_block([rt("🤔 아직 의문: ", bold=True), rt(j["doubt"])]))

    blocks.append(divider_block())

    # Final quote
    if data.get("final_quote"):
        blocks.append(quote_block(parse_rt(data["final_quote"])))

    return blocks


# ─── Main ───

def build_all_blocks(notes):
    """Build all blocks from a study notes JSON structure."""
    blocks = []
    if notes.get("한_문장_정의"):
        blocks.extend(build_section_1(notes["한_문장_정의"]))
    if notes.get("고정_프레임_질문"):
        blocks.extend(build_section_2(notes["고정_프레임_질문"]))
    if notes.get("보고서_고유_질문"):
        blocks.extend(build_section_3(notes["보고서_고유_질문"]))
    if notes.get("사고_프레임"):
        blocks.extend(build_section_4(notes["사고_프레임"]))
    if notes.get("pm_체크리스트"):
        blocks.extend(build_section_5(notes["pm_체크리스트"]))
    if notes.get("적용_결론"):
        blocks.extend(build_section_6(notes["적용_결론"]))
    return blocks


def main():
    parser = argparse.ArgumentParser(description="Append study notes to Notion page")
    parser.add_argument("--input", required=True, help="Path to study notes JSON file")
    parser.add_argument("--page-id", help="Notion page ID (overrides JSON)")
    parser.add_argument("--dry-run", action="store_true", help="Build blocks without API call")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        notes = json.load(f)

    page_id = args.page_id or notes.get("page_id")
    if not page_id and not args.dry_run:
        print("Error: --page-id required (or include 'page_id' in JSON)")
        sys.exit(1)

    blocks = build_all_blocks(notes)
    print(f"Built {len(blocks)} top-level blocks")

    if args.dry_run:
        print("\n[DRY RUN] Blocks built successfully. No API call made.")
        print(json.dumps(blocks[:3], ensure_ascii=False, indent=2))
        print(f"... and {len(blocks) - 3} more blocks")
        return

    print(f"\nAppending to page: {page_id}")
    success = append_blocks(page_id, blocks)

    if success:
        print(f"\n✅ Done! URL: https://www.notion.so/{page_id.replace('-', '')}")
    else:
        print("\n❌ Failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
