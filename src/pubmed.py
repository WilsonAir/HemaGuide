"""
PubMed Retriever Module

Searches PubMed using Entrez API and retrieves article abstracts.
Filters for recent clinical trials, systematic reviews, and meta-analyses.
"""

import json
import os
import time
import logging
from typing import List, Dict, Any
import re
from datetime import datetime, timedelta
from Bio import Entrez

logger = logging.getLogger(__name__)

# Entity to MeSH term mapping for PubMed queries
ENTITY_MESH_MAP = {
    # Myeloma / plasma cell entities
    "Multiple Myeloma (MM)": '"Multiple Myeloma"[MeSH]',
    "Smoldering Multiple Myeloma (SMM)": '"Multiple Myeloma"[MeSH]',
    "Monoclonal Gammopathy of Undetermined Significance (MGUS)": '"Monoclonal Gammopathy of Undetermined Significance"[MeSH]',
    "Monoclonal Gammopathy of Renal Significance (MGRS)": '"Paraproteinemias"[MeSH]',
    "Primary AL Amyloidosis": '"Immunoglobulin Light-chain Amyloidosis"[MeSH]',
    "ATTR Amyloidosis": '"Amyloid Neuropathies, Familial"[MeSH]',
    "Waldenström Macroglobulinemia": '"Waldenstrom Macroglobulinemia"[MeSH]',
    "Heavy Chain Diseases": '"Heavy Chain Disease"[MeSH]',

    # AML entities
    "Acute Myeloid Leukemia (AML)": '"Leukemia, Myeloid, Acute"[MeSH]',
    "Acute Promyelocytic Leukemia (APL)": '"Leukemia, Promyelocytic, Acute"[MeSH]',

    # MDS / MPN entities
    "Myelodysplastic Syndromes (MDS)": '"Myelodysplastic Syndromes"[MeSH]',
    "Polycythemia Vera (PV)": '"Polycythemia Vera"[MeSH]',
    "Essential Thrombocythemia (ET)": '"Thrombocythemia, Essential"[MeSH]',
    "Primary Myelofibrosis (PMF)": '"Primary Myelofibrosis"[MeSH]',
    "Chronic Myeloid Leukemia (CML)": '"Leukemia, Myelogenous, Chronic, BCR-ABL Positive"[MeSH]',
    "Chronic Neutrophilic Leukemia (CNL)": '"Leukemia, Neutrophilic, Chronic"[MeSH]',
    "Chronic Eosinophilic Leukemia (CEL)": '"Hypereosinophilic Syndrome"[MeSH]',
    "Chronic Myelomonocytic Leukemia (CMML)": '"Leukemia, Myelomonocytic, Chronic"[MeSH]',
    "Juvenile Myelomonocytic Leukemia (JMML)": '"Leukemia, Myelomonocytic, Juvenile"[MeSH]',
    "MDS/MPN with ring sideroblasts and thrombocytosis (MDS/MPN-RS-T)": '"Myelodysplastic-Myeloproliferative Diseases"[MeSH]',
    "Myeloid/lymphoid neoplasms with eosinophilia (PDGFRA/B, FGFR1, JAK2 rearrangements)": '"Myeloproliferative Disorders"[MeSH]',
    "Myeloid Sarcoma": '"Sarcoma, Myeloid"[MeSH]',
    "Blastic Plasmacytoid Dendritic Cell Neoplasm (BPDCN)": '"Hematologic Neoplasms"[MeSH]',

    # ALL entities
    "B-cell Acute Lymphoblastic Leukemia (B-ALL)": '"Precursor B-Cell Lymphoblastic Leukemia-Lymphoma"[MeSH]',
    "T-cell Acute Lymphoblastic Leukemia (T-ALL)": '"Precursor T-Cell Lymphoblastic Leukemia-Lymphoma"[MeSH]',
    "Early T-cell Precursor ALL (ETP-ALL)": '"Precursor T-Cell Lymphoblastic Leukemia-Lymphoma"[MeSH]',
    "Mixed Phenotype Acute Leukemia (MPAL)": '"Leukemia, Biphenotypic, Acute"[MeSH]',

    # CLL / B-cell leukemia entities
    "Chronic Lymphocytic Leukemia (CLL) / Small Lymphocytic Lymphoma (SLL)": '"Leukemia, Lymphocytic, Chronic, B-Cell"[MeSH]',
    "B-cell Prolymphocytic Leukemia (B-PLL)": '"Leukemia, Prolymphocytic, B-Cell"[MeSH]',
    "Hairy Cell Leukemia (HCL)": '"Leukemia, Hairy Cell"[MeSH]',

    # B-cell lymphoma entities
    "Diffuse Large B-cell Lymphoma (DLBCL)": '"Lymphoma, Large B-Cell, Diffuse"[MeSH]',
    "High-grade B-cell lymphoma (Double-Hit/Triple-Hit)": '"Lymphoma, Large B-Cell, Diffuse"[MeSH]',
    "Primary Mediastinal B-cell Lymphoma (PMBL)": '"Lymphoma, Large B-Cell, Diffuse"[MeSH]',
    "Burkitt Lymphoma": '"Burkitt Lymphoma"[MeSH]',
    "Primary CNS Lymphoma (PCNSL)": '"Lymphoma, Non-Hodgkin"[MeSH]',
    "Lymphomatoid Granulomatosis (LYG)": '"Lymphomatoid Granulomatosis"[MeSH]',
    "Follicular Lymphoma (FL)": '"Lymphoma, Follicular"[MeSH]',
    "Mantle Cell Lymphoma (MCL)": '"Lymphoma, Mantle-Cell"[MeSH]',
    "Marginal Zone Lymphomas (MALT, Splenic, Nodal)": '"Lymphoma, B-Cell, Marginal Zone"[MeSH]',

    # T-cell / NK-cell lymphoma entities
    "Mature T-cell & NK-cell Lymphomas": '"Lymphoma, T-Cell"[MeSH]',
    "Peripheral T-cell Lymphoma (PTCL, NOS)": '"Lymphoma, T-Cell, Peripheral"[MeSH]',
    "Angioimmunoblastic T-cell Lymphoma (AITL)": '"Immunoblastic Lymphadenopathy"[MeSH]',
    "Anaplastic Large Cell Lymphoma (ALCL, ALK+/-)": '"Lymphoma, Large-Cell, Anaplastic"[MeSH]',
    "Hepatosplenic T-cell Lymphoma": '"Lymphoma, T-Cell"[MeSH]',
    "Extranodal NK/T-cell Lymphoma, nasal type": '"Lymphoma, Extranodal NK-T-Cell"[MeSH]',
    "Mycosis Fungoides / Sézary Syndrome": '"Mycosis Fungoides"[MeSH]',
    "T-cell Large Granular Lymphocytic Leukemia (T-LGL)": '"Leukemia, Large Granular Lymphocytic"[MeSH]',
    "T-cell Prolymphocytic Leukemia (T-PLL)": '"Leukemia, Prolymphocytic, T-Cell"[MeSH]',

    # Hodgkin lymphoma entities
    "Hodgkin Lymphoma (HL)": '"Hodgkin Disease"[MeSH]',
    "Classical Hodgkin Lymphoma": '"Hodgkin Disease"[MeSH]',
    "Nodular Lymphocyte-Predominant Hodgkin Lymphoma (NLPHL)": '"Hodgkin Disease"[MeSH]',

    # Pre-malignant / clonal entities
    "Clonal Hematopoiesis of Indeterminate Potential (CHIP)": '"Clonal Hematopoiesis"[MeSH]',
    "Clonal Cytopenia of Undetermined Significance (CCUS)": '"Clonal Hematopoiesis"[MeSH]',
    "Monoclonal B-cell Lymphocytosis (MBL)": '"Lymphocytosis"[MeSH]',

    # Histiocytic / rare entities
    "Histiocytic Neoplasms (Langerhans Cell Histiocytosis, Erdheim-Chester Disease, Rosai-Dorfman)": '"Histiocytosis, Langerhans-Cell"[MeSH]',
    "Castleman Disease (Unicentric, Idiopathic Multicentric, HHV-8-associated)": '"Castleman Disease"[MeSH]',
    "Post-Transplant Lymphoproliferative Disorder (PTLD)": '"Lymphoproliferative Disorders"[MeSH]',
    "Hemophagocytic Lymphohistiocytosis (HLH, malignant forms)": '"Lymphohistiocytosis, Hemophagocytic"[MeSH]',
    "Systemic Mastocytosis": '"Mastocytosis, Systemic"[MeSH]',

    # Cytopenias / autoimmune
    "Immune Thrombocytopenia (ITP)": '"Purpura, Thrombocytopenic, Idiopathic"[MeSH]',
    "Autoimmune Hemolytic Anemia (AIHA)": '"Anemia, Hemolytic, Autoimmune"[MeSH]',

    # Hemoglobinopathies / red cell disorders
    "Thalassemia": '"Thalassemia"[MeSH]',
    "Sickle Cell Disease (SCD)": '"Anemia, Sickle Cell"[MeSH]',
    "Hereditary Spherocytosis": '"Spherocytosis, Hereditary"[MeSH]',

    # Coagulation disorders
    "Hemophilia": '"Hemophilia A"[MeSH]',

    # Immunodeficiency
    "Common Variable Immunodeficiency (CVID)": '"Common Variable Immunodeficiency"[MeSH]',
    "IgG4-Related Disease (IgG4-RD)": '"Immunoglobulin G4-Related Disease"[MeSH]',
}


