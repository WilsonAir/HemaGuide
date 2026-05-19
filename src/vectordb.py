"""
Section-Aware Retrieval-Augmented Generation.

Architecture:
    Document → Section Decomposition → Embeddings → ChromaDB → Retrieval

Key Design Choices:
    - Section-level embeddings: Improves retrieval precision by matching at clinical segment boundaries
    - Entity-specific filtering: Constrains retrieval to relevant disease types
"""

import json
import os
import re
import logging
from pathlib import Path
from typing import List, Dict

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Batch processing for large KB builds
DEFAULT_BATCH_SIZE = 500


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    'build_tumorboard_kb',
    'retrieve_similar_cases',
    'retrieve_gene_matched_cases',
    'collection_exists',
    'clear_collection',
    'get_collection_count',
]


# ============================================================================
# PUBLIC API
# ============================================================================

def build_tumorboard_kb(
    documents: List[Dict],
    db_path: Path,
    collection_name: str = "tumorboards",
    sections: List[str] = None,
    max_section_chars: int = 6000,
    embedding_model: str = "embeddinggemma:300m",
    api_key: str = None,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> None:
    """
    Build section-aware knowledge base from extracted tumor board documents.

    Each document is decomposed into clinical sections, embedded independently,
    and stored in ChromaDB for fine-grained retrieval.

    Args:
        documents: Extracted documents with 'sections' dict and 'document_id'
        db_path: ChromaDB persistence directory
        collection_name: Target collection name
        sections: Sections to index (default: all clinical sections)
        max_section_chars: Truncation threshold per section
        embedding_model: Model identifier for embeddings
        api_key: API key or 'ollama' for local inference
        batch_size: Records per ChromaDB batch (default: 500)
    """
    if sections is None:
        sections = ['age', 'ECOG', 'main_diagnosis', 'secondary_diagnoses',
                    'predictive_factors', 'history', 'question', 'decision',
                    'prior_treatments', 'question_long', 'decision_long',
                    'tumorboard_type']

    logger.info(f"KB build: {len(documents)} documents, model={embedding_model}")

    collection = _get_or_create_collection(db_path, collection_name, embedding_model, api_key)

    all_records = []
    for doc in documents:
        records = _process_document_sections(doc, sections, max_section_chars)
        all_records.extend(records)

    if not all_records:
        logger.warning("KB build: no records to add")
        return

    ids = [f"{r['document_id']}_{r['section']}" for r in all_records]
    contents = [r['content'] for r in all_records]
    metadatas = [{k: v for k, v in r.items() if k != 'content'} for r in all_records]

    # Add in batches to avoid timeout on large KBs
    total = len(all_records)
    n_batches = (total + batch_size - 1) // batch_size
    for i in range(n_batches):
        start, end = i * batch_size, min((i + 1) * batch_size, total)
        collection.add(ids=ids[start:end], documents=contents[start:end], metadatas=metadatas[start:end])
        logger.info(f"KB build: batch {i+1}/{n_batches} ({end - start} records)")

    logger.info(f"KB build: added {total} records to {collection_name}")


def retrieve_similar_cases(
    query_document: Dict,
    db_path: Path,
    collection_name: str = "tumorboards",
    sections: List[str] = None,
    embedding_model: str = None,
    api_key: str = None,
    n_results: int = 3,
    similarity_threshold: float = 0.7,
    entity_slug: str = None
) -> List[Dict]:
    """
    Retrieve similar cases via section-independent similarity aggregation.

    Queries each section independently and aggregates similarity scores across
    sections, enabling multi-dimensional matching (e.g., similar history AND
    similar diagnosis).

    Args:
        query_document: Query document with 'sections' dict
        db_path: ChromaDB persistence directory
        collection_name: Source collection name
        sections: Sections to compare (default: ['history'])
        embedding_model: Model identifier (required)
        api_key: API key or 'ollama' for local inference
        n_results: Maximum cases to return
        similarity_threshold: Minimum average similarity (0-1)
        entity_slug: Optional entity filter (e.g., 'myeloma', 'aml')

    Returns:
        Ranked list of similar cases with similarity scores and full sections
    """
    if embedding_model is None:
        raise ValueError("embedding_model parameter is required")

    if sections is None:
        sections = ['history']

    # Initialize embedding function
    if api_key == "ollama":
        embedding_function = embedding_functions.OllamaEmbeddingFunction(
            model_name=embedding_model,
            url="http://localhost:11434"
        )
    else:
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key or OPENAI_API_KEY,
            model_name=embedding_model
        )

    try:
        client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
        collection = client.get_collection(collection_name, embedding_function=embedding_function)
    except Exception as e:
        logger.warning(f"Knowledge base not available: {e}")
        return []

    query_sections = query_document.get('sections', {})
    query_doc_id = query_document.get('document_id')
    query_patient_id = query_document.get('patient_id', '')

    # Aggregate scores across sections
    document_scores = {}

    for section in sections:
        section_content = query_sections.get(section, '')
        if not section_content.strip():
            continue

        where_clause = (
            {"$and": [{"section": section}, {"entity_slug": entity_slug}]}
            if entity_slug else {"section": section}
        )

        results = collection.query(
            query_texts=[section_content],
            where=where_clause,
            n_results=n_results
        )

        for i, metadata in enumerate(results['metadatas'][0]):
            doc_id = metadata['document_id']

            # Exclude self and same patient
            if query_doc_id and doc_id == query_doc_id:
                continue
            result_patient_id = metadata.get('patient_id', '')
            if query_patient_id and result_patient_id and query_patient_id == result_patient_id:
                continue

            similarity = 1 - results['distances'][0][i]

            if doc_id not in document_scores:
                document_scores[doc_id] = {'total_score': 0, 'metadata': metadata, 'section_scores': {}}

            document_scores[doc_id]['total_score'] += similarity
            document_scores[doc_id]['section_scores'][section] = round(similarity, 3)

    # Rank by average similarity
    ranked_cases = []
    for doc_id, data in document_scores.items():
        avg_similarity = data['total_score'] / len(sections)
        if avg_similarity < similarity_threshold:
            continue

        metadata = data['metadata']
        ranked_cases.append({
            'document_id': doc_id,
            'similarity_score': round(avg_similarity, 3),
            'entity_slug': metadata.get('entity_slug', 'unknown'),
            'section_similarities': data['section_scores'],
            'source_file': metadata.get('source_file', 'unknown'),
            'patient_id': metadata.get('patient_id', ''),
            'sections': {
                'age': metadata.get('age', ''),
                'ECOG': metadata.get('ECOG', ''),
                'main_diagnosis': metadata.get('main_diagnosis', ''),
                'secondary_diagnoses': metadata.get('secondary_diagnoses', ''),
                'predictive_factors': metadata.get('predictive_factors', ''),
                'history': metadata.get('history', ''),
                'question': metadata.get('question', ''),
                'decision': metadata.get('decision', ''),
                'prior_treatments': metadata.get('prior_treatments', ''),
                'question_long': metadata.get('question_long', ''),
                'decision_long': metadata.get('decision_long', ''),
                'tumorboard_type': metadata.get('tumorboard_type', '')
            }
        })

    ranked_cases.sort(key=lambda x: x['similarity_score'], reverse=True)
    results = ranked_cases[:n_results]
    # Logging handled by caller (tools.py) to avoid duplication
    return results


