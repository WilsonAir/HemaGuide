# Benchmark cases (appendix gold standards)

Extracted from `paper/hema_guide_supplementary.txt` via:

```bash
python3 scripts/extract_benchmark_from_supplementary.py
```

Outputs:

- `cases.json` — all 45 cases as a JSON array (lean, no raw vignette)
- `cases.jsonl` — same, one JSON object per line
- `cases.xlsx` — Excel workbook with vignette + gold decision columns
- `cases/{id}.json` — per-case JSON including full `raw_vignette`
