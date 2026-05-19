"""
Computational Evidence Module

Features:
- Query MyVariant.info for dbNSFP annotations (REVEL, CADD, SIFT, PolyPhen-2)
- Apply computational criteria (OP1, SBP1)

Criteria:
- OP1 (+1): All computational evidence supports oncogenic effect
- SBP1 (-1): All computational evidence suggests no impact
"""

import json
import logging
from typing import Dict, Optional, Tuple, Any

import requests

# ============================================================================
# CONSTANTS
# ============================================================================

MYVARIANT_API = "https://myvariant.info/v1/variant"

# Thresholds (user-specified + evidence-based)
THRESHOLDS = {
    'revel_oncogenic': 0.5,      # REVEL >= 0.5 = oncogenic (user request)
    'revel_benign': 0.3,         # REVEL <= 0.3 = benign
    'cadd_oncogenic': 20,        # CADD phred >= 20 = top 1% deleterious
    'cadd_benign': 10,           # CADD < 10 = likely benign
}

# SIFT/PolyPhen predictions (from dbNSFP)
SIFT_DELETERIOUS = {'D'}         # D = deleterious
POLYPHEN_DAMAGING = {'D', 'P'}   # D = probably damaging, P = possibly damaging

# Point values from paper
POINTS = {
    'OP1': +1,
    'SBP1': -1,
}

# Minimum predictors required for criterion application
MIN_PREDICTORS = 2

logger = logging.getLogger(__name__)


# ============================================================================
# MYVARIANT.INFO API
# ============================================================================

