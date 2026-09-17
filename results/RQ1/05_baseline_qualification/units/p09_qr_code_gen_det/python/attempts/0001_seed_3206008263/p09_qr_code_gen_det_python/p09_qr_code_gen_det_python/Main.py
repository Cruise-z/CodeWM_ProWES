"""Main runtime entry and demo for QR code implementation."""

from qr_code import generate, decode, detect, render


def run_demo() -> dict:
    """Run the QR code demo and return results as a dictionary.
    
    Returns:
        Dictionary containing demo results with keys:
        - text: Original text
        - decoded: Decoded text
        - detected: Detection result
        - size: Matrix size
        - rendered_lines: Number of rendered lines
    """
    # Generate QR code from text
    text = "CodeWM"
    matrix = generate(text)
    
    # Decode the matrix
    decoded = decode(matrix)
    
    # Detect if matrix is valid
    detected = detect(matrix)
    
    # Render the matrix
    rendered = render(matrix)
    rendered_lines = len(rendered.split('\n'))
    
    return {
        "text": text,
        "decoded": decoded,
        "detected": detected,
        "size": 21,
        "rendered_lines": rendered_lines
    }


def main():
    """Main entry point that prints demo result."""
    result = run_demo()
    
    # Print concise result
    print(f"Text: {result['text']}, Decoded: {result['decoded']}, "
          f"Detected: {result['detected']}, Size: {result['size']}, "
          f"Lines: {result['rendered_lines']}")


if __name__ == "__main__":
    main()