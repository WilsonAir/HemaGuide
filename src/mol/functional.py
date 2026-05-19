"""
Functional Evidence Module

Features:
- Query CIViC GraphQL API for functional evidence
- Query OncoKB API for oncogenicity annotations
- Combine evidence from both sources

Criteria:
- OS2 (+4): Well-established in vitro or in vivo functional studies
           supportive of an oncogenic effect of the variant
"""

import logging
import os
from typing import Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

CIVIC_API = "https://civicdb.org/api/graphql"
ONCOKB_API = "https://www.oncokb.org/api/v1"

# OS2
POINTS = {
    'OS2': +4,
}

# CIViC evidence types that count as functional
CIVIC_FUNCTIONAL_TYPES = {'FUNCTIONAL'}

# CIViC directions that support oncogenicity
CIVIC_ONCOGENIC_DIRECTIONS = {'SUPPORTS'}

# CIViC significances indicating oncogenic effect
CIVIC_ONCOGENIC_SIGNIFICANCES = {
    'GAIN_OF_FUNCTION',
    'ONCOGENIC',
    'LIKELY_ONCOGENIC',
    'NEOMORPHIC',
    'DOMINANT_NEGATIVE',
}

# OncoKB oncogenic classifications
ONCOKB_ONCOGENIC = {
    'Oncogenic',
    'Likely Oncogenic',
}

# OncoKB mutation effects indicating functional evidence
ONCOKB_FUNCTIONAL_EFFECTS = {
    'Gain-of-function',
    'Likely Gain-of-function',
    'Loss-of-function',
    'Likely Loss-of-function',
    'Switch-of-function',
    'Likely Switch-of-function',
}


# ============================================================================
# CIVIC API
# ============================================================================

