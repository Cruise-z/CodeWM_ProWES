"""Exception hierarchy for the calculator package."""

from typing import Final


class CalculatorError(Exception):
    """Base exception for all calculator-related errors."""


class TokenizationError(CalculatorError):
    """Raised when an expression cannot be tokenized."""


class ParseError(CalculatorError):
    """Raised when an expression cannot be parsed."""


class EvaluationError(CalculatorError):
    """Raised when an expression cannot be evaluated."""