"""Optional Docling adapter: extract a local filing with page provenance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def extract(path: Path, *, issuer: str, filing_type: str, published_at: str,
            source_id: str, source_url: str) -> dict:
    if not path.is_file():
        raise ValueError(f"Local filing does not exist: {path}")
    try:
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Docling is optional; install it separately to parse PDF/Office filings") from exc
    document = DocumentConverter().convert(str(path)).document
    sections = []
    for page_no in sorted(document.pages):
        markdown = document.export_to_markdown(page_no=page_no, traverse_pictures=True).strip()
        if markdown:
            sections.append({"key": f"page-{page_no}", "heading": f"Page {page_no}",
                             "text": markdown, "page": page_no})
    return {"issuer": issuer, "filing_type": filing_type,
            "published_at": published_at, "source_id": source_id,
            "source_url": source_url, "sections": sections,
            "extraction_note": "Page keys are provisional; align stable section keys before comparing revised layouts."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    for name in ("issuer", "filing-type", "published-at", "source-id", "source-url"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = extract(args.file, issuer=args.issuer, filing_type=args.filing_type,
                     published_at=args.published_at, source_id=args.source_id,
                     source_url=args.source_url)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