def query_civic(gene: str, aa_change: str) -> Dict:
    """
    Query CIViC GraphQL API for variant evidence.

    Uses two-step query (CIViC schema v2):
    1. browseVariants to find variant IDs by gene and variant name
    2. variant(id:) to get full evidence details

    Args:
        gene: Hugo gene symbol (e.g., "BRAF")
        aa_change: AA change notation (e.g., "p.V600E" or "V600E")

    Returns:
        Dict with 'found', 'has_functional_evidence', 'evidence_items', or 'error'
    """
    variant_name = _normalize_aa_change(aa_change)

    logger.info(f"  │    CIViC: {gene} {variant_name}")

    # Step 1: Find variant IDs using browseVariants
    browse_query = """
    query($gene: String!, $variant: String!) {
      browseVariants(featureName: $gene, variantName: $variant, first: 5) {
        edges {
          node {
            id
            name
            featureName
          }
        }
      }
    }
    """

    # Step 2: Get full variant details by ID
    detail_query = """
    query($id: Int!) {
      variant(id: $id) {
        id
        name
        feature { name }
        molecularProfiles {
          nodes {
            id
            evidenceItems {
              nodes {
                id
                evidenceType
                evidenceDirection
                significance
                status
                description
              }
            }
          }
        }
      }
    }
    """

    try:
        # Step 1: Browse for variant ID
        response = requests.post(
            CIVIC_API,
            json={
                'query': browse_query,
                'variables': {
                    'gene': gene.upper(),
                    'variant': variant_name
                }
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code != 200:
            logger.warning(f"CIViC HTTP {response.status_code}")
            return {'error': f'HTTP {response.status_code}', 'found': False}

        data = response.json()

        if 'errors' in data:
            error_msg = data['errors'][0].get('message', 'GraphQL error')
            logger.warning(f"CIViC error: {error_msg}")
            return {'error': error_msg, 'found': False}

        edges = data.get('data', {}).get('browseVariants', {}).get('edges', [])

        if not edges:
            logger.info(f"  │    CIViC: not found")
            return {'found': False, 'gene': gene, 'variant': variant_name}

        # Find exact match or best match
        variant_id = None
        for edge in edges:
            node = edge.get('node', {})
            if node.get('name', '').upper() == variant_name.upper():
                variant_id = node.get('id')
                break
        # If no exact match, use first result
        if variant_id is None:
            variant_id = edges[0].get('node', {}).get('id')

        if not variant_id:
            return {'found': False, 'gene': gene, 'variant': variant_name}

        # Step 2: Get full variant details
        response = requests.post(
            CIVIC_API,
            json={
                'query': detail_query,
                'variables': {'id': variant_id}
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code != 200:
            logger.warning(f"CIViC HTTP {response.status_code}")
            return {'error': f'HTTP {response.status_code}', 'found': False}

        data = response.json()

        if 'errors' in data:
            error_msg = data['errors'][0].get('message', 'GraphQL error')
            logger.warning(f"CIViC error: {error_msg}")
            return {'error': error_msg, 'found': False}

        variant_data = data.get('data', {}).get('variant')
        if not variant_data:
            return {'found': False, 'gene': gene, 'variant': variant_name}

        # Convert to list format for compatibility with rest of function
        variants = [variant_data]

        # Collect all evidence items
        evidence_items = []
        has_functional_evidence = False
        functional_supports_oncogenic = False

        for v in variants:
            for mp in v.get('molecularProfiles', {}).get('nodes', []):
                for ei in mp.get('evidenceItems', {}).get('nodes', []):
                    if ei.get('status') != 'ACCEPTED':
                        continue  # Only use accepted evidence

                    evidence_type = ei.get('evidenceType', '')
                    direction = ei.get('evidenceDirection', '')
                    significance = ei.get('significance', '')

                    evidence_items.append({
                        'type': evidence_type,
                        'direction': direction,
                        'significance': significance,
                        'description': ei.get('description', '')[:200]
                    })

                    # Check for functional evidence supporting oncogenicity
                    if evidence_type in CIVIC_FUNCTIONAL_TYPES:
                        has_functional_evidence = True
                        if (direction in CIVIC_ONCOGENIC_DIRECTIONS and
                                significance in CIVIC_ONCOGENIC_SIGNIFICANCES):
                            functional_supports_oncogenic = True

        if has_functional_evidence:
            status = "oncogenic" if functional_supports_oncogenic else "neutral"
            logger.info(f"  │    CIViC: {len(evidence_items)} items, functional={status}")
        else:
            logger.info(f"  │    CIViC: {len(evidence_items)} items, no functional evidence")

        return {
            'found': True,
            'gene': gene,
            'variant': variant_name,
            'evidence_items': evidence_items,
            'has_functional_evidence': has_functional_evidence,
            'functional_supports_oncogenic': functional_supports_oncogenic
        }

    except requests.exceptions.RequestException as e:
        logger.warning(f"CIViC request failed: {e}")
        return {'error': str(e), 'found': False}


# ============================================================================
# ONCOKB API
# ============================================================================

def query_oncokb(gene: str, aa_change: str) -> Dict:
    """
    Query OncoKB API for variant annotation.

    Requires ONCOKB_API_KEY environment variable.

    Args:
        gene: Hugo gene symbol (e.g., "BRAF")
        aa_change: AA change notation (e.g., "p.V600E" or "V600E")

    Returns:
        Dict with 'found', 'oncogenic', 'mutation_effect', or 'error'
    """
    api_key = _get_oncokb_token()
    if not api_key:
        logger.info("OncoKB API key not configured (ONCOKB_API_KEY)")
        return {'error': 'No API key', 'found': False}

    alteration = _normalize_aa_change(aa_change)

    logger.info(f"  │    OncoKB: {gene} {alteration}")

    try:
        response = requests.get(
            f"{ONCOKB_API}/annotate/mutations/byProteinChange",
            params={
                'hugoSymbol': gene.upper(),
                'alteration': alteration,
                'referenceGenome': 'GRCh38'
            },
            headers={
                'Authorization': f'Bearer {api_key}',
                'Accept': 'application/json'
            },
            timeout=30
        )

        if response.status_code == 401:
            logger.warning("OncoKB authentication failed")
            return {'error': 'Authentication failed', 'found': False}

        if response.status_code == 404:
            logger.info(f"  │    OncoKB: not found")
            return {'found': False, 'gene': gene, 'variant': alteration}

        if response.status_code != 200:
            logger.warning(f"OncoKB HTTP {response.status_code}")
            return {'error': f'HTTP {response.status_code}', 'found': False}

        data = response.json()

        oncogenic = data.get('oncogenic', '')
        mutation_effect = data.get('mutationEffect', {})
        known_effect = mutation_effect.get('knownEffect', '')
        effect_desc = mutation_effect.get('description', '')

        is_oncogenic = oncogenic in ONCOKB_ONCOGENIC
        has_functional_effect = known_effect in ONCOKB_FUNCTIONAL_EFFECTS

        logger.info(f"  │    OncoKB: {oncogenic}, {known_effect}")

        return {
            'found': True,
            'gene': gene,
            'variant': alteration,
            'oncogenic': oncogenic,
            'is_oncogenic': is_oncogenic,
            'known_effect': known_effect,
            'effect_description': effect_desc[:200] if effect_desc else '',
            'has_functional_effect': has_functional_effect
        }

    except requests.exceptions.RequestException as e:
        logger.warning(f"OncoKB request failed: {e}")
        return {'error': str(e), 'found': False}


# ============================================================================
# COMBINED EVIDENCE
# ============================================================================

def check_functional_evidence(gene: str, aa_change: str) -> Tuple[str, int, str]:
    """
    Check for functional evidence from CIViC and OncoKB.

    Combines evidence from both sources:
    - CIViC: Look for FUNCTIONAL evidence type with oncogenic support
    - OncoKB: Look for oncogenic classification with functional effect

    Args:
        gene: Hugo gene symbol
        aa_change: AA change notation

    Returns:
        Tuple of (criterion_code, points, description)
    """
    if not gene or not aa_change:
        return ('', 0, 'Missing gene or AA change')

    evidence_sources = []
    has_os2_evidence = False

    # Query CIViC
    civic_result = query_civic(gene, aa_change)
    if civic_result.get('functional_supports_oncogenic'):
        evidence_sources.append('CIViC functional')
        has_os2_evidence = True
    elif civic_result.get('has_functional_evidence'):
        evidence_sources.append('CIViC functional (neutral)')

    # Query OncoKB
    oncokb_result = query_oncokb(gene, aa_change)
    if oncokb_result.get('is_oncogenic') and oncokb_result.get('has_functional_effect'):
        evidence_sources.append(f"OncoKB ({oncokb_result.get('oncogenic', 'Oncogenic')})")
        has_os2_evidence = True
    elif oncokb_result.get('is_oncogenic'):
        evidence_sources.append(f"OncoKB ({oncokb_result.get('oncogenic', 'Oncogenic')}, no functional)")

    # Determine result
    if has_os2_evidence:
        source_str = ' + '.join(evidence_sources)
        return ('OS2', POINTS['OS2'], f"Functional evidence: {source_str}")

    if evidence_sources:
        source_str = ' + '.join(evidence_sources)
        return ('', 0, f"Evidence found but not oncogenic functional: {source_str}")

    # Check for errors
    errors = []
    if civic_result.get('error'):
        errors.append(f"CIViC: {civic_result['error']}")
    if oncokb_result.get('error'):
        errors.append(f"OncoKB: {oncokb_result['error']}")

    if errors and not civic_result.get('found') and not oncokb_result.get('found'):
        return ('', 0, f"Lookup errors: {'; '.join(errors)}")

    return ('', 0, 'No functional evidence found')


# ============================================================================
# OS2 CRITERIA
# ============================================================================

def check_os2_criteria(gene: str, aa_change: str) -> Tuple[str, int, str]:
    """
    Check OS2 criterion: Functional studies supportive of oncogenic effect.

    Criteria:
    - Well-established in vitro or in vivo functional studies
    - If OS1 is applicable, this rule can be used only if functional studies
      are based on the particular nucleotide change

    Args:
        gene: Gene symbol
        aa_change: AA change notation

    Returns:
        Tuple of (criterion_code, points, description)
    """
    return check_functional_evidence(gene, aa_change)


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _normalize_aa_change(aa_change: str) -> str:
    """
    Normalize AA change for CIViC query.

    CIViC uses formats like: G12C, V600E (no 'p.' prefix)

    Args:
        aa_change: e.g., "p.G12C" or "G12C"

    Returns:
        Normalized format for CIViC (e.g., "G12C")
    """
    change = aa_change.strip()
    if change.startswith('p.'):
        change = change[2:]
    return change


def _get_oncokb_token() -> Optional[str]:
    """Get OncoKB API token from environment."""
    return os.environ.get('ONCOKB_API_KEY')
