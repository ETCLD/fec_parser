"""Main entry for fec_parser"""

from .computations import FECComputation
from .indicators import FECIndicators
from .parser import FECParser
from .version import get_pcg_config


class FECAnalyzer:
    """Main class for fec_parser module

    Use parse() to parse input file and then other methods
    to get stats about your FEC
    """

    def __init__(
        self,
        pc_definition_filepath=None,
        plan_comptable_type=None,
        custom_fields_definitions=None,
        config=None,
        config_year=None,
    ):
        self.computations = None
        self.indicateurs = None
        self.parser = None

        self.pc_definition_filepath = pc_definition_filepath
        self.plan_comptable_type = plan_comptable_type
        self.custom_fields_definitions = custom_fields_definitions or {}
        self.config = config
        self.config_year = config_year

    def parse(self, file):
        """Parse file (must be done first)"""
        self.parser = FECParser.from_bytesio(file)
        ecritures = list(self.parser.get_ecritures())

        # Detect config from input year or first ecriture date
        if not self.config:
            self.config = get_pcg_config(
                year=self.config_year,
                ecritures=ecritures,
            )

        self.indicateurs = FECIndicators(
            ecritures,
            config=self.config,
        )
        self.computations = FECComputation(
            ecritures,
            pc_definition_filepath=self.pc_definition_filepath,
            plan_comptable_type=self.plan_comptable_type,
            custom_fields_definition=self.custom_fields_definitions,
        )

    def get_compte_resultat(self):
        """Compute compte resultat based on input definition file"""
        if not self.parser:
            raise ValueError("Please call .parse() before.")
        return self.computations.compute_compte_resultat()

    def get_indicateurs(self):
        """Compute basic indicateurs financiers"""
        if not self.parser:
            raise ValueError("Please call .parse() before.")
        return self.indicateurs.compute_indicateurs()
