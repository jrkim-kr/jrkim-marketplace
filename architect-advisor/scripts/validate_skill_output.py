#!/usr/bin/env python3
"""
Validate sub-skill JSON output against the unified contract schema (W3.2).

Usage:
    python3 scripts/validate_skill_output.py <output.json>
    cat output.json | python3 scripts/validate_skill_output.py -

Returns 0 if valid, 1 otherwise. Prints a human-readable diagnosis.

This script does NOT depend on jsonschema package — it implements only the
checks our schema actually requires (required fields, enums, regex patterns,
constants), so it works in environments without pip access.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "skill-output.schema.json"

REQUIRED = ["status", "summary", "next_actions", "artifacts", "schema_version"]
STATUS_ENUM = {"success", "warning", "error"}
SLASH_CMD_RE = re.compile(r"^/[a-z][a-z0-9-]*( .*)?$")
ARTIFACT_FILE_RE = re.compile(r"^architect-advisor/.+")
ARTIFACT_ID_RE = re.compile(r"^(ADR|DECISION|AUDIT|DECOMP|PATTERN|PORTFOLIO)-[A-Za-z0-9-]+$")
ADR_STATUS_ENUM = {"proposed", "accepted", "deprecated", "superseded"}


def validate(payload: dict) -> list[str]:
    errors: list[str] = []

    for f in REQUIRED:
        if f not in payload:
            errors.append(f"missing required field: {f}")

    if payload.get("schema_version") != "1.0":
        errors.append(f"schema_version must be '1.0', got {payload.get('schema_version')!r}")

    if payload.get("status") not in STATUS_ENUM:
        errors.append(f"status must be one of {sorted(STATUS_ENUM)}, got {payload.get('status')!r}")

    summary = payload.get("summary")
    if not isinstance(summary, str) or not 1 <= len(summary) <= 200:
        errors.append("summary must be a 1..200-char string")

    next_actions = payload.get("next_actions")
    if not isinstance(next_actions, list):
        errors.append("next_actions must be a list")
    else:
        for i, a in enumerate(next_actions):
            if not isinstance(a, str) or not SLASH_CMD_RE.match(a):
                errors.append(f"next_actions[{i}]={a!r} must be a slash command starting with /<lowercase-name>")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be a mapping")
    else:
        files = artifacts.get("files", [])
        if not isinstance(files, list):
            errors.append("artifacts.files must be a list")
        else:
            for i, p in enumerate(files):
                if not isinstance(p, str) or not ARTIFACT_FILE_RE.match(p):
                    errors.append(
                        f"artifacts.files[{i}]={p!r} must be a relative path under architect-advisor/"
                    )
        ids = artifacts.get("ids", [])
        if not isinstance(ids, list):
            errors.append("artifacts.ids must be a list")
        else:
            for i, x in enumerate(ids):
                if not isinstance(x, str) or not ARTIFACT_ID_RE.match(x):
                    errors.append(
                        f"artifacts.ids[{i}]={x!r} must match (ADR|DECISION|AUDIT|DECOMP|PATTERN|PORTFOLIO)-..."
                    )

    lifecycle = payload.get("lifecycle")
    if lifecycle is not None:
        if not isinstance(lifecycle, dict):
            errors.append("lifecycle must be a mapping")
        else:
            adr_status = lifecycle.get("adr_status")
            if adr_status is not None and adr_status not in ADR_STATUS_ENUM:
                errors.append(f"lifecycle.adr_status must be one of {sorted(ADR_STATUS_ENUM)}")

    return errors


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "-"
    raw = sys.stdin.read() if arg == "-" else Path(arg).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"❌ JSON parse failed: {e}\n")
        return 1

    errors = validate(payload)
    if errors:
        print("❌ schema validation failed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"✅ valid (status={payload['status']}, next={len(payload['next_actions'])} actions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
