#!/usr/bin/env python3
"""Fetch Onkopedia guideline HTML for flowchart authoring."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ONKOPEDIA_JSON = PROJECT_ROOT / "data" / "onkopedia.json"
OUT_DIR = PROJECT_ROOT / "data" / "onkopedia_cache"
ONKOPEDIA_URL = (
    "https://www.onkopedia.com/de/onkopedia/guidelines/{slug}/@@guideline/html/index.html"
)

# Plan target entities
TARGET_SLUGS = [
    "aml",
    "all",
    "mds",
    "cml",
    "dlbcl",
    "malt",
    "fl",
    "hcl",
    "chl",
    "myeloma",
    "waldenstrom",
]

MONTHS = {
    "januar": "01",
    "februar": "02",
    "märz": "03",
    "maerz": "03",
    "april": "04",
    "mai": "05",
    "juni": "06",
    "juli": "07",
    "august": "08",
    "september": "09",
    "oktober": "10",
    "november": "11",
    "dezember": "12",
}

# Strip tags roughly for readable therapy excerpts
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\n{3,}")


def parse_stand(html: str) -> str | None:
    header = re.search(
        r"Stand</span>\s*<span[^>]*>(\w+)\s+(\d{4})</span>",
        html,
        re.I,
    )
    if header:
        month, year = header.group(1).lower(), header.group(2)
        mm = MONTHS.get(month)
        if mm:
            return f"{year}-{mm}"
    dates = []
    for m in re.finditer(r"Stand\s+(\w+)\s+(\d{4})", html, re.I):
        mm = MONTHS.get(m.group(1).lower())
        if mm:
            dates.append(f"{m.group(2)}-{mm}")
    return max(dates) if dates else None


def html_to_text(html: str) -> str:
    # Drop scripts/styles
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    text = TAG_RE.sub("\n", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = WS_RE.sub("\n\n", text)
    return text.strip()


def extract_therapy_excerpt(text: str, max_chars: int = 80000) -> str:
    """Prefer Therapie / Therapiealgorithmen sections when present."""
    markers = [
        r"Therapiealgorithmen",
        r"6\.\s*Therapie",
        r"Therapie\s*$",
        r"Indikation zur Therapie",
        r"Erstlinientherapie",
    ]
    start = 0
    for marker in markers:
        m = re.search(marker, text, re.M | re.I)
        if m:
            start = m.start()
            break
    excerpt = text[start : start + max_chars]
    return excerpt


def fetch_one(entity_key: str, meta: dict) -> dict:
    slug = meta["onkopedia_slug"]
    url = ONKOPEDIA_URL.format(slug=slug)
    resp = requests.get(
        url,
        timeout=45,
        headers={"User-Agent": "Mozilla/5.0 (compatible; HemaGuide/1.0)"},
    )
    resp.raise_for_status()
    html = resp.text
    stand = parse_stand(html)
    text = html_to_text(html)
    therapy = extract_therapy_excerpt(text)

    raw_path = OUT_DIR / f"{entity_key}.html"
    text_path = OUT_DIR / f"{entity_key}.txt"
    therapy_path = OUT_DIR / f"{entity_key}_therapy.txt"
    meta_path = OUT_DIR / f"{entity_key}_meta.json"

    raw_path.write_text(html, encoding="utf-8")
    text_path.write_text(text, encoding="utf-8")
    therapy_path.write_text(therapy, encoding="utf-8")

    info = {
        "entity_key": entity_key,
        "name": meta.get("name"),
        "onkopedia_slug": slug,
        "url": url,
        "local_stand": meta.get("local_stand"),
        "online_stand": stand,
        "html_bytes": len(html),
        "therapy_chars": len(therapy),
        "status": (
            "current"
            if stand and meta.get("local_stand") and meta["local_stand"] >= stand
            else "outdated"
            if stand and meta.get("local_stand") and meta["local_stand"] < stand
            else "unknown"
        ),
    }
    meta_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return info


def main() -> None:
    registry = json.loads(ONKOPEDIA_JSON.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = {k: registry[k] for k in TARGET_SLUGS if k in registry}
    missing = [k for k in TARGET_SLUGS if k not in registry]
    if missing:
        print(f"WARNING: missing from onkopedia.json: {missing}")

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(fetch_one, k, v): k for k, v in targets.items()}
        for fut in as_completed(futs):
            key = futs[fut]
            try:
                info = fut.result()
                results.append(info)
                print(
                    f"OK {key}: stand local={info['local_stand']} "
                    f"online={info['online_stand']} ({info['status']}) "
                    f"therapy={info['therapy_chars']} chars"
                )
            except Exception as e:
                print(f"FAIL {key}: {e}")

    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(
        json.dumps(sorted(results, key=lambda x: x["entity_key"]), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(results)} caches to {OUT_DIR}")


if __name__ == "__main__":
    main()
