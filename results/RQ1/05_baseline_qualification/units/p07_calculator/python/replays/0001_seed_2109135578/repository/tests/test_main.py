"""Tests for the calculator package using the canonical public API."""

from calculator import evaluate, tokenize, History, CalculatorError, TokenizationError, ParseError, EvaluationError
from Main import run_demo


def test_run_demo_returns_dict_and_evaluate_correct() -> None:
    """Test that run_demo returns a dict and evaluate works correctly."""
    # Test run_demo returns a dict
    result = run_demo()
    assert isinstance(result, dict)
    
    # Test evaluate with precedence
    assert evaluate("2 + 3 * 4") == 14.0


def test_history_and_tokenization() -> None:
    """Test history recording and tokenization count."""
    # Create a history and evaluate an expression
    history = History()
    evaluate("(1 + 2) * 3", history)
    
    # Check history records
    records = history.records()
    assert len(records) == 1
    assert records[0] == ("(1 + 2) * 3", 9.0)
    
    # Check tokenization count
    tokens = tokenize("1 + 2.5")
    assert len(tokens) == 3


def test_error_handling() -> None:
    """Test error handling for various invalid inputs."""
    # Division by zero
    try:
        evaluate("1 / 0")
        assert False, "Should have raised EvaluationError"
    except EvaluationError:
        pass  # Expected
    
    # Invalid character
    try:
        evaluate("1 @ 2")
        assert False, "Should have raised TokenizationError"
    except TokenizationError:
        pass  # Expected
    
    # Blank input
    try:
        evaluate("   ")
        assert False, "Should have raised ParseError"
    except ParseError:
        pass  # Expected