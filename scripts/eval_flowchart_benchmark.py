#!/usr/bin/env python3
"""
Evaluate local flowcharts against appendix gold-standard benchmark cases.

Default mode is a static coverage check (no LLM required):
  - For each case with routing_hint=guideline and an existing flowchart,
    score overlap between gold decision therapy tokens and flowchart text.
  - Flag likely mis-routed cases (advanced/molecular masquerading as guideline).

Optional --llm runs GUIDELINE-mode decisions via src.tools (requires LLM config).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_JSONL = PROJECT_ROOT / "data" / "benchmark" / "cases.jsonl"
FLOWCHART_DIR = PROJECT_ROOT / "data" / "flowchart"
OUT_DIR = PROJECT_ROOT / "results" / "flowchart_eval"

# Therapy / decision tokens used for static overlap (EN + DE + abbreviations)
TOKEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("7+3", re.compile(r"7\s*\+\s*3|daunorubicin.*cytarabin|cytarabin.*daunorubicin", re.I)),
    ("GO", re.compile(r"gemtuzumab(?:\s+ozogamicin)?|(?<![A-Za-z])GO(?![A-Za-z])", re.I)),
    ("Inotuzumab", re.compile(r"inotuzumab", re.I)),
    ("CPX-351", re.compile(r"cpx-?351|vyxeos", re.I)),
    ("ATRA", re.compile(r"\bATRA\b|all-?trans.?retinoic", re.I)),
    ("ATO", re.compile(r"\bATO\b|arsenic", re.I)),
    ("HU", re.compile(r"hydroxyurea|\bHU\b", re.I)),
    ("leukapheresis", re.compile(r"leukapheres", re.I)),
    ("allo-SCT", re.compile(r"allo(?:geneic)?[-\s]?(?:szt|sct|transplant)", re.I)),
    ("HMA+Ven", re.compile(r"hma\s*\+\s*ven|azacitidin.*venetoclax|venetoclax.*azacitidin", re.I)),
    ("Venetoclax", re.compile(r"venetoclax|\bvipor\b", re.I)),
    ("R-CHOP", re.compile(r"r-?chop", re.I)),
    ("Pola-R-CHP", re.compile(r"pola(?:tuzumab)?[-\s]?r-?chp|pola-?r-?chp", re.I)),
    ("HD-MTX", re.compile(r"hd-?mtx|high[-\s]?dose\s*mtx|methotrexat", re.I)),
    ("orchiectomy", re.compile(r"orchiektomie|orchiectomy", re.I)),
    ("H.pylori", re.compile(r"h\.?\s*pylori|eradikation|eradication", re.I)),
    ("RT", re.compile(r"radiation|radiotherap|bestrahlung|\bRT\b|ISRT", re.I)),
    ("W&W", re.compile(r"w\s*&\s*w|watch[-\s]?and[-\s]?wait|beobachtung|watchful", re.I)),
    ("R-Benda", re.compile(r"r-?benda|rituximab.*bendamustin|bendamustin", re.I)),
    ("BrECADD", re.compile(r"brecadd", re.I)),
    ("ABVD", re.compile(r"\bABVD\b", re.I)),
    ("BEACOPP", re.compile(r"beacopp", re.I)),
    ("Cladribine", re.compile(r"cladribin|2-cda", re.I)),
    ("ESA", re.compile(r"\bESA\b|erythropoetin|epoetin", re.I)),
    ("Asciminib", re.compile(r"asciminib", re.I)),
    ("Ponatinib", re.compile(r"ponatinib", re.I)),
    ("Dasatinib", re.compile(r"dasatinib", re.I)),
    ("Imatinib", re.compile(r"imatinib", re.I)),
    ("Nelarabine", re.compile(r"nelarabin", re.I)),
    ("Blinatumomab", re.compile(r"blinatumomab", re.I)),
    ("Dara-VRd", re.compile(r"dara[-\s]?vrd|dara-?vrd", re.I)),
    ("Dara-VCD", re.compile(r"dara\s*vcd|dara-?vcd|dara.?vcd", re.I)),
    ("VRd", re.compile(r"\bVRd\b|bortezomib.*lenalidomid", re.I)),
    ("KCd", re.compile(r"\bKCD\b|\bKCd\b|carfilzomib.*cyclophosphamid", re.I)),
    ("ASCT", re.compile(r"\bASCT\b|\bASZT\b|autolog|hochdosis|high[-\s]?dose", re.I)),
    ("tandem", re.compile(r"tandem", re.I)),
    ("MGUS-no-tx", re.compile(r"no treatment|keine.*therapie|no therapy indication|keine antineoplastische", re.I)),
    ("Rituximab", re.compile(r"rituximab", re.I)),
    ("CAR-T", re.compile(r"car-?t", re.I)),
    ("BiTE", re.compile(r"glofitamab|epcoritamab|\bBiTE\b", re.I)),
    ("MEK", re.compile(r"mek[-\s]?inhibitor|trametinib", re.I)),
]

# If gold mentions these, case is likely not pure GUIDELINE
ADVANCED_MARKERS = re.compile(
    r"car-?t|glofitamab|epcoritamab|bite|mek inhibitor|trametinib|"
    r"molecular tumor board|cell therapy board|study option|"
    r"asciminib|resistance testing|nelarabin",
    re.I,
)


def load_cases() -> list[dict]:
    rows = []
    for line in BENCHMARK_JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def extract_tokens(text: str) -> set[str]:
    found = set()
    for name, pat in TOKEN_PATTERNS:
        if pat.search(text):
            found.add(name)
    return found


def static_eval_case(case: dict, flowchart_text: str) -> dict:
    gold = case.get("tumor_board_decision") or ""
    gold_tokens = extract_tokens(gold)
    fc_tokens = extract_tokens(flowchart_text)
    overlap = sorted(gold_tokens & fc_tokens)
    missing = sorted(gold_tokens - fc_tokens)

    coverage = (len(overlap) / len(gold_tokens)) if gold_tokens else None
    advanced_like = bool(ADVANCED_MARKERS.search(gold))

    if coverage is None:
        status = "no_tokens"
    elif advanced_like and coverage < 0.5:
        status = "likely_advanced"
    elif coverage >= 0.5:
        status = "pass"
    elif coverage > 0:
        status = "partial"
    else:
        status = "fail"

    return {
        "case_id": case["case_id"],
        "entity_slug": case["entity_slug"],
        "routing_hint": case["routing_hint"],
        "question": case.get("question"),
        "gold": gold,
        "gold_tokens": sorted(gold_tokens),
        "flowchart_tokens_hit": overlap,
        "missing_tokens": missing,
        "coverage": coverage,
        "status": status,
        "advanced_marker_in_gold": advanced_like,
    }


def run_static(cases: list[dict], route_filter: str) -> list[dict]:
    results = []
    for case in cases:
        if route_filter != "all" and case.get("routing_hint") != route_filter:
            continue
        slug = case.get("entity_slug")
        fc_path = FLOWCHART_DIR / f"{slug}.txt"
        if not fc_path.exists():
            results.append(
                {
                    "case_id": case["case_id"],
                    "entity_slug": slug,
                    "routing_hint": case["routing_hint"],
                    "status": "no_flowchart",
                    "gold": case.get("tumor_board_decision"),
                }
            )
            continue
        fc = fc_path.read_text(encoding="utf-8")
        results.append(static_eval_case(case, fc))
    return results


def run_llm(cases: list[dict], route_filter: str) -> list[dict]:
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.tools import _decide_with_guideline  # noqa: WPS433

    out = []
    for case in cases:
        if route_filter != "all" and case.get("routing_hint") != route_filter:
            continue
        slug = case.get("entity_slug")
        if not (FLOWCHART_DIR / f"{slug}.txt").exists():
            continue
        vignette_path = PROJECT_ROOT / "data" / "benchmark" / "cases" / f"{case['case_id']}.json"
        raw = json.loads(vignette_path.read_text(encoding="utf-8")).get("raw_vignette", "")
        agent_case = {
            "entity": case.get("primary_diagnosis", ""),
            "entity_slug": slug,
            "age": case.get("age"),
            "ecog": case.get("ecog"),
            "question": case.get("question"),
            "history": raw,
            "diagnosis": case.get("primary_diagnosis"),
        }
        config = {"model": None}  # tools use env defaults
        try:
            decision = _decide_with_guideline(
                agent_case,
                config,
                {"reasoning": "benchmark guideline eval", "flowchart_path": "auto"},
            )
            pred = decision.get("konferenzbeschluss") or decision.get("decision") or str(decision)
        except Exception as e:
            pred = f"ERROR: {e}"
        out.append(
            {
                "case_id": case["case_id"],
                "entity_slug": slug,
                "gold": case.get("tumor_board_decision"),
                "prediction": pred,
            }
        )
    return out


def apply_routing_overrides(cases: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Re-label clear advanced/molecular gold answers that heuristics missed.
    Returns (updated_cases, override_log).
    """
    overrides = {
        "l_case_12": "advanced",  # TKI resistance → Asciminib/Ponatinib + allo
        "l_case_15": "advanced",  # PD TLBL → Nelarabin bridge + allo conference
        "ly_case_06": "advanced",  # BiTE relapsed DLBCL
        "ly_case_07": "advanced",  # Glofitamab transformed FL
        "mm_case_5": "advanced",  # MEK inhibitor
        "mm_case_6": "advanced",  # CAR-T
        "mm_case_3": "advanced",  # relapsed KCD
        "mm_case_2": "advanced",  # tandem ASCT after prior therapy (SOP)
    }
    log = []
    updated = []
    for case in cases:
        cid = case["case_id"]
        if cid in overrides and case.get("routing_hint") != overrides[cid]:
            log.append({"case_id": cid, "from": case["routing_hint"], "to": overrides[cid]})
            case = {**case, "routing_hint": overrides[cid]}
        updated.append(case)
    return updated, log


