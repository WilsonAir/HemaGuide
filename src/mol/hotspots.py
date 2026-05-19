"""
Hotspots Module

Features:
- Query cancerhotspots.org API for mutation hotspots
- Apply hotspot criteria (OS3, OM3, OP3)

Criteria:
- OS3 (+4): Hotspot with ≥50 samples at position AND ≥10 with same AA change
- OM3 (+2): Hotspot with <50 samples at position AND ≥10 with same AA change
- OP3 (+1): In hotspot but <10 with same AA change
"""

import json
import logging
import re
import time
from typing import Dict, Tuple

import requests

from .cosmic import get_cosmic_counts

# ============================================================================
# CONSTANTS
# ============================================================================

HOTSPOT_API = "https://www.cancerhotspots.org/api/hotspots/single"

# Retry configuration for API requests
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds
REQUEST_TIMEOUT = 60  # seconds (increased for large responses like NRAS ~401KB)

# OS3, OM3, OP3
HOTSPOT_THRESHOLDS = {
    'os3_position': 50,   # Strong: ≥50 samples at position
    'os3_aa_change': 10,  # Strong: ≥10 with same AA change
    'om3_aa_change': 10,  # Moderate: ≥10 with same AA change (position <50)
}

# OS3, OM3, OP3
HOTSPOT_POINTS = {
    'OS3': +4,
    'OM3': +2,
    'OP3': +1,
}

logger = logging.getLogger(__name__)


# ============================================================================
# AA CHANGE PARSING
# ============================================================================

def parse_aa_position(aa_change: str) -> Tuple[int, str, str]:
    """
    Parse amino acid change notation to extract position and residues.

    This is a simple parser for standard missense notation (e.g., G12C).
    For complex variants (frameshift, stop-loss, indels), use
    variant_type.parse_aa_change_extended() instead.

    Args:
        aa_change: e.g., 'p.G12C', 'G12C', 'p.V600E'

    Returns:
        Tuple of (position, ref_aa, alt_aa)
        e.g., (12, 'G', 'C') for G12C

    Raises:
        ValueError: If format is invalid
    """
    # Strip 'p.' prefix if present
    change = aa_change.strip()
    if change.startswith('p.'):
        change = change[2:]

    # Match pattern: RefAA + Position + AltAA (e.g., G12C, V600E)
    match = re.match(r'^([A-Z])(\d+)([A-Z*])$', change, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid AA change format: {aa_change}")

    ref_aa = match.group(1).upper()
    position = int(match.group(2))
    alt_aa = match.group(3).upper()

    return position, ref_aa, alt_aa


# ============================================================================
# HOTSPOT API
# ============================================================================

def query_hotspot(gene: str) -> Dict:
    """
    Query cancerhotspots.org API for all hotspots of a gene.

    Args:
        gene: Hugo gene symbol (e.g., 'KRAS')

    Returns:
        Dict with 'hotspots' list of position data, or {'error': '...'}
    """
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                HOTSPOT_API,
                json=[gene.upper()],
                headers={'Content-Type': 'application/json'},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            # Validate JSON structure (detect truncated responses)
            text = response.text.strip()
            if not text or not (text.endswith('}') or text.endswith(']')):
                raise ValueError('Malformed JSON response')

            data = response.json()

            if not data or not isinstance(data, list):
                return {'hotspots': [], 'gene': gene}

            # Filter to just this gene (API may return related genes)
            gene_hotspots = [h for h in data if h.get('hugoSymbol', '').upper() == gene.upper()]
            return {'gene': gene, 'hotspots': gene_hotspots}

        except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError) as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(f"Hotspot API {gene}: {last_error}, retry {attempt+1}/{MAX_RETRIES} in {wait}s")
                time.sleep(wait)

    return {'error': last_error or 'Unknown error', 'hotspots': []}


