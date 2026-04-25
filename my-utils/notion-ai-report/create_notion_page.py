#!/usr/bin/env python3
"""
AI Report → Notion Database Page Creator & Body Appender

Usage:
    python3 create_notion_page.py --json '{"보고서명": "...", ...}'
    python3 create_notion_page.py --file data.json
    python3 create_notion_page.py --append-to PAGE_ID --body-file body.json
"""

import os
import urllib.request
import json
import sys
import argparse

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
if not NOTION_API_KEY:
    sys.exit("ERROR: NOTION_API_KEY environment variable is required")
DB_ID = os.environ.get("NOTION_AI_REPORT_DB_ID", "309341dc2a9380ed9001caa63f9f45ba")
NOTION_VERSION = "2022-06-28"


# ─── Rich Text Helpers ───

def rt(content, bold=False, italic=False, code=False, strikethrough=False, color="default"):
    """Create a single rich_text item."""
    item = {"type": "text", "text": {"content": content}}
    annotations = {}
    if bold: annotations["bold"] = True
    if italic: annotations["italic"] = True
    if code: annotations["code"] = True
    if strikethrough: annotations["strikethrough"] = True
    if color != "default": annotations["color"] = color
    if annotations:
        item["annotations"] = annotations
    return item


def _ensure_rt_list(content):
    """Convert content to rich_text list if it's a string."""
    if content is None:
        return []
    if isinstance(content, str):
        return [rt(content)]
    if isinstance(content, dict):
        return [content]
    return content


# ─── Block Builders ───

def callout_block(content, icon="💡", children=None):
    """Create a callout block."""
    block = {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": _ensure_rt_list(content),
            "icon": {"type": "emoji", "emoji": icon}
        }
    }
    if children:
        block["callout"]["children"] = children
    return block


def toggle_block(title, children=None):
    """Create a toggle block."""
    block = {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": _ensure_rt_list(title),
        }
    }
    if children:
        block["toggle"]["children"] = children
    return block


def heading_block(level, content):
    """Create a heading block (level 1-3)."""
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {
            "rich_text": _ensure_rt_list(content)
        }
    }


def quote_block(content):
    """Create a quote block."""
    return {
        "object": "block",
        "type": "quote",
        "quote": {
            "rich_text": _ensure_rt_list(content)
        }
    }


