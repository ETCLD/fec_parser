"""Errors for fec_parser module"""

from collections import namedtuple


class BadFECFileError(Exception):
    """Exception raised when a file is not a valid FEC."""


FECParserError = namedtuple("FECParserError", ["filename", "line", "message"])
