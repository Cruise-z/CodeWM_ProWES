"""Tests for the calculator package and Main.py demo."""

from calculator import evaluate, tokenize, History, CalculatorError, TokenizationError, ParseError, EvaluationError
from Main import run_demo


def test_run_demo_returns_dict_and_evaluate_correct():
    """Test that run_demo returns a dict and evaluate produces correct results."""
    # Test run_demo returns a dict
    result = run_demo()
    assert isinstance(result, dict)
    
    # Test evaluate with precedence
    assert evaluate("2 + 3 * 4") == 14.0


def test_history_and_tokenization():
    """Test history recording and tokenization count."""
    # Create a history and evaluate an expression
    history = History()
    evaluate("(1 + 2) * 3", history)
    
    # Check that history has exactly one record
    records = history.records()
    assert len(records) == 1
    assert records[0] == ("(1 + 2) * 3", 9.0)
    
    # Check tokenization count for '1 + 2.5'
    tokens = tokenize("1 + 2.5")
    assert len(tokens) == 3


def test_error_handling():
    """Test that appropriate errors are raised for invalid inputs."""
    # Division by zero should raise EvaluationError
    try:
        evaluate("1 / 0")
        assert False, "Expected EvaluationError"
    except EvaluationError:
        pass
    
    # Invalid character should raise TokenizationError
    try:
        evaluate("1 @ 2")
        assert False, "Expected TokenizationError"
    except TokenizationError:
        pass
    
    # Blank input should raise ParseError
    try:
        evaluate("   ")
        assert False, "Expected ParseError"
    except ParseError:
        pass