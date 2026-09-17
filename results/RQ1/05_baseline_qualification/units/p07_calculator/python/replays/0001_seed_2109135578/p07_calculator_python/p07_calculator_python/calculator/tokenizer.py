"""Tokenizer for the calculator package."""

from typing import List
from .errors import TokenizationError


class Token:
    """Marker base class for all tokens."""


class NumberToken(Token):
    """Token representing a number."""

    value: float

    def __init__(self, value: float) -> None:
        """Initialize a number token.

        Args:
            value: The numeric value of the token.
        """
        self.value = value


class OpToken(Token):
    """Token representing an operator."""

    op: str

    def __init__(self, op: str) -> None:
        """Initialize an operator token.

        Args:
            op: The operator symbol (+, -, *, /).
        """
        self.op = op


class LParenToken(Token):
    """Token representing a left parenthesis."""

    def __init__(self) -> None:
        """Initialize a left parenthesis token."""


class RParenToken(Token):
    """Token representing a right parenthesis."""

    def __init__(self) -> None:
        """Initialize a right parenthesis token."""


class Tokenizer:
    """Tokenizer for arithmetic expressions."""

    def tokenize(self, expression: str) -> List[Token]:
        """Tokenize an arithmetic expression.

        Args:
            expression: The expression to tokenize.

        Returns:
            A list of tokens.

        Raises:
            TokenizationError: If the expression contains invalid characters
                or malformed numbers.
        """
        tokens: List[Token] = []
        i = 0
        length = len(expression)

        while i < length:
            char = expression[i]

            # Skip whitespace
            if char.isspace():
                i += 1
                continue

            # Handle numbers (including decimals and negative numbers)
            if char.isdigit() or char == '.':
                start = i
                has_decimal = False

                while i < length and (expression[i].isdigit() or expression[i] == '.'):
                    if expression[i] == '.':
                        if has_decimal:
                            raise TokenizationError("Malformed number")
                        has_decimal = True
                    i += 1

                # Check if we have a valid number
                if i == start:
                    raise TokenizationError("Malformed number")

                try:
                    value = float(expression[start:i])
                    tokens.append(NumberToken(value))
                except ValueError:
                    raise TokenizationError("Malformed number")

            # Handle operators
            elif char in '+-*/':
                # Check for unary minus or plus
                if char in '+-' and (
                    i == 0 or 
                    expression[i-1] in '(+-*/'
                ):
                    # This is a unary operator; we need to look ahead to get the number
                    j = i + 1
                    # Skip whitespace after the unary operator
                    while j < length and expression[j].isspace():
                        j += 1
                    
                    # Expect a number next
                    if j < length and (expression[j].isdigit() or expression[j] == '.'):
                        # Found a number after unary operator, treat it as a negative/positive number
                        # We'll handle this case by parsing the number directly
                        start = j
                        has_decimal = False
                        
                        while j < length and (expression[j].isdigit() or expression[j] == '.'):
                            if expression[j] == '.':
                                if has_decimal:
                                    raise TokenizationError("Malformed number")
                                has_decimal = True
                            j += 1
                        
                        # Check if we have a valid number
                        if j == start:
                            raise TokenizationError("Malformed number")
                        
                        try:
                            value = float(expression[start:j])
                            # Apply unary sign
                            if char == '-':
                                value = -value
                            tokens.append(NumberToken(value))
                            i = j
                            continue
                        except ValueError:
                            raise TokenizationError("Malformed number")
                    else:
                        # Not followed by a number, so it's a binary operator
                        tokens.append(OpToken(char))
                        i += 1
                else:
                    tokens.append(OpToken(char))
                    i += 1

            # Handle parentheses
            elif char == '(':
                tokens.append(LParenToken())
                i += 1
            elif char == ')':
                tokens.append(RParenToken())
                i += 1
            else:
                raise TokenizationError(f"Invalid character: {char}")

        return tokens