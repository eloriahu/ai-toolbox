"""Render a compact Markdown evidence matrix from JSON source records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


def render_matrix(records: list[dict]) -> str:
    if not isinstance(records, list) or not records:
        raise ValueError("Input must be a non-empty JSON array of source records.")

    rows = []
    for position, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {position} must be an object.")
        title = _required(record, "title", position)
        url = _required(record, "url", position)
        claim = _required(record, "claim", position)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Record {position} has an invalid HTTP(S) URL.")
        published = str(record.get("published_at") or "—")
        rows.append(
            f"| {_escape(title)} | [{_escape(parsed.netloc)}]({url}) | "
            f"{_escape(published)} | {_escape(claim)} |"
        )

    return "\n".join(
        [
            "| Source | Link | Published | Supports |",
            "| --- | --- | --- | --- |",
            *rows,
        ]
    )


def _required(record: dict, field: str, position: int) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Record {position} requires a non-empty '{field}' string.")
    return value.strip()


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", help="JSON file; omit to read stdin")
    parser.add_argument("--output", help="Write Markdown to this path instead of stdout")
    args = parser.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        markdown = render_matrix(json.loads(raw)) + "\n"
    except (json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)


if __name__ == "__main__":
    main()
