#!/usr/bin/env python3
"""Apply Google AdSense script tags to generated HTML files."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MARKER_START = "<!-- ADSENSE_TAG_START -->"
MARKER_END = "<!-- ADSENSE_TAG_END -->"
PLACEHOLDER = "<!-- AdSense: 審査通過後にここにスクリプトを挿入 -->"


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def validate_client_id(client_id: str) -> str:
    cleaned = client_id.strip()
    if not re.fullmatch(r"ca-pub-\d+", cleaned):
        raise ValueError("AdSense client ID must look like ca-pub-XXXXXXXXXXXXXXXX")
    return cleaned


def adsense_block(client_id: str) -> str:
    escaped_id = html.escape(client_id, quote=True)
    return "\n".join(
        [
            MARKER_START,
            f'  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={escaped_id}" crossorigin="anonymous"></script>',
            MARKER_END,
        ]
    )


def replace_or_insert_adsense(content: str, block: str) -> str:
    # 1. すでに埋め込み済みのタグがある場合は置換
    pattern_existing = re.compile(
        rf"\n?\s*{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}",
        flags=re.DOTALL,
    )
    if pattern_existing.search(content):
        return pattern_existing.sub("\n" + block, content, count=1)

    # 2. プレースホルダーコメントがある場合は置換
    pattern_placeholder = re.compile(
        rf"\n?\s*{re.escape(PLACEHOLDER)}",
        flags=re.DOTALL,
    )
    if pattern_placeholder.search(content):
        return pattern_placeholder.sub("\n" + block, content, count=1)

    # 3. どちらもない場合は </head> の直前に挿入
    closing_head = re.search(r"</head>", content)
    if closing_head:
        return content[: closing_head.start()] + block + "\n" + content[closing_head.start() :]

    raise ValueError("HTML does not contain </head>")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Google AdSense tags to docs/*.html")
    parser.add_argument("--client-id", required=True, help="Google AdSense publisher ID, e.g. ca-pub-XXXXXXXXXXXXXXXX")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client_id = validate_client_id(args.client_id)
    docs_dir = resolve(args.docs_dir)
    block = adsense_block(client_id)

    changed: list[Path] = []
    for path in sorted(docs_dir.glob("*.html")):
        content = path.read_text(encoding="utf-8")
        updated = replace_or_insert_adsense(content, block)
        if updated != content:
            changed.append(path)
            if not args.dry_run:
                path.write_text(updated, encoding="utf-8")

    action = "Would update" if args.dry_run else "Updated"
    print(f"{action}: {len(changed)} HTML files")
    for path in changed:
        print(f"- {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
