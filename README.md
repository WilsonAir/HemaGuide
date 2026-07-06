# HemaGuide

Clinical decision support in hematological malignancies using a case-grounded AI agent.

> **Research Use Only** – This software is intended for research purposes only. Generated decisions require validation by qualified medical professionals and must not be used for clinical care without proper oversight.

## Fork / Modifications

This repository is a **modified fork** of the upstream project:

- **Upstream (original):** [https://github.com/Friedrich-Lab/HemaGuide](https://github.com/Friedrich-Lab/HemaGuide)
- **This fork:** [https://github.com/WilsonAir/HemaGuide](https://github.com/WilsonAir/HemaGuide)

Local changes relative to upstream include (non-exhaustive):

- OpenAI / DashScope-compatible LLM defaults (`src/llm.py`, `backend/main.py`, frontend config)
- Backend deployment helpers (`scripts/start-backend.sh`, `/hema_guide` proxy notes)
- System architecture notes ([`system.md`](system.md))
- Draft AML flowchart under `data/flowchart/` (flowcharts are not shipped upstream)
- Supplementary docx generation and trial scripts under `scripts/`

For the full pipeline, routing logic, and knowledge-base design, see [`system.md`](system.md).

## System Requirements

Developed and tested on Mac Studio M3 Ultra, 96GB RAM. We used Python 3.12.

### Prerequisites

Install Python 3.12+ from [python.org](https://www.python.org/downloads/) or via your package manager.

## Quick Start

The fastest path is the bundled launcher:

1. Install [Ollama](https://ollama.com/download)
2. Clone this fork (or the [upstream repository](https://github.com/Friedrich-Lab/HemaGuide)):
```bash
git clone https://github.com/WilsonAir/HemaGuide
```
3. Double-click **`HemaGuide.command`**

It installs Python tools, pulls the required models, creates the virtual environment, starts the server, and opens the web interface at `http://localhost:8000`. The interface ships pre-built — no Node.js required. Double-click **`HemaGuide-Stop.command`** to stop it.

Processing cases also needs a `.env` file and a built knowledge base — see [Step-by-step](#step-by-step).

## Step-by-step

### 1. Setup

```bash
python3 -m venv HemaGuide_venv             # Create virtual environment
source HemaGuide_venv/bin/activate         # Activate it
pip install -r requirements.txt             # Install dependencies
```

Create a `.env` file with:

```bash
# Required (at least one LLM provider)
OPENAI_API_KEY=sk-...        # OpenAI API
OLLAMA_API_KEY=...           # Ollama Cloud (if using --llm-mode ollama-cloud)

# Required for PubMed
PUBMED_EMAIL=your@email.com  # NCBI Entrez API requires valid email

# Optional
NCBI_API_KEY=...             # Increases PubMed rate limit (3 → 10 req/sec)
ONCOKB_API_KEY=...           # OncoKB API for molecular classification
CROSSREF_EMAIL=...           # CrossRef API (falls back to PUBMED_EMAIL)
```

The following step is mandatory as we calculate the embeddings ALWAYS locally.

For default mode local Ollama embeddings and `--llm-mode ollama-local`:
Download Ollama from [ollama.com](https://ollama.com/download) and run it, then:

```bash
ollama pull embeddinggemma:300m             # Pull required models
```

### Optional: COSMIC Data (for hotspot classification)

For enhanced molecular variant classification, download COSMIC data:

1. Register at [COSMIC](https://cancer.sanger.ac.uk/cosmic/register)
2. Download from [COSMIC Downloads](https://cancer.sanger.ac.uk/cosmic/download):
   - File: **Cosmic_CompleteTargetedScreensMutant_v103_GRCh38.tsv** (~7GB)
3. Place in `data/cosmic/`:

```bash
mkdir -p data/cosmic
mv ~/Downloads/Cosmic_CompleteTargetedScreensMutant_v103_GRCh38.tsv data/cosmic/
```

Without this file, hotspot criteria will use the cancerhotspots.org API only.

### 2. CLI (run first to process data)

```bash
python build_kb.py              # Build knowledge base
python process_query_input.py   # Extract queries
python agent.py                 # Run agent
```

### 3. Backend

```bash
cd backend && python main.py
```

### 4. Frontend

```bash
cd frontend && npm install && npm run dev
```

## Data Structure

```
kb_input/
└── tumorboards/
    └── *.docx          ← Clinical Case Memory cases

query_input/
└── *.docx              ← Query cases to process

results/
└── agent_decisions/
    └── *.json          ← Generated decisions (output)
```

## Disclaimer

This software is provided as proof-of-concept for **research purposes only** and is not intended for clinical use.

- We do not ship non-public data (flowcharts, COSMIC data) and offer a prebuilt UI for demonstration (frontend/dist/)
- All patient documents must be de-identified before processing online
- Generated clinical decisions require validation by qualified medical professionals
- Not approved for production clinical decision-making
- Users are responsible for ensuring compliance with local regulations and institutional policies
