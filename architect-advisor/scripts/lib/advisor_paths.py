"""
Path layout resolver for architect-advisor.

All sub-skills MUST go through this module to compute output paths.
This is the single source of truth for the directory layout.

Layout (single-product, default):
    [project_root]/
    └── architect-advisor/
        ├── state/workflow.json
        ├── decisions/
        ├── adrs/
        ├── audits/
        ├── decompositions/
        ├── patterns/CONFLICT_PATTERNS.md
        ├── patterns/candidates.jsonl
        ├── observations.jsonl
        ├── portfolio/
        └── _meta/

Layout (monorepo):
    [project_root]/architect-advisor/<product>/<same subdirs>
    [project_root]/architect-advisor/_shared/patterns/CONFLICT_PATTERNS.md

Resolution rules:
  1. Read .architect-advisor.json if present (cached detection result).
  2. If absent, treat as single-product (do NOT auto-write — caller decides).
  3. In monorepo mode, callers must pass `product` (or rely on default_product).

Design notes:
  - This module never creates directories; it only computes paths.
  - Callers (sub-skills) are responsible for `mkdir -p` before writing.
  - All returned paths are absolute, resolved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


CONFIG_FILENAME = ".architect-advisor.json"
ROOT_DIR_NAME = "architect-advisor"


@dataclass(frozen=True)
class AdvisorLayout:
    project_root: Path
    is_monorepo: bool
    product: Optional[str]
    advisor_root: Path

    def state_file(self) -> Path:
        return self.advisor_root / "state" / "workflow.json"

    def decisions_dir(self) -> Path:
        return self.advisor_root / "decisions"

    def adrs_dir(self) -> Path:
        return self.advisor_root / "adrs"

    def audits_dir(self) -> Path:
        return self.advisor_root / "audits"

    def decompositions_dir(self) -> Path:
        return self.advisor_root / "decompositions"

    def patterns_dir(self) -> Path:
        if self.is_monorepo:
            return self.project_root / ROOT_DIR_NAME / "_shared" / "patterns"
        return self.advisor_root / "patterns"

    def conflict_patterns_file(self) -> Path:
        return self.patterns_dir() / "CONFLICT_PATTERNS.md"

    def candidates_file(self) -> Path:
        return self.patterns_dir() / "candidates.jsonl"

    def observations_file(self) -> Path:
        return self.advisor_root / "observations.jsonl"

    def portfolio_dir(self) -> Path:
        return self.advisor_root / "portfolio"

    def meta_dir(self) -> Path:
        return self.advisor_root / "_meta"


def resolve_layout(project_root: str | Path = ".", product: Optional[str] = None) -> AdvisorLayout:
    root = Path(project_root).resolve()
    cfg = _load_config(root)

    if cfg is None or not cfg.get("monorepo"):
        return AdvisorLayout(
            project_root=root,
            is_monorepo=False,
            product=None,
            advisor_root=(root / ROOT_DIR_NAME).resolve(),
        )

    chosen = product or cfg.get("default_product")
    products = cfg.get("products") or []

    if not chosen and products:
        chosen = products[0]
    if not chosen:
        chosen = "app"

    if products and chosen not in products:
        raise ValueError(
            f"Product '{chosen}' not declared in .architect-advisor.json products={products}"
        )

    return AdvisorLayout(
        project_root=root,
        is_monorepo=True,
        product=chosen,
        advisor_root=(root / ROOT_DIR_NAME / chosen).resolve(),
    )


def _load_config(root: Path) -> Optional[dict]:
    p = root / CONFIG_FILENAME
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def relative_to_root(layout: AdvisorLayout, target: Path) -> str:
    """Return a path string relative to project_root, suitable for artifacts.files schema."""
    target = Path(target).resolve()
    try:
        return str(target.relative_to(layout.project_root))
    except ValueError:
        return str(target)


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    prod = sys.argv[2] if len(sys.argv) > 2 else None
    layout = resolve_layout(root, prod)
    print(json.dumps({
        "project_root": str(layout.project_root),
        "is_monorepo": layout.is_monorepo,
        "product": layout.product,
        "advisor_root": str(layout.advisor_root),
        "state_file": str(layout.state_file()),
        "adrs_dir": str(layout.adrs_dir()),
        "patterns_dir": str(layout.patterns_dir()),
    }, ensure_ascii=False, indent=2))