def paragraph_block(content=None):
    """Create a paragraph block."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": _ensure_rt_list(content) if content else []
        }
    }


def bullet_block(content, children=None):
    """Create a bulleted list item."""
    block = {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": _ensure_rt_list(content)
        }
    }
    if children:
        block["bulleted_list_item"]["children"] = children
    return block


def numbered_block(content, children=None):
    """Create a numbered list item."""
    block = {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {
            "rich_text": _ensure_rt_list(content)
        }
    }
    if children:
        block["numbered_list_item"]["children"] = children
    return block


def todo_block(content, checked=False):
    """Create a to-do block."""
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {
            "rich_text": _ensure_rt_list(content),
            "checked": checked
        }
    }


def divider_block():
    """Create a divider block."""
    return {"object": "block", "type": "divider", "divider": {}}


def table_block(headers, rows, has_column_header=True):
    """Create a table block with header row and data rows."""
    width = len(headers)
    table_rows = []
    table_rows.append({
        "type": "table_row",
        "table_row": {
            "cells": [[rt(h, bold=True)] for h in headers]
        }
    })
    for row in rows:
        cells = []
        for cell in row:
            if isinstance(cell, list):
                cells.append(cell)
            else:
                cells.append([rt(str(cell))])
        table_rows.append({
            "type": "table_row",
            "table_row": {"cells": cells}
        })
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": has_column_header,
            "has_row_header": False,
            "children": table_rows
        }
    }


# ─── Page Properties Builder ───

def build_rich_text(text):
    """Build a rich_text property value, splitting into 2000-char chunks if needed."""
    if not text:
        return []
    chunks = []
    for i in range(0, len(text), 2000):
        chunks.append({"type": "text", "text": {"content": text[i:i+2000]}})
    return chunks


def build_page_properties(data):
    """Build Notion page properties from extracted data dict."""
    props = {}

    if data.get("보고서명"):
        props["보고서명"] = {
            "title": [{"type": "text", "text": {"content": data["보고서명"]}}]
        }

    if data.get("URL"):
        props["URL"] = {"url": data["URL"]}

    if data.get("발행일"):
        props["발행일"] = {"date": {"start": data["발행일"]}}

    if data.get("발행기관"):
        props["발행기관"] = {"select": {"name": data["발행기관"]}}

    if data.get("카테고리"):
        props["카테고리"] = {"select": {"name": data["카테고리"]}}

    if data.get("주제"):
        topics = data["주제"] if isinstance(data["주제"], list) else [data["주제"]]
        props["주제"] = {"multi_select": [{"name": t} for t in topics]}

    if data.get("요약"):
        props["요약"] = {"rich_text": build_rich_text(data["요약"])}

    if data.get("한 문장 정의"):
        props["한 문장 정의"] = {"rich_text": build_rich_text(data["한 문장 정의"])}

    if data.get("PM 핵심 질문"):
        props["PM 핵심 질문"] = {"rich_text": build_rich_text(data["PM 핵심 질문"])}

    if data.get("PM 한 줄 결론"):
        props["PM 한 줄 결론"] = {"rich_text": build_rich_text(data["PM 한 줄 결론"])}

    if data.get("상태"):
        props["상태"] = {"status": {"name": data["상태"]}}

    if data.get("작성일"):
        props["작성일"] = {"date": {"start": data["작성일"]}}

    return props


def build_page_body(data):
    """Build Notion page body (children blocks) for detailed content."""
    children = []

    if data.get("본문_섹션"):
        for section in data["본문_섹션"]:
            if section.get("heading"):
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": section["heading"]}}]
                    }
                })
            if section.get("content"):
                text = section["content"]
                for i in range(0, len(text), 2000):
                    chunk = text[i:i+2000]
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        }
                    })

    return children


# ─── API Functions ───

def create_notion_page(data):
    """Create a page in the Notion database."""
    properties = build_page_properties(data)
    children = build_page_body(data)

    payload = {
        "parent": {"database_id": DB_ID},
        "properties": properties,
    }

    if children:
        payload["children"] = children[:100]

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=body,
        method="POST"
    )
    req.add_header("Authorization", f"Bearer {NOTION_API_KEY}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            page_id = result.get("id", "")
            page_url = result.get("url", "")
            print(f"Page created successfully!")
            print(f"  Page ID: {page_id}")
            print(f"  URL: {page_url}")

            if len(children) > 100:
                append_blocks(page_id, children[100:])

            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Error creating page: {e.code}")
        print(error_body)
        return None


def append_blocks(block_id, children):
    """Append children blocks to a page or block (batched in groups of 100)."""
    for i in range(0, len(children), 100):
        batch = children[i:i+100]
        payload = {"children": batch}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            f"https://api.notion.com/v1/blocks/{block_id}/children",
            data=body,
            method="PATCH"
        )
        req.add_header("Authorization", f"Bearer {NOTION_API_KEY}")
        req.add_header("Notion-Version", NOTION_VERSION)
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as response:
                print(f"  Appended {len(batch)} blocks (batch {i//100 + 1})")
        except urllib.error.HTTPError as e:
            print(f"  Error appending blocks: {e.code}")
            print(e.read().decode())
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Create Notion page from AI report data")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--json", type=str, help="JSON string with report data")
    group.add_argument("--file", type=str, help="Path to JSON file with report data")
    group.add_argument("--append-to", type=str, help="Append body blocks to existing page ID")

    parser.add_argument("--body-file", type=str, help="JSON file with body blocks (for --append-to)")
    args = parser.parse_args()

    if args.append_to:
        if not args.body_file:
            print("Error: --body-file is required with --append-to")
            sys.exit(1)
        with open(args.body_file, "r", encoding="utf-8") as f:
            body_data = json.load(f)
        children = body_data if isinstance(body_data, list) else body_data.get("children", [])
        print(f"Appending {len(children)} blocks to page {args.append_to}...")
        success = append_blocks(args.append_to, children)
        if success:
            print(f"Done! URL: https://www.notion.so/{args.append_to.replace('-', '')}")
        else:
            sys.exit(1)
    else:
        if args.json:
            data = json.loads(args.json)
        else:
            with open(args.file, "r", encoding="utf-8") as f:
                data = json.load(f)
        create_notion_page(data)


if __name__ == "__main__":
    main()
