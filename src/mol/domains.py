"""
Protein Domain Module

Features:
- Query UniProt API for protein features (domains, active sites, binding sites)
- Check if variant position falls within critical functional domain

Criteria:
- OM1 (+2): Located in a critical and well-established part of a functional domain
"""

import json
import logging
from typing import Dict, Tuple

import requests

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

UNIPROT_API = "https://rest.uniprot.org/uniprotkb/search"

# OM1
POINTS = {
    'OM1': +2,
}

# Critical domain feature types (UniProt feature keys)
# Note: UniProt API returns these type names in the features array
CRITICAL_FEATURE_TYPES = {
    'Active site',       # Catalytic residues (ft_act_site)
    'Binding site',      # Substrate/ligand binding (ft_binding)
    'Site',              # Other functionally important sites (ft_site)
    'DNA binding',       # DNA interaction (ft_dna_bind)
}

# Domain types that are considered critical when containing a variant
CRITICAL_DOMAIN_KEYWORDS = {
    'kinase',
    'catalytic',
    'active',
    'atp-binding',
    'gtp-binding',
    'dna-binding',
    'rna-binding',
    'helicase',
    'polymerase',
    'protease',
    'phosphatase',
    'transferase',
    'ligase',
    'hydrolase',
    'oxidoreductase',
}


# ============================================================================
# UNIPROT API
# ============================================================================

def query_uniprot_features(gene: str) -> Dict:
    """
    Query UniProt for protein features of a gene.

    Args:
        gene: Hugo gene symbol (e.g., "KRAS")

    Returns:
        Dict with 'found', 'features', 'length', or 'error'
    """
    logger.info(f"  │    UniProt: {gene}")

    # Search for human protein by gene name
    # Note: UniProt field names use ft_* prefix for features
    # Valid fields: ft_domain, ft_site, ft_binding, ft_act_site, ft_dna_bind
    # Invalid (removed): ft_metal, ft_np_bind, ft_lipid
    params = {
        'query': f'(gene:{gene}) AND (organism_id:9606)',  # Human only
        'format': 'json',
        'fields': 'accession,gene_names,length,ft_domain,ft_site,ft_binding,ft_act_site,ft_dna_bind',
        'size': 1  # Get top result (canonical)
    }

    try:
        response = requests.get(UNIPROT_API, params=params, timeout=30)

        if response.status_code != 200:
            logger.warning(f"UniProt HTTP {response.status_code}")
            return {'error': f'HTTP {response.status_code}', 'found': False}

        data = response.json()
        results = data.get('results', [])

        if not results:
            logger.info(f"  │    UniProt: {gene} not found")
            return {'found': False, 'gene': gene}

        protein = results[0]
        accession = protein.get('primaryAccession', '')
        length = protein.get('sequence', {}).get('length', 0)

        # Extract all features
        features = []
        for feature in protein.get('features', []):
            feat_type = feature.get('type', '')
            description = feature.get('description', '')
            location = feature.get('location', {})

            start = location.get('start', {}).get('value')
            end = location.get('end', {}).get('value')

            if start is not None:
                features.append({
                    'type': feat_type,
                    'description': description,
                    'start': start,
                    'end': end if end else start,  # Point features
                })

        logger.info(f"  │    UniProt: {len(features)} features for {accession}")

        return {
            'found': True,
            'gene': gene,
            'accession': accession,
            'length': length,
            'features': features
        }

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.warning(f"UniProt request failed: {e}")
        return {'error': str(e), 'found': False}


def is_in_critical_domain(gene: str, aa_position: int) -> Tuple[bool, str]:
    """
    Check if amino acid position falls within a critical functional domain.

    Args:
        gene: Hugo gene symbol
        aa_position: Amino acid position (1-indexed)

    Returns:
        Tuple of (is_in_critical_domain, description)
    """
    result = query_uniprot_features(gene)

    if result.get('error'):
        return False, f"UniProt error: {result['error']}"

    if not result.get('found'):
        return False, f"Gene {gene} not found in UniProt"

    features = result.get('features', [])

    # Find features containing this position
    matching_features = []
    for f in features:
        start = f.get('start', 0)
        end = f.get('end', 0)

        if start <= aa_position <= end:
            if _is_critical_feature(f):
                matching_features.append(f)

    if matching_features:
        # Return the most specific (smallest range) critical feature
        matching_features.sort(key=lambda f: (f.get('end', 0) - f.get('start', 0)))
        best = matching_features[0]

        feat_type = best.get('type', 'Domain')
        description = best.get('description', 'functional region')

        # Create descriptive string
        if best.get('start') == best.get('end'):
            position_str = f"position {best['start']}"
        else:
            position_str = f"positions {best['start']}-{best['end']}"

        return True, f"{feat_type} ({description}) at {position_str}"

    return False, "Not in critical functional domain"


# ============================================================================
# OM1 CRITERIA
# ============================================================================

def check_om1_criteria(gene: str, aa_position: int) -> Tuple[str, int, str]:
    """
    Check OM1 criterion: Located in critical functional domain.

    Criteria:
    - Located in a critical and well-established part of a functional domain
    - e.g., active site of an enzyme
    - Cannot be used if OS1 or OS3 is applicable

    Args:
        gene: Gene symbol
        aa_position: Amino acid position (1-indexed)

    Returns:
        Tuple of (criterion_code, points, description)
    """
    if aa_position is None or aa_position <= 0:
        return ('', 0, 'Invalid amino acid position')

    is_critical, domain_desc = is_in_critical_domain(gene, aa_position)

    if is_critical:
        return ('OM1', POINTS['OM1'], f"{gene} p.{aa_position} in {domain_desc}")

    return ('', 0, domain_desc)


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _is_critical_feature(feature: Dict) -> bool:
    """
    Determine if a feature is considered critical for OM1.

    Args:
        feature: Feature dict with 'type' and 'description'

    Returns:
        True if feature is critical
    """
    feat_type = feature.get('type', '')
    description = feature.get('description', '').lower()

    # Check if feature type is in critical list
    if feat_type in CRITICAL_FEATURE_TYPES:
        return True

    # Check if domain description contains critical keywords
    if feat_type == 'Domain':
        for keyword in CRITICAL_DOMAIN_KEYWORDS:
            if keyword in description:
                return True

    return False
