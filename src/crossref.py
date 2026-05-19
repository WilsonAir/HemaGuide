"""
Crossref Retriever Module

Searches Crossref API for conference literature from ASH (Blood), ASCO (JCO), and EHA (HemaSphere).
Designed for retrieving hematology/oncology conference proceedings and publications.

Target journals:
- Blood (ISSN: 1528-0020) - ASH Annual Meeting
- Journal of Clinical Oncology (ISSN: 0732-183X) - ASCO Annual Meeting
- HemaSphere (ISSN: 2572-9241) - EHA Congress
"""

import os
import time
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

CROSSREF_API = "https://api.crossref.org/works"

# Target journals for hematology/oncology conference proceedings
TARGET_JOURNALS = {
    "Blood": {"issn": "1528-0020", "conference": "ASH", "aliases": ["blood"]},
    "JCO": {"issn": "0732-183X", "conference": "ASCO", "aliases": ["journal of clinical oncology", "j clin oncol"]},
    "HemaSphere": {"issn": "2572-9241", "conference": "EHA", "aliases": ["hemasphere"]},
}


class CrossrefRetriever:
    """
    Retrieves publications from Crossref API for hematology/oncology conferences.

    Implements rate limiting, error handling, and filtering for high-quality
    clinical evidence from ASH, ASCO, and EHA proceedings.
    """

    def __init__(self, mailto: str = None):
        """
        Initialize Crossref retriever.

        Args:
            mailto: Email for Crossref polite pool (higher rate limits).
                    Falls back to CROSSREF_EMAIL or PUBMED_EMAIL env vars.
        """
        self.mailto = mailto or os.getenv("CROSSREF_EMAIL") or os.getenv("PUBMED_EMAIL")
        # Polite pool: faster rate limit with mailto
        self.rate_limit = 0.05 if self.mailto else 0.1

    def retrieve(
        self,
        query: str,
        journals: List[str] = None,
        max_results: int = 5,
        years_back: int = 5
    ) -> List[Dict]:
        """
        Complete retrieval: search and parse articles.

        If primary search returns no results, falls back to extended time window.

        Args:
            query: Search query string
            journals: List of journal keys to search (default: all target journals)
            max_results: Maximum number of articles to retrieve
            years_back: Number of years to look back

        Returns:
            List of article dictionaries with full metadata
        """
        items = self.search(query, journals, max_results, years_back)

        # Fallback: extended time window (10 years)
        if not items:
            items = self.search(query, journals, max_results, 10)
            if not items:
                return []

        articles = []
        for item in items:
            article = self._parse_article(item)
            if article:
                articles.append(article)

        return articles

    def search(
        self,
        query: str,
        journals: List[str] = None,
        max_results: int = 5,
        years_back: int = 5
    ) -> List[Dict]:
        """
        Search Crossref for publications matching query.

        Args:
            query: Search query string
            journals: List of journal keys to search (default: all target journals)
            max_results: Maximum number of results to return
            years_back: Number of years to look back

        Returns:
            List of Crossref work items (raw API response)
        """
        issn_filter = self._build_issn_filter(journals)
        from_year = datetime.now().year - years_back

        params = {
            "query": query,
            "filter": f"{issn_filter},from-pub-date:{from_year}",
            "rows": max_results,
            "sort": "relevance",
            "select": "DOI,title,author,container-title,published,abstract,is-referenced-by-count"
        }

        try:
            time.sleep(self.rate_limit)
            response = requests.get(
                CROSSREF_API,
                params=params,
                headers=self._build_headers(),
                timeout=30
            )

            if response.status_code != 200:
                logger.warning(f"Crossref: HTTP {response.status_code}")
                return []

            data = response.json()
            items = data.get("message", {}).get("items", [])
            return items

        except requests.exceptions.Timeout:
            logger.warning("Crossref: timeout")
            return []
        except requests.exceptions.RequestException as e:
            logger.warning(f"Crossref: request error - {e}")
            return []
        except Exception as e:
            logger.warning(f"Crossref: unexpected error - {e}")
            return []

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with optional mailto for polite pool."""
        headers = {"Accept": "application/json"}
        if self.mailto:
            headers["User-Agent"] = f"HemaGuide/1.0 (mailto:{self.mailto})"
        return headers

    def _build_issn_filter(self, journals: List[str] = None) -> str:
        """Build ISSN filter for Crossref query.

        Crossref requires 'issn:' prefix for each ISSN in the filter.
        """
        if journals:
            issns = [TARGET_JOURNALS[j]["issn"] for j in journals if j in TARGET_JOURNALS]
        else:
            issns = [j["issn"] for j in TARGET_JOURNALS.values()]
        return ",".join(f"issn:{issn}" for issn in issns)

    def _parse_article(self, item: Dict) -> Optional[Dict]:
        """
        Parse Crossref work item into article dictionary.

        Output format is compatible with PubMed articles for unified processing.

        Returns:
            Article dict with: doi, title, authors, journal, year, abstract,
            citation_count, conference, source
        """
        try:
            doi = item.get("DOI", "")

            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""

            # Extract authors (first 3 + et al.)
            authors_list = item.get("author", [])
            authors = []
            for author in authors_list[:3]:
                family = author.get("family", "")
                given = author.get("given", "")
                if family:
                    initials = "".join([n[0] for n in given.split() if n]) if given else ""
                    authors.append(f"{family} {initials}".strip())
            if len(authors_list) > 3:
                authors.append("et al.")
            authors_str = ", ".join(authors)

            journal_list = item.get("container-title", [])
            journal = journal_list[0] if journal_list else ""

            # Map journal to conference
            conference = ""
            journal_lower = journal.lower() if journal else ""
            for jname, jdata in TARGET_JOURNALS.items():
                if jdata["issn"] in doi:
                    conference = jdata["conference"]
                    break
                for alias in jdata.get("aliases", []):
                    if alias in journal_lower:
                        conference = jdata["conference"]
                        break
                if conference:
                    break

            published = item.get("published", {})
            date_parts = published.get("date-parts", [[]])
            year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""

            abstract = item.get("abstract", "")
            if abstract:
                abstract = re.sub(r'<[^>]+>', '', abstract)
                abstract = abstract.strip()

            citation_count = item.get("is-referenced-by-count", 0)

            if not doi or not title:
                return None

            return {
                "doi": doi,
                "title": title,
                "authors": authors_str,
                "journal": journal,
                "year": year,
                "abstract": abstract,
                "citation_count": citation_count,
                "conference": conference,
                "source": "crossref"
            }

        except Exception as e:
            logger.debug(f"Crossref: article parse error - {e}")
            return None
