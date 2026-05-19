"""
HemaGuide: Precision Hematology Agent

A clinical decision support framework for German-language tumor boards.
Model-agnostic (OpenAI, Ollama, open-weights). Conditional mode selection
across 3 decision modes: GUIDELINE (Onkopedia flowchart), ADVANCED
(case + literature synthesis), MOLECULAR (Horak et al. 2022 SOP).
"""

# Extraction
from .extraction import (
    read_docx,
    read_document,
    extract_document,
    extract_document_cached,
    build_extraction_prompt,
    generate_document_id
)

# Vector DB (SA-RAG)
from .vectordb import (
    build_tumorboard_kb,
    retrieve_similar_cases,
    collection_exists,
    clear_collection,
    get_collection_count
)

# Core Decision
from .decision import (
    generate_decision,
    generate_plain_decision,
    generate_context_decision,
    build_decision_prompt,
    load_decision_prompts
)

# Utils
from .utils import (
    setup_logging,
    load_json,
    save_json,
    save_prompt,
    load_prompts,
    find_files,
    get_cache_path,
    validate_query_extractions,
    extract_patient_id,
    format_prior_treatments,
    log_result,
    process_items_batch,
    wrap_log_message,
    LOG_MSG_WIDTH,
    LOG_MAX_LINES,
    TREE_BRANCH,
    TREE_LAST,
    TREE_CONT,
)

# PubMed
from .pubmed import PubMedRetriever, translate_diagnosis_to_english

# Crossref (conference literature: ASH, ASCO, EHA)
from .crossref import CrossrefRetriever, TARGET_JOURNALS as CROSSREF_JOURNALS

# Agent Tools
from .tools import (
    TOOLS,
    load_flowchart,
    execute_tool
)

# LLM Client Factory
from .llm import (
    create_client,
    is_ollama_mode,
    is_ollama_client,
    is_ollama_cloud,
    OLLAMA_LOCAL_URL,
    OLLAMA_CLOUD_URL
)

# Enrichment
from .enrichment import (
    is_enriched,
    enrich_document,
    enrich_similar_cases,
    ENRICHED_DATA_DIR
)

# Population Data (gnomAD + HGVS translation)
from .mol.population import (
    translate_hgvs,
    check_population_criteria,
    get_population_data,
    POINTS as POPULATION_POINTS
)

# Hotspot Data (cancerhotspots.org)
from .mol.hotspots import (
    check_hotspot_criteria,
    parse_aa_position,
    HOTSPOT_POINTS
)

# COSMIC Data (local TSV)
from .mol.cosmic import (
    get_cosmic_counts,
    load_cosmic_index
)

# Computational Evidence (MyVariant.info / dbNSFP)
from .mol.computational import (
    check_computational_criteria,
    POINTS as COMPUTATIONAL_POINTS
)

# Variant Type Detection (OVS1, OM2)
from .mol.variant_type import (
    parse_aa_change_extended,
    check_ovs1_criteria,
    check_om2_criteria,
    load_gene_classification,
    POINTS as VARIANT_TYPE_POINTS
)

# Protein Domain Lookup (OM1)
from .mol.domains import (
    check_om1_criteria,
    POINTS as DOMAIN_POINTS
)

# Functional Evidence (OS2)
from .mol.functional import (
    check_os2_criteria,
    POINTS as FUNCTIONAL_POINTS
)

# Cytogenetics (FISH risk classification)
from .mol.cytogenetics import (
    classify_fish_risk,
    MYELOMA_HIGH_RISK_ABERRATIONS,
)

__all__ = [
    # Extraction
    'read_docx',
    'read_document',
    'extract_document',
    'extract_document_cached',
    'build_extraction_prompt',
    'generate_document_id',
    # Vector DB (SA-RAG)
    'build_tumorboard_kb',
    'retrieve_similar_cases',
    'collection_exists',
    'clear_collection',
    'get_collection_count',
    # Core Decision
    'generate_decision',
    'generate_plain_decision',
    'generate_context_decision',
    'build_decision_prompt',
    'load_decision_prompts',
    # Utils
    'setup_logging',
    'load_json',
    'save_json',
    'save_prompt',
    'load_prompts',
    'find_files',
    'get_cache_path',
    'validate_query_extractions',
    'extract_patient_id',
    'format_prior_treatments',
    'log_result',
    'process_items_batch',
    'wrap_log_message',
    'LOG_MSG_WIDTH',
    'LOG_MAX_LINES',
    'TREE_BRANCH',
    'TREE_LAST',
    'TREE_CONT',
    # PubMed
    'PubMedRetriever',
    'translate_diagnosis_to_english',
    # Crossref (conference literature: ASH, ASCO, EHA)
    'CrossrefRetriever',
    'CROSSREF_JOURNALS',
    # Agent Tools
    'TOOLS',
    'load_flowchart',
    'execute_tool',
    # LLM Client Factory
    'create_client',
    'is_ollama_mode',
    'is_ollama_client',
    'is_ollama_cloud',
    'OLLAMA_LOCAL_URL',
    'OLLAMA_CLOUD_URL',
    # Enrichment
    'is_enriched',
    'enrich_document',
    'enrich_similar_cases',
    'ENRICHED_DATA_DIR',
    # Population Data (gnomAD + HGVS translation)
    'translate_hgvs',
    'check_population_criteria',
    'get_population_data',
    'POPULATION_POINTS',
    # Hotspot Data (cancerhotspots.org)
    'check_hotspot_criteria',
    'parse_aa_position',
    'HOTSPOT_POINTS',
    # COSMIC Data (local TSV)
    'get_cosmic_counts',
    'load_cosmic_index',
    # Computational Evidence (MyVariant.info / dbNSFP)
    'check_computational_criteria',
    'COMPUTATIONAL_POINTS',
    # Variant Type Detection (OVS1, OM2)
    'parse_aa_change_extended',
    'check_ovs1_criteria',
    'check_om2_criteria',
    'load_gene_classification',
    'VARIANT_TYPE_POINTS',
    # Protein Domain Lookup (OM1)
    'check_om1_criteria',
    'DOMAIN_POINTS',
    # Functional Evidence (OS2)
    'check_os2_criteria',
    'FUNCTIONAL_POINTS',
    # Cytogenetics (FISH risk)
    'classify_fish_risk',
    'MYELOMA_HIGH_RISK_ABERRATIONS',
]
