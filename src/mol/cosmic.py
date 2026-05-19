"""
COSMIC TSV lookup for hotspot sample counts.

Data source: Cosmic_CompleteTargetedScreensMutant_v103_GRCh38.tsv
Location: data/cosmic/
Download: https://cancer.sanger.ac.uk/cosmic/download (requires registration)
"""

import csv
import logging
import re
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

COSMIC_TSV_PATH = Path('./data/cosmic/Cosmic_CompleteTargetedScreensMutant_v103_GRCh38.tsv')

# Lazy-loaded index: gene -> position -> {position_count, variant_counts}
_cosmic_index: Optional[Dict[str, Dict[int, Dict]]] = None


# ============================================================================
# PUBLIC API
# ============================================================================

def load_cosmic_index(tsv_path: Path = None) -> Dict:
    """
    Load and index COSMIC TSV by gene + AA position.

    Returns:
        {gene: {position: {position_count: int, variant_counts: {aa_alt: int}}}}
    """
    global _cosmic_index

    if _cosmic_index is not None:
        return _cosmic_index

    if tsv_path is None:
        tsv_path = COSMIC_TSV_PATH

    if not tsv_path.exists():
        logger.warning(f"COSMIC TSV not found: {tsv_path}")
        _cosmic_index = {}
        return _cosmic_index

    logger.info(f"  │    COSMIC: loading {tsv_path.name}...")
    _cosmic_index = {}

    with open(tsv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            gene = row.get('GENE_SYMBOL', '').upper()
            aa = row.get('MUTATION_AA', '')  # e.g., 'p.G12C'

            if not gene or not aa:
                continue

            position = _parse_aa_position(aa)
            aa_alt = _parse_aa_alt(aa)

            if position is None:
                continue

            if gene not in _cosmic_index:
                _cosmic_index[gene] = {}

            if position not in _cosmic_index[gene]:
                _cosmic_index[gene][position] = {
                    'position_count': 0,
                    'variant_counts': {}
                }

            _cosmic_index[gene][position]['position_count'] += 1

            if aa_alt:
                vc = _cosmic_index[gene][position]['variant_counts']
                vc[aa_alt] = vc.get(aa_alt, 0) + 1

    logger.info(f"  │    COSMIC: loaded {len(_cosmic_index)} genes")
    return _cosmic_index


def get_cosmic_counts(gene: str, aa_position: int, aa_alt: str) -> Dict:
    """
    Get sample counts from COSMIC for a specific position.

    Args:
        gene: Hugo gene symbol (e.g., 'KRAS')
        aa_position: Amino acid position (e.g., 12)
        aa_alt: Alternate amino acid (e.g., 'C')

    Returns:
        {found, position_count, aa_change_count}
    """
    index = load_cosmic_index()

    gene_data = index.get(gene.upper())
    if not gene_data:
        return {'found': False, 'position_count': 0, 'aa_change_count': 0}

    pos_data = gene_data.get(aa_position)
    if not pos_data:
        return {'found': False, 'position_count': 0, 'aa_change_count': 0}

    return {
        'found': True,
        'position_count': pos_data['position_count'],
        'aa_change_count': pos_data['variant_counts'].get(aa_alt.upper(), 0)
    }


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _parse_aa_position(aa_string: str) -> Optional[int]:
    """Extract position from AA notation like 'p.G12C' -> 12."""
    if not aa_string:
        return None
    match = re.search(r'[A-Z](\d+)', aa_string.upper())
    return int(match.group(1)) if match else None


def _parse_aa_alt(aa_string: str) -> Optional[str]:
    """Extract alt AA from notation like 'p.G12C' -> 'C'."""
    if not aa_string:
        return None
    match = re.search(r'[A-Z]\d+([A-Z*])', aa_string.upper())
    return match.group(1) if match else None
