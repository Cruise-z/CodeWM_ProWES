"""Shunting-yard algorithm implementation for converting infix to RPN and evaluating RPN."""

from typing import List
from .tokenizer import Token, NumberToken, OpToken, LParenToken, RParenToken
from .errors import ParseError, EvaluationError


def to_rpn(tokens: List[Token]) -> List[Token]:
    """Convert a list of tokens to Reverse Polish Notation (RPN) using shunting-yard algorithm.

    Args:
        tokens: List of tokens representing an arithmetic expression.

    Returns:
        List of tokens in RPN order.

    Raises:
        ParseError: If the expression has mismatched parentheses or other structural issues.
    """
    output: List[Token] = []
    operator_stack: List[Token] = []

    # Define operator precedence
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
    
    # Define right-associative operators
    right_associative = set()

    for token in tokens:
        if isinstance(token, NumberToken):
            output.append(token)
        elif isinstance(token, OpToken):
            op = token.op
            # While there is an operator at the top of the stack with greater precedence,
            # or equal precedence and left-associative, pop it to output
            while (operator_stack and 
                   operator_stack[-1] != LParenToken() and
                   precedence.get(operator_stack[-1].op, 0) >= precedence.get(op, 0) and
                   op not in right_associative):
                output.append(operator_stack.pop())
            operator_stack.append(token)
        elif isinstance(token, LParenToken):
            operator_stack.append(token)
        elif isinstance(token, RParenToken):
            # Pop operators to output until we find the matching left parenthesis
            while operator_stack and not isinstance(operator_stack[-1], LParenToken):
                output.append(operator_stack.pop())
            if not operator_stack:
                raise ParseError("Mismatched parentheses")
            # Remove the left parenthesis
            operator_stack.pop()
    
    # Pop any remaining operators
    while operator_stack:
        if isinstance(operator_stack[-1], (LParenToken, RParenToken)):
            raise ParseError("Mismatched parentheses")
        output.append(operator_stack.pop())

    return output


def eval_rpn(rpn: List[Token]) -> float:
    """Evaluate a list of tokens in Reverse Polish Notation.

    Args:
        rpn: List of tokens in RPN order.

    Returns:
        The numerical result of evaluating the expression.

    Raises:
        EvaluationError: If there are insufficient operands or division by zero.
    """
    if not rpn:
        raise EvaluationError("Empty expression")

    stack: List[float] = []

    for token in rpn:
        if isinstance(token, NumberToken):
            stack.append(token.value)
        elif isinstance(token, OpToken):
            if len(stack) < 2:
                raise EvaluationError("Insufficient operands for operator")
            
            b = stack.pop()
            a = stack.pop()
            
            if token.op == '+':
                result = a + b
            elif token.op == '-':
                result = a - b
            elif token.op == '*':
                result = a * b
            elif token.op == '/':
                if b == 0:
                    raise EvaluationError("Division by zero")
                result = a / b
            else:
                raise EvaluationError(f"Unknown operator: {token.op}")
            
            stack.append(result)
    
    if len(stack) != 1:
        raise EvaluationError("Invalid expression")
        
    return stack[0]