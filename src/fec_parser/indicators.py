"""Module to to compute indicateurs from FEC entries."""

from decimal import Decimal


class FECIndicators:
    """Compute indicateurs financiers from FEC."""

    def __init__(self, ecritures, config=None):
        self.ecritures = list(ecritures)
        self.sum_ecritures_by_compte = {}
        for ecriture in self.ecritures:
            self.sum_ecritures_by_compte.setdefault(ecriture.compte_num, 0)
            self.sum_ecritures_by_compte[ecriture.compte_num] += (
                ecriture.credit - ecriture.debit
            )
        self.config = config

    def _compute_compte_sum(self, start_pattern):
        """Return sum for given start pattern"""
        return sum(
            v
            for k, v in self.sum_ecritures_by_compte.items()
            if k.startswith(start_pattern)
        )

    def compute_multiple_compte_sum(self, *comptes_patterns):
        """Aggregate multiple accounts matching pattern by summing them."""
        ret = Decimal("0.00")
        for pattern in comptes_patterns:
            ret += self._compute_compte_sum(pattern)
        return ret

    def compute_resultat_net(self):
        """Compute the resultat net by a different computation than in compute_all to check
        the file is valid."""
        return self.compute_multiple_compte_sum("6", "7")

    def compute_ebe(self):
        """Compute Excédent Brut d'Exploitation"""
        ebe = self.compute_resultat_net() - self.compute_multiple_compte_sum(
            "66",
            "76",
            "67",
            "77",
            "68",
            "78",
            "69",
        )

        if self.config.transfert_charges_pattern:
            ebe -= self._compute_compte_sum(self.config.transfert_charges_pattern)
        if self.config.quote_part_subvention_pattern != "777":
            ebe -= self._compute_compte_sum("747")
        return ebe

    def compute_caf(self):
        """Compute Capacité d'Auto Financement"""
        return (
            self.compute_resultat_net()
            - self.compute_multiple_compte_sum("681", "781")
            - self.compute_multiple_compte_sum("689", "789")
            - self.compute_multiple_compte_sum(*self.config.cession_actifs_patterns)
            - self._compute_compte_sum(self.config.quote_part_subvention_pattern)
        )

    def compute_fr(self):
        """Compute Fonds de Roulement

        Fonds de roulement = Resultat net (6XX+7XX) + 1XX + 2XX + 45XX
        """
        return self.compute_resultat_net() + self.compute_multiple_compte_sum(
            "1", "2", "45"
        )

    def compute_bfr(self):
        """Compute Besoin en Fonds de Roulement

        BFR = 3XX + 4XX (excluding 45XX)
        """
        return -(
            self.compute_multiple_compte_sum("3", "4") - self._compute_compte_sum("45")
        )

    def compute_indicateurs(self):
        """Return computed indicateurs financiers"""
        return {
            "EBE": self.compute_ebe(),
            "CAF": self.compute_caf(),
            "FR": self.compute_fr(),
            "BFR": self.compute_bfr(),
        }
