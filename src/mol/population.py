"""
Population Data Module - HGVS translation and gnomAD population criteria.

Provides:
- HGVS → genomic coordinate translation via Ensembl VEP
- gnomAD allele frequency lookup
- Population criteria

Criteria:
- SBVS1 (-8): MAF > 5%
- SBS1 (-4): MAF > 1%
- OP4 (+1): Absent or rare (MAF < 0.01%)
"""

import json
import logging
from typing import Dict, Optional, Tuple
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

GNOMAD_API = "https://gnomad.broadinstitute.org/api"
GNOMAD_DATASET = "gnomad_r4"

ENSEMBL_API = "https://rest.ensembl.org"
NCBI_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# SBVS1, SBS1, OP4
THRESHOLDS = {
    'sbvs1': 0.05,    # > 5% = very strong benign
    'sbs1': 0.01,     # > 1% = strong benign
    'op4': 0.0001,    # < 0.01% = supporting oncogenic
}

# SBVS1, SBS1, OP4
POINTS = {
    'SBVS1': -8,
    'SBS1': -4,
    'OP4': +1,
}

# DNA complement for strand conversion
_COMPLEMENT = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}


# ============================================================================
# HGVS TRANSLATION (Ensembl VEP)
# ============================================================================

def translate_hgvs(transcript: str, cds: str) -> Dict:
    """
    Translate HGVS notation to genomic coordinates via Ensembl VEP.

    On HTTP 400, tries fallbacks:
    1. Query NCBI for current version
    2. Strip version suffix

    Args:
        transcript: RefSeq transcript ID (e.g., "NM_033360.2")
        cds: CDS change notation (e.g., "c.182A>T")

    Returns:
        Dict with 'chrom', 'pos', 'ref', 'alt' or {'error': '...'}
    """
    logger.debug(f"VEP: Translating {transcript}:{cds}")

    result = _call_ensembl_vep(transcript, cds)

    if 'error' in result and 'HTTP 400' in result['error']:
        logger.debug(f"VEP: HTTP 400 for {transcript}:{cds}, trying fallbacks")

        # Fallback 1: Query NCBI for current RefSeq version
        current = _get_current_refseq_version(transcript)
        if current and current != transcript:
            logger.debug(f"VEP: Trying NCBI-resolved version {current}")
            result = _call_ensembl_vep(current, cds)
            if 'error' not in result:
                result['resolved_transcript'] = current

        # Fallback 2: Strip version suffix
        if 'error' in result and '.' in transcript:
            base = transcript.rsplit('.', 1)[0]
            logger.debug(f"VEP: Trying base transcript {base}")
            result = _call_ensembl_vep(base, cds)
            if 'error' not in result:
                result['resolved_transcript'] = base

    # Log outcome
    if 'resolved_transcript' in result:
        logger.info(f"  │    VEP: {transcript} → {result['resolved_transcript']}")
    elif 'error' in result:
        logger.warning(f"VEP: Failed for {transcript}:{cds} - {result['error']}")

    return result


# ============================================================================
# POPULATION DATA (gnomAD)
# ============================================================================