def persist_routing_overrides(overrides: list[dict]) -> None:
    if not overrides:
        return
    by_id = {o["case_id"]: o["to"] for o in overrides}
    # jsonl
    lines = []
    for line in BENCHMARK_JSONL.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["case_id"] in by_id:
            rec["routing_hint"] = by_id[rec["case_id"]]
        lines.append(json.dumps(rec, ensure_ascii=False))
    BENCHMARK_JSONL.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # per-case json
    for cid, new_hint in by_id.items():
        path = PROJECT_ROOT / "data" / "benchmark" / "cases" / f"{cid}.json"
        rec = json.loads(path.read_text(encoding="utf-8"))
        rec["routing_hint"] = new_hint
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def summarize(results: list[dict]) -> dict:
    by_status: dict[str, int] = defaultdict(int)
    by_slug: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        by_status[r["status"]] += 1
        by_slug[r.get("entity_slug") or "?"][r["status"]] += 1
    return {
        "n": len(results),
        "by_status": dict(by_status),
        "by_slug": {k: dict(v) for k, v in sorted(by_slug.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--route",
        default="guideline",
        choices=["guideline", "advanced", "molecular", "all"],
        help="Which routing_hint subset to evaluate",
    )
    parser.add_argument("--llm", action="store_true", help="Also run GUIDELINE LLM decisions")
    parser.add_argument(
        "--apply-overrides",
        action="store_true",
        help="Persist advanced re-labels for clear non-guideline gold answers",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_cases()
    cases, override_log = apply_routing_overrides(cases)
    if args.apply_overrides:
        persist_routing_overrides(override_log)

    static_results = run_static(cases, args.route)
    summary = summarize(static_results)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "generated_at": stamp,
        "route_filter": args.route,
        "routing_overrides": override_log,
        "summary": summary,
        "results": static_results,
    }

    report_path = OUT_DIR / f"static_{args.route}_{stamp}.json"
    latest_path = OUT_DIR / f"static_{args.route}_latest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Human-readable markdown
    md_lines = [
        f"# Flowchart static eval ({args.route})",
        "",
        f"Generated: `{stamp}`",
        "",
        "## Summary",
        "",
        f"- cases: **{summary['n']}**",
        f"- by status: `{summary['by_status']}`",
        "",
        "## Failures / partial / likely_advanced",
        "",
    ]
    for r in static_results:
        if r["status"] in {"fail", "partial", "likely_advanced", "no_flowchart"}:
            md_lines.append(
                f"- **{r['case_id']}** ({r.get('entity_slug')}) `{r['status']}` "
                f"missing={r.get('missing_tokens')} gold_tokens={r.get('gold_tokens')}"
            )
    md_path = OUT_DIR / f"static_{args.route}_latest.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    if override_log:
        print("routing overrides:", override_log)
    print(f"Wrote {report_path}")
    print(f"Wrote {md_path}")

    if args.llm:
        llm_results = run_llm(cases, args.route)
        llm_path = OUT_DIR / f"llm_{args.route}_{stamp}.json"
        llm_path.write_text(json.dumps(llm_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {llm_path} ({len(llm_results)} cases)")


if __name__ == "__main__":
    main()