def query_myvariant(chrom: str, pos: int, ref: str, alt: str) -> Dict:
    """
    Query MyVariant.info for computational predictions.

    Args:
        chrom: Chromosome (1-22, X, Y)
        pos: Position (GRCh38)
        ref: Reference allele
        alt: Alternate allele

    Returns:
        Dict with predictor scores and predictions, or {'error': '...'}
    """
    # Normalize chromosome
    chrom = str(chrom).replace('chr', '')

    # Build HGVS genomic notation
    variant_id = f"chr{chrom}:g.{pos}{ref}>{alt}"

    # Fields to retrieve
    fields = ",".join([
        "dbnsfp.revel.score",
        "cadd.phred",
        "dbnsfp.sift.pred",
        "dbnsfp.polyphen2_hvar.pred"
    ])

    logger.info(f"  │    MyVariant: {variant_id}")

    try:
        response = requests.get(
            f"{MYVARIANT_API}/{variant_id}",
            params={
                'fields': fields,
                'assembly': 'hg38'  # Use GRCh38 coordinates (Ensembl VEP returns hg38)
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code == 404:
            logger.info("Variant not found in MyVariant.info")
            return {'found': False, 'variant_id': variant_id}

        if response.status_code != 200:
            logger.warning(f"HTTP {response.status_code}")
            return {'error': f'HTTP {response.status_code}', 'found': False}

        data = response.json()

        # Check for "not found" response (MyVariant returns 200 with notfound=true)
        if data.get('notfound'):
            logger.info("Variant not found in MyVariant.info")
            return {'found': False, 'variant_id': variant_id}

        # Extract nested scores
        result = {
            'found': True,
            'variant_id': variant_id,
            'revel_score': _extract_nested(data, 'dbnsfp', 'revel', 'score'),
            'cadd_phred': _extract_nested(data, 'cadd', 'phred'),
            'sift_pred': _extract_nested(data, 'dbnsfp', 'sift', 'pred'),
            'polyphen2_pred': _extract_nested(data, 'dbnsfp', 'polyphen2_hvar', 'pred'),
        }

        # Log scores (only non-None values)
        scores = []
        if result['revel_score'] is not None:
            scores.append(f"REVEL={result['revel_score']:.2f}")
        if result['cadd_phred'] is not None:
            scores.append(f"CADD={result['cadd_phred']:.1f}")
        if result['sift_pred']:
            scores.append(f"SIFT={result['sift_pred']}")
        if result['polyphen2_pred']:
            scores.append(f"PP2={result['polyphen2_pred']}")
        if scores:
            logger.info(f"  │    Scores: {', '.join(scores)}")

        return result

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.warning(f"Request failed: {e}")
        return {'error': str(e), 'found': False}


# ============================================================================
# COMPUTATIONAL CRITERIA
# ============================================================================

def check_computational_criteria(
    chrom: str,
    pos: int,
    ref: str,
    alt: str
) -> Tuple[str, int, str]:
    """
    Apply OP1/SBP1 criteria based on computational evidence.

    Criteria:
    - OP1 (+1): ALL utilized computational evidence supports oncogenic effect
    - SBP1 (-1): ALL utilized computational evidence suggests no impact
    - Can only be used ONCE per variant evaluation

    Args:
        chrom: Chromosome
        pos: Position
        ref: Reference allele
        alt: Alternate allele

    Returns:
        Tuple of (criterion_code, points, description)
    """
    data = query_myvariant(chrom, pos, ref, alt)

    if data.get('error'):
        logger.warning(f"MyVariant: {data['error']}")
        return ('', 0, f"Computational lookup error: {data['error']}")

    if not data.get('found'):
        logger.info("MyVariant: no data for variant")
        return ('', 0, 'No computational evidence available')

    # Count evidence signals
    oncogenic_signals = 0
    benign_signals = 0
    total_evaluated = 0
    evidence_details = []

    # REVEL score
    revel = data.get('revel_score')
    if revel is not None:
        total_evaluated += 1
        if revel >= THRESHOLDS['revel_oncogenic']:
            oncogenic_signals += 1
            evidence_details.append(f"REVEL={revel:.2f}(O)")
        elif revel <= THRESHOLDS['revel_benign']:
            benign_signals += 1
            evidence_details.append(f"REVEL={revel:.2f}(B)")
        else:
            evidence_details.append(f"REVEL={revel:.2f}(N)")  # Neutral

    # CADD phred score
    cadd = data.get('cadd_phred')
    if cadd is not None:
        total_evaluated += 1
        if cadd >= THRESHOLDS['cadd_oncogenic']:
            oncogenic_signals += 1
            evidence_details.append(f"CADD={cadd:.1f}(O)")
        elif cadd < THRESHOLDS['cadd_benign']:
            benign_signals += 1
            evidence_details.append(f"CADD={cadd:.1f}(B)")
        else:
            evidence_details.append(f"CADD={cadd:.1f}(N)")

    # SIFT prediction
    sift = data.get('sift_pred')
    if sift is not None:
        total_evaluated += 1
        if sift in SIFT_DELETERIOUS:
            oncogenic_signals += 1
            evidence_details.append(f"SIFT={sift}(O)")
        else:
            benign_signals += 1
            evidence_details.append(f"SIFT={sift}(B)")

    # PolyPhen-2 prediction
    polyphen = data.get('polyphen2_pred')
    if polyphen is not None:
        total_evaluated += 1
        if polyphen in POLYPHEN_DAMAGING:
            oncogenic_signals += 1
            evidence_details.append(f"PP2={polyphen}(O)")
        else:
            benign_signals += 1
            evidence_details.append(f"PP2={polyphen}(B)")

    evidence_str = ", ".join(evidence_details)
    logger.info(f"  │    Signals: {oncogenic_signals}O / {benign_signals}B / {total_evaluated}T")

    # Need minimum predictors
    if total_evaluated < MIN_PREDICTORS:
        return ('', 0, f'Insufficient computational evidence ({total_evaluated} predictors)')

    # OP1: ALL evidence supports oncogenic
    if oncogenic_signals == total_evaluated:
        return ('OP1', POINTS['OP1'],
                f'Computational: ALL oncogenic ({evidence_str})')

    # SBP1: ALL evidence suggests benign
    if benign_signals == total_evaluated:
        return ('SBP1', POINTS['SBP1'],
                f'Computational: ALL benign ({evidence_str})')

    # Mixed evidence - no criterion applies
    return ('', 0, f'Mixed computational evidence ({evidence_str})')


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _extract_nested(data: Dict, *keys) -> Optional[Any]:
    """
    Extract nested value from dict, handling lists (take first).

    Args:
        data: Source dictionary
        *keys: Path of keys to traverse

    Returns:
        Extracted value or None
    """
    current = data
    for key in keys:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and len(current) > 0:
            current = current[0].get(key) if isinstance(current[0], dict) else None
        else:
            return None
    # Handle list values (take first)
    if isinstance(current, list) and len(current) > 0:
        current = current[0]
    return current
