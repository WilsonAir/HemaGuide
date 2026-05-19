"""
Variant Type Module

Features:
- Parse CDS and AA change notations (HGVS format)
- Detect in-frame deletions/insertions (OM2)
- Detect stop-loss variants (OM2)
- Detect null variants: nonsense, frameshift, splice site (OVS1)

Criteria:
- OVS1 (+8): Null variant in a bona fide tumor suppressor gene
- OM2 (+2): In-frame del/ins in oncogene/TSG, or stop-loss in TSG
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Set

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

# OVS1, OM2
POINTS = {
    'OVS1': +8,
    'OM2': +2,
}

# Gene classification file path (relative to project root: data/gene_classification.json)
GENE_CLASSIFICATION_PATH = Path(__file__).parent.parent.parent / 'data' / 'gene_classification.json'

# Cached gene lists
_ONCOGENES: Optional[Set[str]] = None
_TSGS: Optional[Set[str]] = None


# ============================================================================
# GENE CLASSIFICATION
# ============================================================================

def _load_gene_classification() -> Tuple[Set[str], Set[str]]:
    """
    Load oncogene and TSG lists from JSON file.

    Returns:
        Tuple of (oncogenes_set, tsgs_set)
    """
    global _ONCOGENES, _TSGS

    if _ONCOGENES is not None and _TSGS is not None:
        return _ONCOGENES, _TSGS

    if not GENE_CLASSIFICATION_PATH.exists():
        logger.warning(f"Gene classification file not found: {GENE_CLASSIFICATION_PATH}")
        _ONCOGENES = set()
        _TSGS = set()
        return _ONCOGENES, _TSGS

    try:
        with open(GENE_CLASSIFICATION_PATH, 'r') as f:
            data = json.load(f)

        _ONCOGENES = set(g.upper() for g in data.get('oncogenes', []))
        _TSGS = set(g.upper() for g in data.get('tsgs', []))

        logger.info(f"  │    Gene lists: {len(_ONCOGENES)} oncogenes, {len(_TSGS)} TSGs")
        return _ONCOGENES, _TSGS

    except Exception as e:
        logger.error(f"Failed to load gene classification: {e}")
        _ONCOGENES = set()
        _TSGS = set()
        return _ONCOGENES, _TSGS


def load_gene_classification() -> Dict:
    """
    Load gene classification data as a dictionary.

    Returns:
        Dict with 'oncogenes' and 'tsgs' lists
    """
    oncogenes, tsgs = _load_gene_classification()
    return {
        'oncogenes': list(oncogenes),
        'tsgs': list(tsgs)
    }


def is_oncogene(gene: str) -> bool:
    """Check if gene is a known oncogene."""
    oncogenes, _ = _load_gene_classification()
    return gene.upper() in oncogenes


def is_tsg(gene: str) -> bool:
    """Check if gene is a known tumor suppressor gene."""
    _, tsgs = _load_gene_classification()
    return gene.upper() in tsgs


def is_cancer_gene(gene: str) -> bool:
    """Check if gene is either an oncogene or TSG."""
    oncogenes, tsgs = _load_gene_classification()
    return gene.upper() in oncogenes or gene.upper() in tsgs


# ============================================================================
# CDS CHANGE PARSING
# ============================================================================

def parse_cds_change(cds: str) -> Dict:
    """
    Parse CDS change notation to extract variant type and details.

    Handles:
    - Substitution: c.123A>G
    - Deletion: c.123del, c.123_125del, c.123_125delABC
    - Insertion: c.123_124insABC
    - Duplication: c.123dup, c.123_125dup
    - Delins: c.123_125delinsABC
    - Splice: c.123+1G>A, c.123-2A>G

    Args:
        cds: CDS notation (e.g., "c.123A>G", "c.123_125del")

    Returns:
        Dict with 'type', 'position', 'length_change', etc.
    """
    result = {
        'original': cds,
        'type': 'unknown',
        'is_splice': False,
        'is_in_frame': None,
        'length_change': 0,
    }

    if not cds or not cds.startswith('c.'):
        return result

    change = cds[2:]  # Remove 'c.' prefix

    # Check for splice site variant (contains + or - in position)
    splice_match = re.match(r'^(\d+)([+-])(\d+)([ACGT])>([ACGT])$', change)
    if splice_match:
        result['type'] = 'splice'
        result['is_splice'] = True
        result['position'] = int(splice_match.group(1))
        result['splice_offset'] = int(splice_match.group(2) + splice_match.group(3))
        return result

    # Substitution: 123A>G
    sub_match = re.match(r'^(\d+)([ACGT])>([ACGT])$', change)
    if sub_match:
        result['type'] = 'substitution'
        result['position'] = int(sub_match.group(1))
        result['is_in_frame'] = True  # SNVs don't change reading frame
        return result

    # Deletion with range: 123_125del or 123_125delABC
    del_range_match = re.match(r'^(\d+)_(\d+)del([ACGT]*)$', change)
    if del_range_match:
        start = int(del_range_match.group(1))
        end = int(del_range_match.group(2))
        deleted_seq = del_range_match.group(3)

        # Calculate deletion length
        if deleted_seq:
            del_len = len(deleted_seq)
        else:
            del_len = end - start + 1

        result['type'] = 'deletion'
        result['position'] = start
        result['end_position'] = end
        result['length_change'] = -del_len
        result['is_in_frame'] = (del_len % 3 == 0)
        return result

    # Single position deletion: 123del or 123delA
    del_single_match = re.match(r'^(\d+)del([ACGT]*)$', change)
    if del_single_match:
        result['type'] = 'deletion'
        result['position'] = int(del_single_match.group(1))
        deleted_seq = del_single_match.group(2)
        del_len = len(deleted_seq) if deleted_seq else 1
        result['length_change'] = -del_len
        result['is_in_frame'] = (del_len % 3 == 0)
        return result

    # Insertion: 123_124insABC
    ins_match = re.match(r'^(\d+)_(\d+)ins([ACGT]+)$', change)
    if ins_match:
        result['type'] = 'insertion'
        result['position'] = int(ins_match.group(1))
        inserted_seq = ins_match.group(3)
        ins_len = len(inserted_seq)
        result['length_change'] = ins_len
        result['is_in_frame'] = (ins_len % 3 == 0)
        return result

    # Duplication with range: 123_125dup
    dup_range_match = re.match(r'^(\d+)_(\d+)dup([ACGT]*)$', change)
    if dup_range_match:
        start = int(dup_range_match.group(1))
        end = int(dup_range_match.group(2))
        dup_seq = dup_range_match.group(3)

        if dup_seq:
            dup_len = len(dup_seq)
        else:
            dup_len = end - start + 1

        result['type'] = 'duplication'
        result['position'] = start
        result['length_change'] = dup_len
        result['is_in_frame'] = (dup_len % 3 == 0)
        return result

    # Single position duplication: 123dup
    dup_single_match = re.match(r'^(\d+)dup([ACGT]*)$', change)
    if dup_single_match:
        result['type'] = 'duplication'
        result['position'] = int(dup_single_match.group(1))
        dup_seq = dup_single_match.group(2)
        dup_len = len(dup_seq) if dup_seq else 1
        result['length_change'] = dup_len
        result['is_in_frame'] = (dup_len % 3 == 0)
        return result

    # Delins (deletion-insertion): 123_125delinsABC or 123delinsABC
    delins_range_match = re.match(r'^(\d+)_(\d+)delins([ACGT]+)$', change)
    if delins_range_match:
        start = int(delins_range_match.group(1))
        end = int(delins_range_match.group(2))
        inserted_seq = delins_range_match.group(3)

        del_len = end - start + 1
        ins_len = len(inserted_seq)
        net_change = ins_len - del_len

        result['type'] = 'delins'
        result['position'] = start
        result['length_change'] = net_change
        result['is_in_frame'] = (net_change % 3 == 0)
        return result

    delins_single_match = re.match(r'^(\d+)delins([ACGT]+)$', change)
    if delins_single_match:
        inserted_seq = delins_single_match.group(2)
        net_change = len(inserted_seq) - 1  # Replacing 1 base

        result['type'] = 'delins'
        result['position'] = int(delins_single_match.group(1))
        result['length_change'] = net_change
        result['is_in_frame'] = (net_change % 3 == 0)
        return result

    return result


# ============================================================================
# AA CHANGE PARSING
# ============================================================================

def parse_aa_change_extended(aa_change: str) -> Dict:
    """
    Extended parsing of amino acid change notation.

    Handles:
    - Missense: p.G12C
    - Nonsense: p.Q61*, p.Q61Ter
    - Frameshift: p.G12Cfs, p.G12Cfs*14
    - Stop-loss: p.*123Lext*?, p.*123L
    - In-frame deletion: p.G12_V14del
    - In-frame insertion: p.G12_V14insABC

    Args:
        aa_change: AA change notation (e.g., "p.G12C", "p.Q61*")

    Returns:
        Dict with 'type', 'position', 'is_null', 'is_stop_loss', etc.
    """
    result = {
        'original': aa_change,
        'type': 'unknown',
        'position': None,
        'ref_aa': None,
        'alt_aa': None,
        'is_null': False,
        'is_stop_loss': False,
        'is_in_frame_indel': False,
    }

    if not aa_change:
        return result

    # Strip 'p.' prefix
    change = aa_change.strip()
    if change.startswith('p.'):
        change = change[2:]

    # AA code pattern: single letter (G) or three-letter (Gly)
    AA_PATTERN = r'([A-Z][a-z]{0,2})'

    # Stop-loss: *123Lext*? or *123L or *123Lext*10 (mutation at stop codon)
    stop_loss_match = re.match(r'^\*(\d+)' + AA_PATTERN + r'(?:ext\*(?:\?|\d+))?$', change)
    if stop_loss_match:
        result['type'] = 'stop_loss'
        result['position'] = int(stop_loss_match.group(1))
        result['ref_aa'] = '*'
        result['alt_aa'] = stop_loss_match.group(2)
        result['is_stop_loss'] = True
        return result

    # Alternative stop-loss format: Ter123Lext*? or Ter123Lext*10
    stop_loss_ter_match = re.match(r'^Ter(\d+)' + AA_PATTERN + r'(?:ext\*(?:\?|\d+))?$', change)
    if stop_loss_ter_match:
        result['type'] = 'stop_loss'
        result['position'] = int(stop_loss_ter_match.group(1))
        result['ref_aa'] = '*'
        result['alt_aa'] = stop_loss_ter_match.group(2)
        result['is_stop_loss'] = True
        return result

    # Nonsense (termination): G12* or G12Ter or Glu12* or Glu12Ter
    nonsense_match = re.match(AA_PATTERN + r'(\d+)(\*|Ter)$', change)
    if nonsense_match:
        result['type'] = 'nonsense'
        result['ref_aa'] = nonsense_match.group(1)
        result['position'] = int(nonsense_match.group(2))
        result['alt_aa'] = '*'
        result['is_null'] = True
        return result

    # Frameshift: G12Cfs or G12Cfs*14 or G12fs or Gly12Cysfs or Arg41fs
    fs_match = re.match(AA_PATTERN + r'(\d+)' + AA_PATTERN + r'?fs(\*\d+)?$', change)
    if fs_match:
        result['type'] = 'frameshift'
        result['ref_aa'] = fs_match.group(1)
        result['position'] = int(fs_match.group(2))
        result['alt_aa'] = fs_match.group(3) if fs_match.group(3) else 'fs'
        result['is_null'] = True
        return result

    # In-frame deletion: G12_V14del or Gly12_Val14del
    del_match = re.match(AA_PATTERN + r'(\d+)_' + AA_PATTERN + r'(\d+)del$', change)
    if del_match:
        result['type'] = 'deletion'
        result['ref_aa'] = del_match.group(1)
        result['position'] = int(del_match.group(2))
        result['end_position'] = int(del_match.group(4))
        result['is_in_frame_indel'] = True
        return result

    # Single AA deletion: G12del or Gly12del
    single_del_match = re.match(AA_PATTERN + r'(\d+)del$', change)
    if single_del_match:
        result['type'] = 'deletion'
        result['ref_aa'] = single_del_match.group(1)
        result['position'] = int(single_del_match.group(2))
        result['is_in_frame_indel'] = True
        return result

    # In-frame insertion: G12_V14insABC or Gly12_Val14insAlaBC
    ins_match = re.match(AA_PATTERN + r'(\d+)_' + AA_PATTERN + r'(\d+)ins([A-Za-z]+)$', change)
    if ins_match:
        result['type'] = 'insertion'
        result['ref_aa'] = ins_match.group(1)
        result['position'] = int(ins_match.group(2))
        result['end_position'] = int(ins_match.group(4))
        result['inserted_aa'] = ins_match.group(5)
        result['is_in_frame_indel'] = True
        return result

    # Duplication: G12_V14dup or Gly12_Val14dup
    dup_match = re.match(AA_PATTERN + r'(\d+)(?:_' + AA_PATTERN + r'(\d+))?dup$', change)
    if dup_match:
        result['type'] = 'duplication'
        result['ref_aa'] = dup_match.group(1)
        result['position'] = int(dup_match.group(2))
        if dup_match.group(4):
            result['end_position'] = int(dup_match.group(4))
        result['is_in_frame_indel'] = True
        return result

    # Missense: G12C or Gly12Cys
    missense_match = re.match(AA_PATTERN + r'(\d+)' + AA_PATTERN + r'$', change)
    if missense_match:
        result['type'] = 'missense'
        result['ref_aa'] = missense_match.group(1)
        result['position'] = int(missense_match.group(2))
        result['alt_aa'] = missense_match.group(3)
        return result

    # Initiation codon mutation: M1?
    init_match = re.match(r'^M1[\?A-Z]?$', change)
    if init_match:
        result['type'] = 'initiation'
        result['position'] = 1
        result['ref_aa'] = 'M'
        result['is_null'] = True
        return result

    return result


# ============================================================================
# VARIANT TYPE DETECTION
# ============================================================================

def is_null_variant(cds: str, aa_change: str) -> Tuple[bool, str]:
    """
    Detect if variant is a null/loss-of-function variant.

    Null variants include:
    - Nonsense (stop-gain): creates premature termination
    - Frameshift: shifts reading frame
    - Canonical splice site: ±1 or ±2 positions
    - Initiation codon: affects start codon (M1)

    Args:
        cds: CDS notation (e.g., "c.123+1G>A")
        aa_change: AA change notation (e.g., "p.Q61*")

    Returns:
        Tuple of (is_null, description)
    """
    # Check AA change first
    if aa_change:
        aa_parsed = parse_aa_change_extended(aa_change)

        if aa_parsed['type'] == 'nonsense':
            return True, f"Nonsense mutation: {aa_change}"

        if aa_parsed['type'] == 'frameshift':
            return True, f"Frameshift mutation: {aa_change}"

        if aa_parsed['type'] == 'initiation':
            return True, f"Initiation codon mutation: {aa_change}"

    # Check CDS for splice site
    if cds:
        cds_parsed = parse_cds_change(cds)

        if cds_parsed['is_splice']:
            offset = abs(cds_parsed.get('splice_offset', 0))
            if offset in [1, 2]:  # Canonical splice sites
                return True, f"Canonical splice site variant: {cds}"

        # Check for frameshift from CDS (if AA not available)
        if not aa_change and cds_parsed['is_in_frame'] is False:
            return True, f"Frameshift ({cds_parsed['type']}): {cds}"

    return False, ""


def is_in_frame_indel(cds: str, aa_change: str) -> Tuple[bool, str]:
    """
    Detect if variant is an in-frame insertion or deletion.

    Args:
        cds: CDS notation
        aa_change: AA change notation

    Returns:
        Tuple of (is_in_frame_indel, description)
    """
    # Check AA change first (more reliable)
    if aa_change:
        aa_parsed = parse_aa_change_extended(aa_change)

        if aa_parsed['is_in_frame_indel']:
            return True, f"In-frame {aa_parsed['type']}: {aa_change}"

    # Check CDS
    if cds:
        cds_parsed = parse_cds_change(cds)

        if cds_parsed['type'] in ['deletion', 'insertion', 'duplication', 'delins']:
            if cds_parsed.get('is_in_frame') is True:
                return True, f"In-frame {cds_parsed['type']}: {cds}"

    return False, ""


def is_stop_loss(aa_change: str) -> Tuple[bool, str]:
    """
    Detect if variant is a stop-loss (mutation at termination codon).

    Args:
        aa_change: AA change notation (e.g., "p.*123Lext*?")

    Returns:
        Tuple of (is_stop_loss, description)
    """
    if not aa_change:
        return False, ""

    aa_parsed = parse_aa_change_extended(aa_change)

    if aa_parsed['is_stop_loss']:
        return True, f"Stop-loss mutation: {aa_change}"

    return False, ""


# ============================================================================
# OVS1 CRITERIA
# ============================================================================

def check_ovs1_criteria(
    gene: str,
    cds: str,
    aa_change: str
) -> Tuple[str, int, str]:
    """
    Check OVS1 criterion: Null variant in tumor suppressor gene.

    Criteria:
    - Nonsense, frameshift, canonical ±1/2 splice sites, initiation codon
    - Must be in a bona fide TSG

    Args:
        gene: Gene symbol
        cds: CDS notation
        aa_change: AA change notation

    Returns:
        Tuple of (criterion_code, points, description)
    """
    # Must be in TSG
    if not is_tsg(gene):
        return ('', 0, f'{gene} is not a known TSG')

    is_null, null_desc = is_null_variant(cds, aa_change)

    if is_null:
        return ('OVS1', POINTS['OVS1'], f"{null_desc} in TSG {gene}")

    return ('', 0, 'Not a null variant')


def check_om2_criteria(
    gene: str,
    cds: str,
    aa_change: str
) -> Tuple[str, int, str]:
    """
    Check OM2 criterion: Protein length changes in cancer gene.

    Criteria:
    - In-frame deletions/insertions in known oncogene or TSG
    - Stop-loss variants in known TSG

    Args:
        gene: Gene symbol
        cds: CDS notation
        aa_change: AA change notation

    Returns:
        Tuple of (criterion_code, points, description)
    """
    # Check for stop-loss in TSG
    if is_tsg(gene):
        is_stop, stop_desc = is_stop_loss(aa_change)
        if is_stop:
            return ('OM2', POINTS['OM2'], f"{stop_desc} in TSG {gene}")

    # Check for in-frame indel in cancer gene
    if is_cancer_gene(gene):
        is_inframe, inframe_desc = is_in_frame_indel(cds, aa_change)
        if is_inframe:
            gene_type = "oncogene" if is_oncogene(gene) else "TSG"
            return ('OM2', POINTS['OM2'], f"{inframe_desc} in {gene_type} {gene}")

    return ('', 0, 'Not an in-frame indel or stop-loss in cancer gene')
