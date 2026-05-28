"""PCG versioning file"""

from dataclasses import dataclass, field


@dataclass
class PCGConfigV1:
    """Initial PCG"""

    # For indicateurs computing
    cession_actifs_patterns: list[str] = field(default_factory=lambda: ["775", "675"])
    quote_part_subvention_pattern: str = "777"
    transfert_charges_pattern: str = "79"


@dataclass
class PCGConfigV2(PCGConfigV1):
    """PCG used from 2025"""

    cession_actifs_patterns: list[str] = field(
        default_factory=lambda: ["657", "757", "6671", "7671"]
    )
    quote_part_subvention_pattern: str = "747"
    transfert_charges_pattern: str = "" # Removed in new PCG


def get_pcg_config(year=None, ecritures=None):
    """Returns PCG config for given FEC"""

    def config_from_year(year):
        """Get PCG config from FEC year"""
        if year >= 2025:
            return PCGConfigV2
        return PCGConfigV1

    if not year and not ecritures:
        raise TypeError

    if not year:
        year = ecritures[0].ecriture_date.year

    return config_from_year(year)()
