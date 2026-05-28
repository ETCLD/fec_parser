"""Parse FEC file"""

import csv
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from io import BytesIO, StringIO, TextIOBase, TextIOWrapper

from .errors import BadFECFileError, FECParserError

fec_ecriture_specs = [
    {"name": "JournalCode", "attr": "journal_code", "null": False},
    {"name": "JournalLib", "attr": "journal_lib", "null": False},
    {"name": "EcritureDate", "attr": "ecriture_date", "null": False},
    {"name": "CompteNum", "attr": "compte_num", "null": False},
    {"name": "CompteLib", "attr": "compte_lib", "null": False},
    {"name": "CompAuxNum", "attr": "comp_aux_num", "null": True},
    {"name": "CompAuxLib", "attr": "comp_aux_lib", "null": True},
    {"name": "EcritureLib", "attr": "ecriture_lib", "null": False},
    {"name": "Debit", "attr": "debit", "null": False},
    {"name": "Credit", "attr": "credit", "null": False},
]


@dataclass
class FECEcriture:
    """One ecriture for a FEC file."""

    file_reference: str
    journal_code: str
    journal_lib: str
    ecriture_date: date
    compte_num: str
    compte_lib: str
    ecriture_lib: str
    debit: Decimal
    credit: Decimal
    comp_aux_num: str = ""
    comp_aux_lib: str = ""

    @staticmethod
    def from_dict(file_reference, ecriture):
        ecriture_dict = {"file_reference": file_reference}

        for spec in fec_ecriture_specs:
            field = spec["name"]
            attr_name = spec["attr"]

            field_value = ecriture.get(field, "")

            if field in ["Debit", "Credit"]:
                value = ecriture.get("Montant")
                sens = ecriture.get("Sens")
                if value and sens:
                    field_value = value if sens == field[0] else "0"
                field_value = Decimal(field_value.replace(",", "."))

            if field_value == "":
                if not spec["null"]:
                    raise ValueError(
                        "la ligne ne possède pas de montant ou le format comporte des erreurs."
                    )
                ecriture_dict[attr_name] = ""
                continue

            if not isinstance(field_value, Decimal):
                field_value = field_value.strip()

            if field == "EcritureDate":
                try:
                    field_value = datetime.strptime(field_value, "%Y%m%d").date()
                except ValueError as e:
                    raise ValueError(
                        "la ligne ne possède pas de date d'écriture valide."
                    ) from e

            ecriture_dict[attr_name] = field_value

        return FECEcriture(**ecriture_dict)


class FECParser:
    """Represents the file parser."""

    @staticmethod
    def from_bytesio(fec: BytesIO, filename=""):
        """Read file from BytesIO"""
        encoding = "utf-8-sig"
        try:
            fec.read().decode(encoding)
        except UnicodeDecodeError:
            encoding = "ISO-8859-15"
        finally:
            fec.seek(0)

        fec_txt = TextIOWrapper(fec, encoding=encoding)

        return FECParser(fec_txt, filename)

    @staticmethod
    def from_txt(fec_str: str, filename=""):
        """Parse the FEC file as a string."""
        fec_file = StringIO(fec_str)
        fec = FECParser(fec_file, filename)
        return fec

    def __init__(self, fec: TextIOBase, filename=""):
        self.errors = None
        self.filename = filename
        self.parsed_fec = []
        self.fec = fec
        self.dialect = None

    def parse(self) -> None:
        """Parse the FEC file."""
        if self.errors is not None:
            return self.errors

        self.errors = []
        try:
            self.dialect = csv.Sniffer().sniff(self.fec.read(), delimiters="|\t")
        except csv.Error as e:
            raise BadFECFileError(
                "Le format de votre fichier semble invalide - pour rappel les fichiers d’un "
                "autre format que CSV ou txt ne sont pas acceptés (erreur de détection du "
                "délimiteur CSV)."
            ) from e
        self.fec.seek(0)

        try:
            reader = csv.DictReader(
                self.fec,
                delimiter=self.dialect.delimiter,
                quotechar=None,
                quoting=csv.QUOTE_NONE,
            )
        except csv.Error as e:
            raise BadFECFileError(
                "Le format de votre fichier semble invalide - pour rappel les fichiers d’un "
                "autre format que CSV ou txt ne sont pas acceptés "
                "(erreur de lecture du fichier)."
            ) from e

        for i, line in enumerate(reader):
            try:
                file_reference = f"{self.filename}:{i+2}"
                FECEcriture.from_dict(file_reference, line)
            except ValueError as e:
                self.errors.append(FECParserError(self.filename, i + 2, str(e)))

        return self.errors

    def get_ecritures(self):
        """Get FEC ecritures parsed from file"""
        errors = self.parse()
        if errors:
            raise BadFECFileError(errors)

        self.fec.seek(0)
        reader = csv.DictReader(
            self.fec,
            delimiter=self.dialect.delimiter,
            quotechar=None,
            quoting=csv.QUOTE_NONE,
        )
        for i, line in enumerate(reader):
            file_reference = f"{self.filename}:{i+2}"
            try:
                yield FECEcriture.from_dict(file_reference, line)
            except ValueError:
                continue
