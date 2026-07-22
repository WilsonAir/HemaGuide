# Diagnosis decision trees

Executable diagnosis / workup / classification trees extracted from Onkopedia
guideline sections (Diagnose, Diagnostik, Klassifikation, Staging, Differentialdiagnose).

| Item | Path |
|------|------|
| Trees | `data/diagnosis/{entity_slug}.txt` |
| Treatment counterparts | `data/flowchart/{entity_slug}.txt` |
| Registry / Stand | `data/onkopedia.json` |

## Format

Same style as flowcharts: node IDs, explicit `IF` / `ELSE` / `->` branches.

Typical node groups:

- `[DX-SUSPECT]` — when to start workup  
- `[DX-WORKUP]` — required tests  
- `[DX-CRITERIA]` — diagnostic criteria  
- `[DX-CLASS]` / `[DX-STAGE]` / `[DX-RISK]` — subtype, staging, risk  
- `[DX-DDX]` — differential diagnosis  

Language: German (aligned with Onkopedia DE and treatment flowcharts).

## Coverage

One file per entry in `onkopedia.json` (30 entities).

## Note

These trees support **diagnostic structuring**. Runtime GUIDELINE mode still loads
**treatment** flowcharts from `data/flowchart/` unless the agent is wired to also
load `data/diagnosis/`.