def retrieve_gene_matched_cases(
    genes: List[str],
    kb_path: Path,
    n_results: int = 3
) -> List[Dict]:
    """Retrieve KB cases containing specified genes via word matching.

    Args:
        genes: Gene symbols to match (e.g., ['NRAS', 'TP53'])
        kb_path: Path to KB JSON files
        n_results: Max cases to return

    Returns:
        List of matched case documents, ranked by gene match count
    """
    if not genes:
        return []

    matches = []
    pattern = re.compile(r'\b(' + '|'.join(re.escape(g) for g in genes) + r')\b', re.I)

    try:
        for f in kb_path.glob('*.json'):
            doc = json.load(open(f))
            analysis = doc.get('sections', {}).get('mol_info', '')
            found = pattern.findall(analysis)
            if found:
                matches.append({'doc': doc, 'genes': list(set(found)), 'count': len(set(found))})
    except Exception as e:
        logger.warning(f"Gene-matched case retrieval failed: {e}")
        return []

    matches.sort(key=lambda x: x['count'], reverse=True)
    return [m['doc'] for m in matches[:n_results]]


# ============================================================================
# COLLECTION UTILITIES
# ============================================================================

def collection_exists(db_path: Path, collection_name: str) -> bool:
    """Check if collection exists and contains documents."""
    try:
        client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
        return client.get_collection(collection_name).count() > 0
    except Exception:
        return False