def get_hotspot_counts(gene: str, aa_position: int, aa_alt: str) -> Dict:
    """
    Get sample counts for a specific position and AA change.

    Args:
        gene: Hugo gene symbol (e.g., 'KRAS')
        aa_position: Amino acid position (e.g., 12)
        aa_alt: Alternate amino acid (e.g., 'C')

    Returns:
        {
            'found': bool,
            'position_count': int,  # Total samples at this position
            'aa_change_count': int, # Samples with this specific AA change
            'residue': str,         # Position label (e.g., 'G12')
        }
    """
    result = query_hotspot(gene)

    if result.get('error'):
        logger.warning(f"Hotspot: {gene} lookup failed - {result['error']}")
        return {
            'found': False,
            'error': result['error'],
            'position_count': 0,
            'aa_change_count': 0
        }

    hotspots = result.get('hotspots', [])

    # Find hotspot at this position
    for h in hotspots:
        aa_pos = h.get('aminoAcidPosition', {})
        if aa_pos.get('start') == aa_position:
            position_count = h.get('tumorCount', 0)
            variant_counts = h.get('variantAminoAcid', {})

            # Get count for specific AA change
            aa_change_count = variant_counts.get(aa_alt.upper(), 0)

            return {
                'found': True,
                'position_count': position_count,
                'aa_change_count': aa_change_count,
                'residue': h.get('residue', f'pos{aa_position}'),
                'all_variants': variant_counts
            }

    # Position not found in hotspots
    return {
        'found': False,
        'position_count': 0,
        'aa_change_count': 0
    }


# ============================================================================
# HOTSPOT CRITERIA
# ============================================================================

def check_hotspot_criteria(
    gene: str,
    aa_position: int,
    aa_ref: str,
    aa_alt: str
) -> Tuple[str, int, str]:
    """
    Apply hotspot criteria.

    Args:
        gene: Hugo gene symbol (e.g., 'KRAS')
        aa_position: Amino acid position (e.g., 12)
        aa_ref: Reference amino acid (e.g., 'G')
        aa_alt: Alternate amino acid (e.g., 'C')

    Returns:
        Tuple of (criterion_code, points, description)
        - ('OS3', 4, '...') if position_count ≥ 50 AND aa_change_count ≥ 10
        - ('OM3', 2, '...') if position_count < 50 AND aa_change_count ≥ 10
        - ('OP3', 1, '...') if in hotspot but aa_change_count < 10
        - ('', 0, 'Not in hotspot') otherwise
    """
    counts = get_hotspot_counts(gene, aa_position, aa_alt)

    if counts.get('error'):
        logger.warning(f"Hotspot lookup error: {counts['error']}")
        return ('', 0, f"Hotspot lookup error: {counts['error']}")

    if not counts.get('found'):
        return ('', 0, 'Not in cancerhotspots.org')

    position_count = counts['position_count']
    aa_change_count = counts['aa_change_count']
    residue = counts.get('residue', f'{aa_ref}{aa_position}')
    source = 'cancerhotspots.org'

    # COSMIC fallback: when cancerhotspots position_count < 50, check COSMIC
    if counts['found'] and position_count < HOTSPOT_THRESHOLDS['os3_position']:
        cosmic = get_cosmic_counts(gene, aa_position, aa_alt)
        if (cosmic['found'] and
            cosmic['position_count'] >= HOTSPOT_THRESHOLDS['os3_position'] and
            cosmic['aa_change_count'] >= HOTSPOT_THRESHOLDS['os3_aa_change']):
            logger.info(f"  │    COSMIC upgrade: pos={cosmic['position_count']}, change={cosmic['aa_change_count']}")
            position_count = cosmic['position_count']
            aa_change_count = cosmic['aa_change_count']
            source = 'COSMIC'

    # OS3: Strong (+4) - high frequency hotspot
    if (position_count >= HOTSPOT_THRESHOLDS['os3_position'] and
            aa_change_count >= HOTSPOT_THRESHOLDS['os3_aa_change']):
        return (
            'OS3',
            HOTSPOT_POINTS['OS3'],
            f"Hotspot {residue}{aa_alt}: pos={position_count}, change={aa_change_count} (≥50/≥10) [{source}]"
        )

    # OM3: Moderate (+2) - moderate frequency hotspot
    if aa_change_count >= HOTSPOT_THRESHOLDS['om3_aa_change']:
        return (
            'OM3',
            HOTSPOT_POINTS['OM3'],
            f"Hotspot {residue}{aa_alt}: pos={position_count}, change={aa_change_count} (<50/≥10)"
        )

    # OP3: Supporting (+1) - low frequency in hotspot
    if position_count > 0:
        return (
            'OP3',
            HOTSPOT_POINTS['OP3'],
            f"Hotspot {residue}{aa_alt}: pos={position_count}, change={aa_change_count} (<10)"
        )

    return ('', 0, 'Not in cancerhotspots.org')
