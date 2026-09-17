"""Entry point for the calculator application."""

from calculator import evaluate, History


def run_demo() -> dict:
    """Run a demonstration of the calculator functionality.

    Returns:
        A dictionary containing the expression, result, and history length.
    """
    # Create a history instance
    history = History()
    
    # Evaluate a fixed expression
    expression = "(1 + 2) * 3"
    result = evaluate(expression, history)
    
    # Return the results
    return {
        "expression": expression,
        "result": result,
        "history_len": len(history)
    }


if __name__ == "__main__":
    # Run the demo and print the result
    demo_result = run_demo()
    print(demo_result["result"])