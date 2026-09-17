"""Parsing and evaluation engine for the calculator package."""

from typing import List
from .tokenizer import Token, NumberToken, OpToken, LParenToken, RParenToken
from .errors import ParseError, EvaluationError


def to_rpn(tokens: List[Token]) -> List[Token]:
    """Convert a list of tokens to Reverse Polish Notation using Shunting-yard algorithm.

    Args:
        tokens: A list of tokens to convert.

    Returns:
        A list of tokens in Reverse Polish Notation.

    Raises:
        ParseError: If the token sequence is malformed (e.g., mismatched parentheses,
            or incorrect operator usage).
    """
    output: List[Token] = []
    operator_stack: List[Token] = []

    # Define operator precedence
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
    right_associative = set()

    for token in tokens:
        if isinstance(token, NumberToken):
            output.append(token)
        elif isinstance(token, OpToken):
            op = token.op
            while (operator_stack and
                   operator_stack[-1] is not LParenToken() and
                   isinstance(operator_stack[-1], OpToken) and
                   (precedence[operator_stack[-1].op] > precedence[op] or
                    (precedence[operator_stack[-1].op] == precedence[op] and
                     op not in right_associative))):
                output.append(operator_stack.pop())
            operator_stack.append(token)
        elif isinstance(token, LParenToken):
            operator_stack.append(token)
        elif isinstance(token, RParenToken):
            while (operator_stack and
                   not isinstance(operator_stack[-1], LParenToken)):
                output.append(operator_stack.pop())
            if not operator_stack:
                raise ParseError("Mismatched parentheses")
            operator_stack.pop()  # Remove the LParenToken

    while operator_stack:
        if isinstance(operator_stack[-1], (LParenToken, RParenToken)):
            raise ParseError("Mismatched parentheses")
        output.append(operator_stack.pop())

    return output


def eval_rpn(rpn: List[Token]) -> float:
    """Evaluate a list of tokens in Reverse Polish Notation.

    Args:
        rpn: A list of tokens in Reverse Polish Notation.

    Returns:
        The result of the evaluation.

    Raises:
        EvaluationError: If there is a division by zero or an invalid operation.
    """
    stack: List[float] = []

    for token in rpn:
        if isinstance(token, NumberToken):
            stack.append(token.value)
        elif isinstance(token, OpToken):
            if len(stack) < 2:
                raise EvaluationError("Invalid expression")

            b = stack.pop()
            a = stack.pop()
            op = token.op

            if op == '+':
                result = a + b
            elif op == '-':
                result = a - b
            elif op == '*':
                result = a * b
            elif op == '/':
                if b == 0:
                    raise EvaluationError("Division by zero")
                result = a / b
            else:
                raise EvaluationError(f"Unknown operator: {op}")

            stack.append(result)

    if len(stack) != 1:
        raise EvaluationError("Invalid expression")

    return stack[0]