def query_gnomad(chrom: str, pos: int, ref: str, alt: str) -> Dict:
    """
    Query gnomAD GraphQL API for allele frequency.

    Args:
        chrom: Chromosome (1-22, X, Y)
        pos: Position (GRCh38)
        ref: Reference allele
        alt: Alternate allele

    Returns:
        Dict with 'af', 'found', 'source', and raw data
    """
    chrom = str(chrom).replace('chr', '').upper()
    variant_id = f"{chrom}-{pos}-{ref}-{alt}"

    logger.info(f"  │    gnomAD: {variant_id}")

    query = """
    query($variantId: String!, $dataset: DatasetId!) {
      variant(variantId: $variantId, dataset: $dataset) {
        variant_id
        exome {
          ac
          an
          af
        }
        genome {
          ac
          an
          af
        }
      }
    }
    """

    try:
        response = requests.post(
            GNOMAD_API,
            json={
                'query': query,
                'variables': {
                    'variantId': variant_id,
                    'dataset': GNOMAD_DATASET
                }
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code != 200:
            logger.warning(f"gnomAD: HTTP {response.status_code} for {variant_id}")
            return {'error': f'HTTP {response.status_code}', 'found': False}

        data = response.json()

        if 'errors' in data:
            error_msg = data['errors'][0].get('message', 'GraphQL error')
            if error_msg != 'Variant not found':
                logger.warning(f"gnomAD: {error_msg} for {variant_id}")
                return {'error': error_msg, 'found': False}

        variant = data.get('data', {}).get('variant')

        if variant is None:
            return {'found': False, 'af': None, 'variant_id': variant_id}

        exome_af = variant.get('exome', {}).get('af') if variant.get('exome') else None
        genome_af = variant.get('genome', {}).get('af') if variant.get('genome') else None

        afs = [af for af in [exome_af, genome_af] if af is not None]
        max_af = max(afs) if afs else None

        return {
            'found': True,
            'af': max_af,
            'exome_af': exome_af,
            'genome_af': genome_af,
            'variant_id': variant_id,
            'source': GNOMAD_DATASET
        }

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return {'error': str(e), 'found': False}


def check_population_criteria(af: Optional[float]) -> Tuple[str, int, str]:
    """
    Apply population frequency criteria.

    Args:
        af: Allele frequency from gnomAD (None = not found)

    Returns:
        Tuple of (criterion_code, points, description)
    """
    if af is None or af == 0:
        return ('OP4', POINTS['OP4'], 'Absent from gnomAD')

    if af > THRESHOLDS['sbvs1']:
        return ('SBVS1', POINTS['SBVS1'], f'Common: MAF={af:.4f} (>5%)')

    if af > THRESHOLDS['sbs1']:
        return ('SBS1', POINTS['SBS1'], f'Polymorphism: MAF={af:.4f} (1-5%)')

    if af < THRESHOLDS['op4']:
        return ('OP4', POINTS['OP4'], f'Rare: MAF={af:.6f} (<0.01%)')

    return ('', 0, f'Intermediate: MAF={af:.4f}')


def get_population_data(chrom: str, pos: int, ref: str, alt: str) -> Dict:
    """
    Get population data for a variant.

    Queries gnomAD for allele frequency and applies population criteria.

    Args:
        chrom: Chromosome (1-22, X, Y)
        pos: Position (GRCh38)
        ref: Reference allele
        alt: Alternate allele

    Returns:
        Dict with 'gnomad' data and 'criteria_met' list
    """
    gnomad = query_gnomad(chrom, pos, ref, alt)

    if gnomad.get('error'):
        return {
            'gnomad': {'found': False, 'error': gnomad['error']},
            'criteria_met': []
        }

    criterion, points, desc = check_population_criteria(gnomad.get('af'))

    return {
        'gnomad': {
            'af': gnomad.get('af'),
            'exome_af': gnomad.get('exome_af'),
            'genome_af': gnomad.get('genome_af'),
            'found': gnomad.get('found', False),
            'source': gnomad.get('source')
        },
        'criteria_met': [{'code': criterion, 'points': points, 'description': desc}] if criterion else []
    }


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _complement(allele: str) -> str:
    """Complement allele for minus strand → plus strand conversion."""
    return ''.join(_COMPLEMENT.get(b, b) for b in allele.upper())


def _get_current_refseq_version(transcript: str) -> Optional[str]:
    """Query NCBI for current RefSeq transcript version."""
    base = transcript.rsplit('.', 1)[0] if '.' in transcript else transcript
    try:
        resp = requests.get(
            f"{NCBI_API}/efetch.fcgi?db=nuccore&id={base}&rettype=acc&retmode=text",
            timeout=10
        )
        if resp.status_code == 200 and resp.text.strip():
            return resp.text.strip()
    except requests.RequestException as e:
        logger.debug(f"NCBI RefSeq lookup failed for {base}: {e}")
    return None


def _call_ensembl_vep(transcript: str, cds: str) -> Dict:
    """Single Ensembl VEP call for HGVS to genomic coordinate translation."""
    hgvs = f"{transcript}:{cds}"
    hgvs_encoded = quote(hgvs, safe='')

    try:
        response = requests.get(
            f"{ENSEMBL_API}/vep/human/hgvs/{hgvs_encoded}?refseq=1",
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code != 200:
            return {'error': f'HTTP {response.status_code}: {hgvs}'}

        data = response.json()

        if not data or not isinstance(data, list) or len(data) == 0:
            logger.warning(f"VEP: empty response for {hgvs}")
            return {'error': f'Empty response from VEP: {hgvs}'}

        variant = data[0]
        chrom = str(variant.get('seq_region_name', ''))
        pos = variant.get('start')
        allele_string = variant.get('allele_string', '')

        if not chrom or pos is None or '/' not in allele_string:
            logger.warning(f"VEP: missing coordinates for {hgvs}")
            return {'error': f'Missing coordinate data: {hgvs}'}

        ref, alt = allele_string.split('/')
        strand = variant.get('strand', 1)

        if strand == -1:
            ref = _complement(ref)
            alt = _complement(alt)

        return {
            'chrom': chrom,
            'pos': pos,
            'ref': ref,
            'alt': alt
        }

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return {'error': str(e)}
