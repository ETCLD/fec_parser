"""Module to to perform calculations from FEC entries."""

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from graphlib import TopologicalSorter


@dataclass
class PlanComptableElement:
    """A row of the PlanComptable."""

    compte_pattern: str
    num: str
    label: str
    opposite: bool
    parent: str
    to_sum: bool = False
    plan_comptable: str = ""
    formula: str = ""
    value: Decimal = None
    sub_rows: list = None
    child_identifiers: list = None

    def __post_init__(self):
        """Force the datetime to now if datetime is None.
        The default_factory is not call if the value is None.
        """
        if self.value is None:
            self.value = Decimal("0.00")
        if self.sub_rows is None:
            self.sub_rows = []
        if self.child_identifiers is None:
            self.child_identifiers = []


FORMULA_ADDITION = "+"
FORMULA_SUBTRACTION = "-"
FORMULA_KEYWORDS = (FORMULA_ADDITION, FORMULA_SUBTRACTION)


class FECComputation:
    """Helper class to do computations on FECs."""

    def __init__(
        self,
        ecritures,
        pc_definition_filepath,
        plan_comptable_type="",
        custom_fields_definition=None,
    ):
        self.pc_definition_filepath = pc_definition_filepath
        self.plan_comptable_type = plan_comptable_type
        self.custom_fields_definition = custom_fields_definition or []

        self.all_ecritures = list(ecritures)
        self.ecritures = [
            ecriture
            for ecriture in self.all_ecritures
            if ecriture.compte_num.startswith("6")
            or ecriture.compte_num.startswith("7")
        ]
        self.sum_ecritures_by_compte = {}
        self.compte_names = {}

        for ecriture in self.ecritures:
            self.sum_ecritures_by_compte.setdefault(ecriture.compte_num, 0)
            self.sum_ecritures_by_compte[ecriture.compte_num] += (
                ecriture.credit - ecriture.debit
            )
            self.compte_names[ecriture.compte_num] = ecriture.compte_lib

        # Boolean to know if PC definition file handle differents PC type
        self._pc_file_uses_pc_type = None
        self._cached_results = None

    def _compte_pattern_match(self, compte_num, pattern):
        """Check if a compte_num match a pattern.
        The pattern is the start of the account name, if pattern contains
        'X', it also check the end of the account name so 79XXX1 match all accounts starting by
        79 and ending by 1. The number of X is not relevant.
        """
        if pattern.startswith("CUSTOM"):
            # pylint: disable=protected-access
            include, not_include = self.custom_fields_definition[pattern]
            return self._compte_pattern_match(compte_num, include) and not any(
                self._compte_pattern_match(compte_num, p) for p in not_include
            )

        compte_num = compte_num.rstrip("0")

        splited = pattern.split("X")
        startswith = splited[0]
        endswith = None
        if len(splited) > 1:
            endswith = splited[-1]

        if endswith is not None:
            if not compte_num.endswith(endswith):
                return False
            # If XX are precised, it must have something between the start and the end.
            if compte_num == startswith + endswith:
                return False

        if compte_num.startswith(startswith):
            return True
        return False

    def _compute_signed_sum_compte(self, pattern):
        """Compute the sum of all credits and all debits of accounts corresponding to
        the given pattern.
        """
        ret = 0
        for key, value in self.sum_ecritures_by_compte.items():
            if self._compte_pattern_match(key, pattern):
                ret += value
        return ret

    def compute_multiple_compte_sum(self, *comptes_patterns):
        """Aggregate multiple accounts matching pattern by summing them."""
        ret = Decimal("0.00")
        for pattern in comptes_patterns:
            ret += self._compute_signed_sum_compte(pattern)
        return ret

    def _get_row_dependencies(self, row):
        """Return a list of row identifiers necessary to calculate the given row."""
        if not row.formula:
            return []
        return re.split(r" \+ | - ", row.formula)

    def _init_plan_comptable(self, plan_type=None):
        """Initialize a "plan comptable" and return a new "plan comptable" structured as a dict."""
        # pylint: disable=protected-access
        plan_comptable = {}
        self._pc_file_uses_pc_type = False

        with open(self.pc_definition_filepath) as csvfile:
            csvread = csv.reader(csvfile)

            for row in csvread:
                if plan_type and plan_type not in row[6]:
                    continue

                row_el = PlanComptableElement(
                    compte_pattern=row[0],
                    num=row[1],
                    label=row[2],
                    opposite=(row[3] == "-"),
                    parent=row[4],
                    to_sum=(row[5] == "SOMME"),
                    plan_comptable=row[6],
                    formula=row[7].strip(),
                )
                plan_comptable[row_el.compte_pattern] = row_el

                if row[6] != "":
                    self._pc_file_uses_pc_type = True

        # Updates parent and childs
        for row in plan_comptable.values():
            row.child_identifiers += self._get_row_dependencies(row)
            if row.parent:
                plan_comptable[row.parent].child_identifiers.append(row.compte_pattern)

        return plan_comptable

    def _handle_custom(self, row):
        """Hardcoded specific custom computations (specific lines, in blue in the spec)."""
        # pylint: disable=protected-access
        good_custom = self.custom_fields_definition[row.compte_pattern]

        comptes = []
        lines = []
        custom_total_sum = Decimal("0.00")
        for compte_num, total_sum in self.sum_ecritures_by_compte.items():
            if not compte_num.startswith(good_custom[0]):
                continue
            for not_include in good_custom[1]:
                if self._compte_pattern_match(compte_num, not_include):
                    break
            else:
                custom_total_sum += total_sum
                if row.opposite:
                    total_sum = -total_sum
                comptes.append((compte_num, total_sum))

        # Sort the compte names to have a determinist result
        comptes.sort()
        for compte_num, total_sum in comptes:
            lines.append(
                PlanComptableElement(
                    compte_pattern=f"{row.compte_pattern}__{compte_num}",
                    num="",
                    label=self.compte_names[compte_num],
                    value=total_sum,
                    parent=row.parent,
                    opposite=row.opposite,
                )
            )

        if row.opposite:
            custom_total_sum = -custom_total_sum

        return lines, custom_total_sum

    def _handle_formula(self, formula, plan_comptable):
        """Handle the formula column to calculate some 'TITRE#'."""
        computed_value = Decimal("0.00")

        tokens = re.split(r"(\+|-)", formula.replace(" ", ""))
        for i, token in enumerate(tokens):
            if token in FORMULA_KEYWORDS:
                continue

            value = Decimal("0.00")
            if token in plan_comptable:
                value = plan_comptable[token].value
            else:
                value = self.compute_multiple_compte_sum(token)

            if i == 0:  # Consider an addition
                computed_value += value
            elif tokens[i - 1] == FORMULA_SUBTRACTION:
                computed_value -= value
            else:
                computed_value += value

        return computed_value

    def filter_compte_resultat_with_children(self, compte_patterns):
        """Filter the compte_resultat by compte_patterns and
        return the given compte_patterns with their children.
        """
        compte_resultat = {row.compte_pattern: row for row in self.compute_all()}

        def filter_rows(comptes, identifiers):
            rows = []
            for compte_pattern in identifiers:
                row = comptes.get(compte_pattern, None)
                if not row:
                    continue
                rows.append(compte_pattern)
                if row.child_identifiers:
                    rows += filter_rows(comptes, row.child_identifiers)
            return rows

        filtered = filter_rows(compte_resultat, compte_patterns)
        return [row for row in self.compute_all() if row.compte_pattern in filtered]

    def compute_all(self):
        """Compute all fields in the Compte de résultat."""
        if self._cached_results is not None:
            return self._cached_results

        plan_comptable = self._init_plan_comptable(self.plan_comptable_type)

        # Compute the "Plan Comptable" by dependencies order
        plan_comptable_graph = {
            row.compte_pattern: row.child_identifiers for row in plan_comptable.values()
        }
        sorted_compte_patterns = TopologicalSorter(plan_comptable_graph).static_order()

        for compte_pattern in sorted_compte_patterns:
            if compte_pattern not in plan_comptable:
                continue

            row = plan_comptable[compte_pattern]

            specific = False
            res = Decimal("0.00")

            if row.compte_pattern.startswith("CUSTOM#"):
                sub_rows, res = self._handle_custom(row)
                row.sub_rows += sub_rows
                specific = True

            if row.formula:
                res = self._handle_formula(row.formula, plan_comptable)
                res = -res if row.opposite else res
                specific = True

            if not specific:
                res = self.compute_multiple_compte_sum(compte_pattern)
                res = -res if row.opposite else res

            row.value += res

            if row.to_sum:
                plan_comptable[row.parent].value += row.value

        self._cached_results = []
        for row in plan_comptable.values():
            self._cached_results.append(row)
            self._cached_results += row.sub_rows
        return self._cached_results

    def compute_all_as_dict(self):
        """Return the compute_all as a dict compte_pattern -> value."""
        return {row.compte_pattern: row.value for row in self.compute_all()}

    def compute_compte_resultat(self):
        """Compute compte de resultat."""
        rows = self.compute_all()
        ret = []

        for row in rows:
            # Don't display blue lines sum
            if (
                row.compte_pattern.startswith("CUSTOM#")
                and "__" not in row.compte_pattern
            ):
                continue

            ret.append(
                {
                    "internal_label": row.compte_pattern,
                    "label": row.label,
                    "montant": row.value,
                    "parent": row.parent,
                }
            )

        return ret

    def compute_diff_credit_debit(self):
        """Compute the difference between credit and debit. It must be 0 if everything is valid."""
        return sum(ecriture.credit - ecriture.debit for ecriture in self.all_ecritures)

    def find_unused_ecritures(self):
        """Search for FECEcriture that are not used in the choosen plan_comptable."""
        for ecriture in self.ecritures:
            match = False

            for pattern in self._init_plan_comptable().values():
                if self._compte_pattern_match(
                    ecriture.compte_num, pattern.compte_pattern
                ):
                    match = True
                    if (
                        self._pc_file_uses_pc_type
                        and self.plan_comptable_type not in pattern.plan_comptable
                    ):
                        yield ecriture, True
                    break

            if not match:
                yield ecriture, False

    def compute_resultat_net(self):
        """Compute the resultat net by a different computation than in compute_all to check
        the file is valid."""
        return self._compute_signed_sum_compte("7") + self._compute_signed_sum_compte(
            "6"
        )
