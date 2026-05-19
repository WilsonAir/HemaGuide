"""
Horak et al. 2022 Oncogenicity Classification

Implements ClinGen/CGC/VICC SOP for somatic variant oncogenicity classification.
This module provides 12 criteria across 8 submodules for automated variant interpretation.

Submodules:
- population: gnomAD + HGVS translation (SBVS1, SBS1, OP4)
- hotspots: cancerhotspots.org (OS3, OM3, OP3)
- cosmic: COSMIC TSV lookup for hotspot counts
- cytogenetics: Cytogenetic risk classification (FISH/karyotype)
- computational: MyVariant.info / dbNSFP (OP1, SBP1)
- variant_type: Null variants, in-frame indels (OVS1, OM2)
- domains: UniProt protein domains (OM1)
- functional: CIViC + OncoKB functional evidence (OS2)
"""

# Population Data (gnomAD + HGVS translation)
from .population import (
    translate_hgvs,
    check_population_criteria,
    get_population_data,
    POINTS as POPULATION_POINTS
)

# Hotspot Data (cancerhotspots.org)
from .hotspots import (
    check_hotspot_criteria,
    parse_aa_position,
    HOTSPOT_POINTS
)

# COSMIC Data (local TSV)
from .cosmic import (
    get_cosmic_counts,
    load_cosmic_index
)

# Computational Evidence (MyVariant.info / dbNSFP)
from .computational import (
    check_computational_criteria,
    POINTS as COMPUTATIONAL_POINTS
)

# Variant Type Detection (OVS1, OM2)
from .variant_type import (
    parse_aa_change_extended,
    check_ovs1_criteria,
    check_om2_criteria,
    load_gene_classification,
    POINTS as VARIANT_TYPE_POINTS
)

# Protein Domain Lookup (OM1)
from .domains import (
    check_om1_criteria,
    POINTS as DOMAIN_POINTS
)

# Functional Evidence (OS2)
from .functional import (
    check_os2_criteria,
    POINTS as FUNCTIONAL_POINTS
)

# Cytogenetics (FISH risk classification)
from .cytogenetics import (
    classify_fish_risk,
    MYELOMA_HIGH_RISK_ABERRATIONS,
)

__all__ = [
    # Population Data (gnomAD + HGVS translation)
    'translate_hgvs',
    'check_population_criteria',
    'get_population_data',
    'POPULATION_POINTS',
    # Hotspot Data (cancerhotspots.org)
    'check_hotspot_criteria',
    'parse_aa_position',
    'HOTSPOT_POINTS',
    # COSMIC Data (local TSV)
    'get_cosmic_counts',
    'load_cosmic_index',
    # Computational Evidence (MyVariant.info / dbNSFP)
    'check_computational_criteria',
    'COMPUTATIONAL_POINTS',
    # Variant Type Detection (OVS1, OM2)
    'parse_aa_change_extended',
    'check_ovs1_criteria',
    'check_om2_criteria',
    'load_gene_classification',
    'VARIANT_TYPE_POINTS',
    # Protein Domain Lookup (OM1)
    'check_om1_criteria',
    'DOMAIN_POINTS',
    # Functional Evidence (OS2)
    'check_os2_criteria',
    'FUNCTIONAL_POINTS',
    # Cytogenetics (FISH risk)
    'classify_fish_risk',
    'MYELOMA_HIGH_RISK_ABERRATIONS',
]
