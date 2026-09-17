"""Exception hierarchy for the calculator package."""

from typing import Final


class CalculatorError(Exception):
    """Base exception for all calculator-related errors."""


class TokenizationError(CalculatorError):
    """Raised when an expression cannot be tokenized due to invalid syntax."""


class ParseError(CalculatorError):
    """Raised when an expression cannot be parsed due to structural issues."""


class EvaluationError(CalculatorError):
    """Raised when an expression cannot be evaluated due to mathematical errors."""