class PubMedRetriever:
    """
    Retrieves medical literature from PubMed using NCBI Entrez API.

    Implements rate limiting, error handling, and filtering for high-quality
    clinical evidence (trials, reviews, meta-analyses).
    """

    def __init__(self):
        """
        Initialize PubMed retriever with NCBI credentials.

        Requires:
            - PUBMED_EMAIL environment variable (mandatory for NCBI)
            - NCBI_API_KEY environment variable (optional, for higher rate limits)
        """
        self.email = os.getenv("PUBMED_EMAIL")
        if not self.email:
            raise ValueError(
                "PUBMED_EMAIL environment variable is required for NCBI Entrez API access. "
                "Set it in your .env file."
            )

        Entrez.email = self.email

        api_key = os.getenv("NCBI_API_KEY")
        if api_key and api_key != "your_ncbi_api_key_here":
            Entrez.api_key = api_key
            self.rate_limit = 0.1  # 10 requests/second with API key
        else:
            self.rate_limit = 0.34  # ~3 requests/second without API key

    def _build_search_query(
        self,
        base_query: str,
        article_types: List[str] = None
    ) -> str:
        """Build PubMed search query with publication type filter.

        Note: Date filtering is handled via mindate/maxdate parameters in search().
        """
        if article_types is None:
            article_types = [
                "Clinical Trial",
                "Meta-Analysis",
                "Systematic Review",
                "Randomized Controlled Trial"
            ]

        # Publication type filter - use lowercase for reliability
        type_filter = " OR ".join([f'{ptype.lower()}[pt]' for ptype in article_types])

        return f"({base_query}) AND ({type_filter})"

    def search(self, query: str, max_results: int = 10, years_back: int = 5) -> List[str]:
        """Search PubMed and return list of PMIDs."""
        full_query = self._build_search_query(query)

        # Calculate date range for filtering
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years_back)

        try:
            time.sleep(self.rate_limit)
            handle = Entrez.esearch(
                db="pubmed",
                term=full_query,
                retmax=max_results,
                sort="relevance",
                mindate=start_date.strftime("%Y/%m/%d"),
                maxdate=end_date.strftime("%Y/%m/%d"),
                datetype="pdat"  # Publication date
            )

            record = Entrez.read(handle)
            handle.close()

            return record.get("IdList", [])
        except Exception as e:
            logger.warning(f"PubMed: search error - {e}")
            return []

    def fetch_abstracts(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch detailed article information including abstracts."""
        if not pmids:
            return []

        articles = []
        batch_size = 10

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]

            try:
                time.sleep(self.rate_limit)
                handle = Entrez.efetch(
                    db="pubmed",
                    id=batch,
                    rettype="abstract",
                    retmode="xml"
                )

                records = Entrez.read(handle)
                handle.close()

                for article_data in records.get("PubmedArticle", []):
                    article = self._parse_article(article_data)
                    if article:
                        articles.append(article)
            except Exception as e:
                logger.warning(f"PubMed: fetch error for batch {i//batch_size + 1} - {e}")
                continue

        return articles

    def _parse_article(self, article_data: Dict) -> Dict[str, Any]:
        """Parse PubMed XML article data into structured dictionary.

        Returns partial data with defaults if individual fields fail to parse.
        """
        result = {
            "pmid": "",
            "title": "",
            "authors": "",
            "journal": "",
            "year": "",
            "abstract": "",
            "publication_types": []
        }

        try:
            medline = article_data.get("MedlineCitation", {})
            article = medline.get("Article", {})

            result["pmid"] = str(medline.get("PMID", ""))
            result["title"] = article.get("ArticleTitle", "")

            # Extract authors (first 3)
            try:
                author_list = article.get("AuthorList", [])
                authors = []
                for author in author_list[:3]:
                    last_name = author.get("LastName", "")
                    initials = author.get("Initials", "")
                    if last_name:
                        authors.append(f"{last_name} {initials}".strip())
                if len(author_list) > 3:
                    authors.append("et al.")
                result["authors"] = ", ".join(authors)
            except Exception as e:
                logger.debug(f"PubMed: author parse error for PMID {result['pmid']} - {e}")

            # Extract journal and year
            try:
                journal = article.get("Journal", {})
                result["journal"] = journal.get("Title", "")
                pub_date = journal.get("JournalIssue", {}).get("PubDate", {})
                year = pub_date.get("Year", "")
                # Fallback: extract year from MedlineDate (e.g., "2020 Jan-Feb")
                if not year:
                    medline_date = pub_date.get("MedlineDate", "")
                    if medline_date:
                        year = medline_date.split()[0] if medline_date.split() else ""
                result["year"] = year
            except Exception as e:
                logger.debug(f"PubMed: journal/year parse error for PMID {result['pmid']} - {e}")

            # Extract abstract
            try:
                abstract_data = article.get("Abstract", {})
                abstract_texts = abstract_data.get("AbstractText", [])
                if isinstance(abstract_texts, list):
                    result["abstract"] = " ".join([str(text) for text in abstract_texts])
                else:
                    result["abstract"] = str(abstract_texts)
            except Exception as e:
                logger.debug(f"PubMed: abstract parse error for PMID {result['pmid']} - {e}")

            # Extract publication types
            try:
                pub_type_list = article.get("PublicationTypeList", [])
                result["publication_types"] = [str(pt) for pt in pub_type_list]
            except Exception as e:
                logger.debug(f"PubMed: pub_types parse error for PMID {result['pmid']} - {e}")

            # Only return None if we have no PMID (critical identifier)
            if not result["pmid"]:
                logger.warning("PubMed: article parse error - no PMID found")
                return None

            return result

        except Exception as e:
            logger.warning(f"PubMed: article parse error - {e}")
            return None

    def retrieve(self, query: str, max_results: int = 5, years_back: int = 10) -> List[Dict[str, Any]]:
        """
        Complete retrieval: search and fetch abstracts.

        If the primary search (10 years) returns no results, falls back to
        the same query with extended time window (15 years).

        Args:
            query: Search query string
            max_results: Maximum number of articles to retrieve
            years_back: Number of years to look back

        Returns:
            List of article dictionaries with full metadata and abstracts
        """
        # Primary search
        pmids = self.search(query, max_results, years_back)

        # Fallback: extended time window (15 years)
        if not pmids:
            pmids = self.search(query, max_results, 15)

        if not pmids:
            return []

        articles = self.fetch_abstracts(pmids)
        # Logging handled by caller (tools.py) to avoid duplication
        return articles


def build_molecular_query(gene: str, aa_change: str = None, entity: str = None) -> str:
    """Build PubMed query for gene+mutation therapy.

    Args:
        gene: Gene symbol (e.g., "BRAF", "FLT3")
        aa_change: Amino acid change (optional, not currently used in query)
        entity: Full entity name from case (e.g., "Acute Myeloid Leukemia (AML)")

    Returns:
        PubMed query string with appropriate MeSH term for the entity
    """
    query_parts = [f'"{gene}"[tiab]']
    if entity and entity in ENTITY_MESH_MAP:
        query_parts.append(ENTITY_MESH_MAP[entity])
    query_parts.append('("therapy"[tiab] OR "treatment"[tiab])')
    return ' AND '.join(query_parts)


def build_pubmed_query(case: Dict[str, Any]) -> str:
    """Build PubMed query from structured case data. No LLM needed.

    Constructs a deterministic query using:
    1. Entity MeSH term from entity field
    2. Disease state (relapsed/refractory vs treatment)
    3. Key actionable gene if present

    Args:
        case: Case dictionary with 'sections' containing extracted data

    Returns:
        PubMed query string ready for search
    """
    sections = case.get('sections', {})
    parts = []

    # 1. Entity MeSH term from entity field
    entity_name = sections.get('entity', '').lower()
    mesh_term = None
    for entity, mesh in ENTITY_MESH_MAP.items():
        if entity.lower() in entity_name or entity_name in entity.lower():
            mesh_term = mesh
            break

    if mesh_term:
        parts.append(mesh_term)
    else:
        # Fallback: main diagnosis as free text
        diagnosis = sections.get('main_diagnosis', 'cancer')
        parts.append(f'{diagnosis}[tiab]')

    # 2. Disease state detection (German + English keywords)
    text = (sections.get('history', '') + ' ' +
            sections.get('question_long', sections.get('question', ''))).lower()
    relapsed_kw = ['relaps', 'rezidiv', 'refraktär', 'refractory', 'progress', 'versagen', 'resistenz']

    if any(kw in text for kw in relapsed_kw):
        parts.append('(relapsed[tiab] OR refractory[tiab])')
    else:
        parts.append('(therapy[tiab] OR treatment[tiab])')

    # 3. Key actionable gene (optional)
    mol_info_raw = sections.get('mol_info', '[]')
    mol_info = []
    if isinstance(mol_info_raw, str) and mol_info_raw not in ('', 'nicht vorhanden'):
        try:
            mol_info = json.loads(mol_info_raw)
        except json.JSONDecodeError:
            pass
    elif isinstance(mol_info_raw, list):
        mol_info = mol_info_raw

    actionable = {
        # AML/Myeloma
        'FLT3', 'IDH1', 'IDH2', 'NPM1', 'BRAF', 'NRAS', 'KRAS', 'TP53', 'EGFR', 'ALK',
        # ALL
        'IKZF1', 'PAX5', 'ETV6', 'RUNX1', 'ABL1', 'JAK2',
        # Lymphomas (DLBCL, FL, MALT)
        'MYC', 'BCL2', 'BCL6', 'PTEN', 'CD79B', 'CREBBP', 'KMT2D', 'EZH2', 'BIRC3', 'MALT1'
    }
    for variant in mol_info[:3]:
        gene = variant.get('gene', '').upper()
        if gene in actionable:
            parts.append(f'{gene}[tiab]')
            break

    return ' AND '.join(parts)


def translate_diagnosis_to_english(
    diagnosis: str,
    model: str,
    llm_mode: str | None,
    api_key: str | None,
) -> str:
    """Translate German diagnosis to English PubMed search term via single LLM call."""
    from .extraction import _call_llm
    messages = [
        {"role": "system", "content": "You are a medical translator. Translate the German diagnosis into a concise English medical term suitable for PubMed search. Return ONLY the English term, nothing else."},
        {"role": "user", "content": diagnosis}
    ]
    try:
        result = _call_llm(messages, model, llm_mode, api_key, temperature=0.0)
        return result.strip()
    except Exception as e:
        logger.warning(f"Diagnosis translation failed: {e}")
        return diagnosis  # fall back to original German text
