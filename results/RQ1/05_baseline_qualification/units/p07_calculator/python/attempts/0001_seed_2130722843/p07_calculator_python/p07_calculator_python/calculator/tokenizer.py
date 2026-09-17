"""Tokenizer for arithmetic expressions.

This module provides the Token classes and the Tokenizer class
for converting arithmetic expressions into tokens.
"""

from typing import List, Union
from .errors import TokenizationError


class Token:
    """Marker base class for all token types."""


class NumberToken(Token):
    """Token representing a numeric value."""

    def __init__(self, value: float) -> None:
        """Initialize a NumberToken with a numeric value.

        Args:
            value: The numeric value represented by this token.
        """
        self.value = value


class OpToken(Token):
    """Token representing an operator."""

    def __init__(self, op: str) -> None:
        """Initialize an OpToken with an operator.

        Args:
            op: The operator symbol (+, -, *, /).

        Raises:
            ValueError: If the operator is not one of +, -, *, /.
        """
        if op not in "+-*/":
            raise ValueError(f"Invalid operator: {op}")
        self.op = op


class LParenToken(Token):
    """Token representing a left parenthesis."""

    def __init__(self) -> None:
        """Initialize an LParenToken."""
        pass


class RParenToken(Token):
    """Token representing a right parenthesis."""

    def __init__(self) -> None:
        """Initialize an RParenToken."""
        pass


class Tokenizer:
    """Converts arithmetic expressions into lists of tokens."""

    def tokenize(self, expression: str) -> List[Token]:
        """Convert an expression string into a list of tokens.

        Args:
            expression: A string containing a valid arithmetic expression.

        Returns:
            A list of tokens representing the expression.

        Raises:
            TokenizationError: If the expression contains invalid characters
                or malformed numbers.
        """
        if not expression:
            raise TokenizationError("Empty expression")

        tokens: List[Token] = []
        i = 0

        while i < len(expression):
            char = expression[i]

            # Skip whitespace
            if char.isspace():
                i += 1
                continue

            # Handle numbers (including decimals)
            if char.isdigit() or char == '.':
                start = i
                while i < len(expression) and (
                    expression[i].isdigit() or expression[i] == '.'
                ):
                    i += 1
                num_str = expression[start:i]
                try:
                    # Try integer first, then float
                    if '.' in num_str:
                        value = float(num_str)
                    else:
                        value = int(num_str)
                    tokens.append(NumberToken(value))
                except ValueError:
                    raise TokenizationError(
                        f"Malformed number: {num_str}"
                    )
                continue

            # Handle unary minus or plus
            if char in "+-" and (
                i == 0 or
                expression[i-1] in "(+-*/"
            ):
                # Look ahead to see if next character is a digit
                j = i + 1
                while j < len(expression) and expression[j].isspace():
                    j += 1
                if j < len(expression) and expression[j].isdigit():
                    # Found unary operator followed by digit, treat as negative
                    # We'll process the number part in the next iteration
                    # Add the operator as a token
                    tokens.append(OpToken(char))
                    i += 1
                    continue
                elif j < len(expression) and expression[j] == '.':
                    # Check if it's a decimal number starting with unary minus/plus
                    k = j + 1
                    while k < len(expression) and expression[k].isdigit():
                        k += 1
                    if k < len(expression) and expression[k] == '.':
                        # Invalid - more than one decimal point
                        raise TokenizationError(
                            f"Malformed number: {expression[i:j+1]}"
                        )
                    elif k == len(expression) or not expression[k].isdigit():
                        # This case handles unary plus/minus followed by decimal
                        # but we don't want to consume the decimal yet
                        # Let it be handled by the number detection logic
                        pass
                    else:
                        # Invalid decimal format
                        raise TokenizationError(
                            f"Malformed number: {expression[i:j+1]}"
                        )

            # Handle operators and parentheses
            if char in "+-*/()":
                if char == '(':
                    tokens.append(LParenToken())
                elif char == ')':
                    tokens.append(RParenToken())
                else:
                    tokens.append(OpToken(char))
                i += 1
                continue

            # Everything else is invalid
            raise TokenizationError(
                f"Unexpected character: '{char}'"
            )

        return tokens