from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Calculator, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

==========================
PROJECT MODULE: Calculator
==========================

Package & Paths

* Package: com.example.calculator
* Main class: Calculator
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/calculator/Calculator.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (Calculator)

* Evaluate arithmetic expressions entered as strings.
* Supported syntax (minimum):

  * Numbers: integers and decimals (e.g., `0`, `3`, `-2`, `3.1415`). Optional leading `+`/`-`.
  * Operators: `+`, `-`, `*`, `/` with standard precedence (`*`/`/` > `+`/`-`) and left associativity.
  * Parentheses: `(` `)` to override precedence; nested parentheses allowed.
  * Whitespace: allowed anywhere and ignored by parsing.
* Numeric model:

  * Use precise decimal arithmetic (e.g., `java.math.BigDecimal`) with a sensible default `MathContext`/scale (e.g., DECIMAL64, HALF_EVEN).
  * Division must specify explicit rounding behavior; division by zero must raise an error.
* Results & formatting:

  * Produce a canonical string/decimal result (trim trailing zeros when appropriate or document chosen formatting).
  * Maintain a running score/history of evaluated expressions with results (most recent N entries, N≥10 recommended).
* Errors:

  * Invalid tokens, mismatched parentheses, or other parse errors should produce clear error messages (e.g., `IllegalArgumentException`).
  * Arithmetic errors (e.g., divide-by-zero) should be surfaced distinctly (e.g., `ArithmeticException` or well-documented error).
* UI (optional):

  * If a GUI is provided, use a minimal Swing panel with an input field and an “Evaluate” action; must not crash in headless mode (skip window creation when headless).
  * A console-only implementation is acceptable as long as `main` runs self-tests per the BASELINE.

Keep Typical Single-File Architecture (Calculator)

* Single source file `Calculator.java` containing:

  * Private state (e.g., evaluation context, history list, optional memory registers).
  * Private helpers for lexing/tokenizing, parsing (shunting-yard or recursive descent), and evaluation.
  * Optional nested types for tokens/AST nodes.
  * Optional minimal Swing UI (panel + input + output label) guarded against headless mode.
* Without exposing raw internals, add minimal **test hooks** and a nested **self-test suite** as required by the BASELINE. Prefer thin wrappers that provide capabilities (evaluate/reset/inspect/history/determinism) rather than leaking fields.

Calculator-Specific Test Guidance

* Parsing & precedence:

  * Verify `2+3*4` == `14`, `(2+3)*4` == `20`, `3-2-1` == `0` (left associativity), unary minus (`-3*2` == `-6`).
  * Verify whitespace insensitivity: `  12  /  3  ` == `4`.
* Decimal accuracy:

  * Verify precise decimal behavior: `0.1+0.2` should equal `0.3` under the chosen BigDecimal rules (format expectations documented).
  * Verify rounding policy for division (e.g., `1/3`) matches documented MathContext/scale.
* Error handling:

  * Division by zero raises the documented exception.
  * Invalid inputs (e.g., `2+*3`, `((1+2)`) report clear parse errors.
* Determinism:

  * Results are deterministic for the same input and configuration; no time-based or random behavior.
  * Provide a hook to configure precision/scale/MathContext for tests.
* History:

  * After several evaluations, a history snapshot reflects inputs and results in order; clearing/resetting removes prior entries.
* Restart:

  * Reset hook restores a clean calculator state (clears history and any registers).

pom.xml Requirements (Calculator)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.calculator.Calculator`.
* Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (Calculator)

* Output exactly two complete files, in this order:
  1. pom.xml (full content)
  2. src/main/java/com/example/calculator/Calculator.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests use them)
"""