def clear_collection(db_path: Path, collection_name: str) -> None:
    """Remove all documents from collection."""
    try:
        client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
        collection = client.get_collection(collection_name)
        results = collection.get()
        if results['ids']:
            collection.delete(ids=results['ids'])
    except Exception:
        pass


def get_collection_count(db_path: Path, collection_name: str) -> int:
    """Return document count in collection (0 if non-existent)."""
    try:
        client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
        return client.get_collection(collection_name).count()
    except Exception:
        return 0


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _truncate_section(content: str, max_chars: int = 6000) -> str:
    """Truncate long sections, preserving start and end context."""
    if len(content) <= max_chars:
        return content

    keep_start = int(max_chars * 0.5)
    keep_end = max_chars - keep_start
    return f"{content[:keep_start]}\n\n[...TRUNCATED...]\n\n{content[-keep_end:]}"


def _process_document_sections(
    document: Dict,
    sections: List[str],
    max_section_chars: int = 6000
) -> List[Dict]:
    """Transform document into section records for vector storage."""
    records = []
    doc_sections = document.get('sections', {})

    for section_name in sections:
        content = doc_sections.get(section_name, '')
        if not content or content.strip() in ['nicht vorhanden', 'Keine', '']:
            continue

        content = _truncate_section(content, max_section_chars)

        record = {
            'document_id': document['document_id'],
            'section': section_name,
            'content': content,
            'source_file': document.get('source_file', 'unknown'),
            'patient_id': document.get('patient_id', ''),
            'entity_slug': document.get('entity_slug', 'unknown'),
            'age': doc_sections.get('age', ''),
            'ECOG': doc_sections.get('ECOG', ''),
            'main_diagnosis': doc_sections.get('main_diagnosis', ''),
            'secondary_diagnoses': doc_sections.get('secondary_diagnoses', ''),
            'predictive_factors': doc_sections.get('predictive_factors', ''),
            'history': doc_sections.get('history', ''),
            'question': doc_sections.get('question', ''),
            'decision': doc_sections.get('decision', ''),
            'prior_treatments': doc_sections.get('prior_treatments', ''),
            'question_long': doc_sections.get('question_long', ''),
            'decision_long': doc_sections.get('decision_long', ''),
            'tumorboard_type': doc_sections.get('tumorboard_type', '')
        }
        records.append(record)

    return records


def _get_or_create_collection(
    db_path: Path,
    collection_name: str,
    embedding_model: str = "embeddinggemma:300m",
    api_key: str = None
):
    """Initialize ChromaDB collection with specified embedding function."""
    client = chromadb.PersistentClient(
        path=str(db_path),
        settings=Settings(anonymized_telemetry=False)
    )

    if api_key == 'ollama':
        embedding_function = embedding_functions.OllamaEmbeddingFunction(
            url="http://localhost:11434",
            model_name=embedding_model
        )
    else:
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key or OPENAI_API_KEY,
            model_name=embedding_model
        )

    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={"embedding_model": embedding_model, "hnsw:space": "cosine"}
    )
