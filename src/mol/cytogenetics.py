"""
Cytogenetic/FISH classification for tumor board cases.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


# ============================================================================
# MYELOMA RISK CLASSIFICATION (IMWG)
# ============================================================================

# High-risk FISH aberrations for myeloma
MYELOMA_HIGH_RISK_ABERRATIONS = {
    '17p', '17p13', 'del17p', 'del(17p)',  # TP53 deletion
    't(4;14)', '4;14',  # FGFR3-MMSET
    't(14;16)', '14;16',  # MAF
    't(14;20)', '14;20',  # MAFB
}


# ============================================================================
# AML RISK CLASSIFICATION (ELN 2022)
# ============================================================================

# ELN 2022 Favorable-risk cytogenetic abnormalities
AML_FAVORABLE_CYTOGENETICS = {
    't(8;21)', 'runx1::runx1t1', 'runx1-runx1t1',           # Core binding factor
    'inv(16)', 't(16;16)', 'cbfb::myh11', 'cbfb-myh11',     # Core binding factor
    't(15;17)', 'pml::rara', 'pml-rara',                     # APL
}

# ELN 2022 Adverse-risk cytogenetic abnormalities
AML_ADVERSE_CYTOGENETICS = {
    't(6;9)', 'dek::nup214', 'dek-nup214',
    '11q23', 'kmt2a',                                        # KMT2A/11q23 rearrangements
    't(9;22)', 'bcr::abl1', 'bcr-abl1',                      # Philadelphia chromosome
    't(8;16)', 'kat6a::crebbp', 'kat6a-crebbp',              # New in ELN 2022
    'inv(3)', 't(3;3)', 'gata2::mecom', 'gata2-mecom',
    't(3q26.2)', 'mecom',                                    # MECOM rearrangements
    '-5', 'del(5q)', '-5/del(5q)',                           # Chromosome 5 abnormalities
    '-7', 'del(7q)', '-7/del(7q)',                           # Chromosome 7 abnormalities
    '-17', 'abn(17p)',                                       # TP53 locus
    'del(17p)',
    '17p',                                                   # TP53 deletion
    'complex', 'komplex',                                    # Complex karyotype (>=3 abnormalities)
    'monosomal',                                             # Monosomal karyotype
}

# ELN 2022 Adverse-risk molecular mutations (MDS-related gene mutations)
AML_ADVERSE_MUTATIONS = {
    'TP53', 'ASXL1', 'BCOR', 'EZH2', 'RUNX1',
    'SF3B1', 'SRSF2', 'STAG2', 'U2AF1', 'ZRSR2',
}

# ELN 2022 Favorable-risk molecular mutations (context-dependent)
AML_FAVORABLE_MUTATIONS = {'NPM1', 'CEBPA'}  # bZIP in-frame mutated CEBPA, NPM1 without FLT3-ITD


# ============================================================================
# ALL RISK CLASSIFICATION (WHO/NCCN Guidelines)
# ============================================================================

# ALL Favorable-risk cytogenetic abnormalities
ALL_FAVORABLE_CYTOGENETICS = {
    't(12;21)', 'etv6::runx1', 'etv6-runx1', 'tel-aml1',  # ETV6-RUNX1 (TEL-AML1) - excellent prognosis
    'hyperdiploidy', 'high hyperdiploidy',                 # >50 chromosomes
}

# ALL Adverse-risk cytogenetic abnormalities
ALL_ADVERSE_CYTOGENETICS = {
    # Philadelphia chromosome - high risk (though TKI-responsive)
    't(9;22)', 'bcr::abl1', 'bcr-abl1', 'ph+', 'philadelphia',
    # KMT2A/MLL rearrangements - high risk
    't(4;11)', 'kmt2a::aff1', 'mll::af4', 'mll-af4', 'af4-mll',
    '11q23', 't(11;19)', 'kmt2a', 'mll',
    # TCF3-HLF - very poor prognosis
    't(17;19)', 'tcf3::hlf', 'e2a-hlf',
    # Hypodiploidy - poor prognosis
    'hypodiploidy', 'near-haploidy', 'nearhaploidy', 'low hypodiploidy', 'lowhypodiploidy',
    # Complex karyotype
    'complex karyotype', 'complex',
    # iAMP21
    'iamp21', 'intrachromosomal amplification of chromosome 21',
    # IKZF1 deletions (often detected by MLPA/array, but may appear in FISH)
    'ikzf1', 'ikaros',
}


def classify_fish_risk(findings: List[Dict], entity_slug: str = 'fallback') -> List[Dict]:
    """
    Entity-aware FISH risk classification.

    Routes to entity-specific classification logic:
    - myeloma: IMWG guidelines
    - aml: ELN 2022 guidelines
    - all: WHO/NCCN guidelines

    Args:
        findings: List of FISH finding dicts
        entity_slug: Entity type ('myeloma', 'aml', or 'all')

    Returns:
        Same list with risk_status added to each finding
    """
    if entity_slug == 'aml':
        results = _classify_aml_fish_risk(findings)
    elif entity_slug == 'all':
        results = _classify_all_fish_risk(findings)
    elif entity_slug == 'myeloma':
        results = _classify_myeloma_risk(findings)
    else:
        # No entity-specific FISH rules — return findings unmodified
        results = findings

    # Log summary of high-risk/adverse findings
    if entity_slug == 'myeloma':
        high_risk = [f for f in results if f.get('risk_status') == 'high_risk']
        if high_risk:
            aberrations = [f.get('aberration', '?') for f in high_risk]
            logger.info(f"FISH {entity_slug}: {len(high_risk)} high-risk ({', '.join(aberrations)})")
    else:  # AML or ALL
        adverse = [f for f in results if f.get('risk_status') == 'adverse']
        favorable = [f for f in results if f.get('risk_status') == 'favorable']
        if adverse:
            aberrations = [f.get('aberration', '?') for f in adverse]
            logger.info(f"FISH {entity_slug}: {len(adverse)} adverse ({', '.join(aberrations)})")
        if favorable:
            aberrations = [f.get('aberration', '?') for f in favorable]
            logger.info(f"FISH {entity_slug}: {len(favorable)} favorable ({', '.join(aberrations)})")

    return results


def _classify_myeloma_risk(findings: List[Dict]) -> List[Dict]:
    """
    Myeloma FISH risk classification (IMWG guidelines).

    High-risk aberrations: del(17p), t(4;14), t(14;16), t(14;20), gain(1q) >=4 copies

    Args:
        findings: List of FISH finding dicts

    Returns:
        Same list with risk_status added to each finding
    """
    for finding in findings:
        aberration = finding.get('aberration', '').lower().replace(' ', '')
        finding_type = finding.get('finding_type', '').lower()
        partner = finding.get('partner', '') or ''

        # Check high-risk deletion or translocation patterns
        is_high_risk = False

        # Check aberration field
        for hr in MYELOMA_HIGH_RISK_ABERRATIONS:
            if hr.lower() in aberration:
                is_high_risk = True
                break

        # Check partner field for translocations
        if not is_high_risk and partner:
            partner_lower = partner.lower().replace(' ', '')
            for hr in MYELOMA_HIGH_RISK_ABERRATIONS:
                if hr.lower() in partner_lower:
                    is_high_risk = True
                    break

        # Special case: gain of 1q with >=4 copies is high-risk
        if not is_high_risk and finding_type == 'gain' and aberration.startswith('1q'):
            copies = finding.get('copies')
            if copies is not None and copies >= 4:
                is_high_risk = True

        finding['risk_status'] = 'high_risk' if is_high_risk else 'standard'

    return findings


def _classify_aml_fish_risk(findings: List[Dict]) -> List[Dict]:
    """
    AML FISH risk classification (ELN 2022 guidelines).

    Classifies each finding as 'favorable', 'adverse', or 'intermediate'.

    Args:
        findings: List of FISH finding dicts

    Returns:
        Same list with risk_status added to each finding
    """
    for finding in findings:
        aberration = finding.get('aberration', '').lower().replace(' ', '')
        partner = finding.get('partner', '') or ''
        partner_lower = partner.lower().replace(' ', '') if partner else ''

        risk = 'intermediate'  # Default

        # Check for favorable cytogenetics
        for fav in AML_FAVORABLE_CYTOGENETICS:
            if fav.lower() in aberration or fav.lower() in partner_lower:
                risk = 'favorable'
                break

        # Check for adverse cytogenetics (overrides favorable if both present)
        if risk != 'adverse':
            for adv in AML_ADVERSE_CYTOGENETICS:
                if adv.lower() in aberration or adv.lower() in partner_lower:
                    risk = 'adverse'
                    break

        # ELN 2022 exception: t(9;11)/MLLT3::KMT2A is intermediate, not adverse
        if risk == 'adverse':
            t911 = {'t(9;11)', 'mllt3::kmt2a', 'mllt3-kmt2a'}
            if any(p in aberration or p in partner_lower for p in t911):
                risk = 'intermediate'

        finding['risk_status'] = risk

    return findings


def _classify_all_fish_risk(findings: List[Dict]) -> List[Dict]:
    """
    ALL FISH risk classification (WHO/NCCN guidelines).

    Classifies each finding as 'favorable', 'adverse', or 'intermediate'.

    Key prognostic markers:
    - Favorable: ETV6-RUNX1 t(12;21), hyperdiploidy
    - Adverse: Ph+ t(9;22), KMT2A/MLL rearrangements, hypodiploidy, iAMP21

    Args:
        findings: List of FISH finding dicts

    Returns:
        Same list with risk_status added to each finding
    """
    for finding in findings:
        aberration = finding.get('aberration', '').lower().replace(' ', '')
        partner = finding.get('partner', '') or ''
        partner_lower = partner.lower().replace(' ', '') if partner else ''

        risk = 'intermediate'  # Default

        # Check for favorable cytogenetics
        for fav in ALL_FAVORABLE_CYTOGENETICS:
            if fav.lower() in aberration or fav.lower() in partner_lower:
                risk = 'favorable'
                break

        # Check for adverse cytogenetics (overrides favorable if both present)
        if risk != 'adverse':
            for adv in ALL_ADVERSE_CYTOGENETICS:
                if adv.lower() in aberration or adv.lower() in partner_lower:
                    risk = 'adverse'
                    break

        finding['risk_status'] = risk

    return findings
