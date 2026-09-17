"""Public API for the calculator package."""

from typing import Optional

from .tokenizer import Tokenizer, Token
from .engine import to_rpn, eval_rpn
from .history import History
from .errors import ParseError


def tokenize(expression: str) -> list[Token]:
    """Tokenize an arithmetic expression.

    Args:
        expression: The expression to tokenize.

    Returns:
        A list of tokens.
    """
    return Tokenizer().tokenize(expression)


def evaluate(expression: str, history: Optional[History] = None) -> float:
    """Evaluate an arithmetic expression.

    Args:
        expression: The expression to evaluate.
        history: Optional history to record the result.

    Returns:
        The result of the evaluation.

    Raises:
        ParseError: If the expression is blank or cannot be parsed.
        Exception: Propagates TokenizationError, ParseError, and EvaluationError
            from underlying components.
    """
    # Validate input
    if not expression or not expression.strip():
        raise ParseError("Blank expression")

    # Tokenize
    tokens = tokenize(expression)

    # Convert to RPN
    rpn_tokens = to_rpn(tokens)

    # Evaluate
    result = eval_rpn(rpn_tokens)

    # Record in history if provided
    if history is not None:
        history.add(expression, result)

    return result