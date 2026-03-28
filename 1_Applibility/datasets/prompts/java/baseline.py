from typing import Final

baseline: Final[str] = """
Goal
- Produce a tiny Java 11 application that is self-tested at runtime. The repository must contain exactly 2 files.

Hard Rules (non-negotiable)
- Language: Java 11 ONLY (no preview; no Java 12+ features).
- Build tool: Maven ONLY.
- Package and main class are specified by the project module.
- EXACTLY 2 files in the repo (no others):
  1) pom.xml
  2) src/main/java/<package>/<MainClass>.java
- No external assets/resources/config/scripts/README.
- Rendering (if any) must use only standard Java 11 APIs. Avoid external libraries.
- Use classic switch (case + break). DO NOT use switch expressions (case ->), yield, text blocks, records, sealed, pattern matching, or var in public APIs.
- Must not crash in headless mode: if headless, do not create a window but keep core logic runnable.

Build & Run (baseline)
- maven-compiler-plugin: <source>11</source>, <target>11</target>, <release>11</release>; no preview flags.
- exec-maven-plugin: runs <package>.<MainClass>.
- Commands:
  - Run app + self-tests: mvn -q -DskipTests exec:java -Dexec.mainClass=<package>.<MainClass>

Test Architecture (capability-based, NOT fixed names)
Provide minimal in-class test hooks (public or package-private methods, or a nested static test harness) enabling:
  1) CONTROL: change controllable inputs/state (e.g., direction or moves) with domain rules enforced; reset/restart to initial state.
  2) STEP: advance exactly one deterministic logic tick (the same logic used by the runtime loop/scheduler) without relying on sleeps.
  3) INSPECT: read core observables required for assertions (e.g., primary entity position, counters/scores/length, in-game or running status, and a non-null scheduler/timer if applicable).
  4) DETERMINISM (recommended): allow fixing randomness (seed) or overriding specific spawn/placement to build stable scenarios.
Do NOT prescribe concrete names. At the top of the source file, add a short **Public/Test API Summary** comment listing the chosen public interfaces (signatures + meaning) used by self-tests.

Self-Tests (in the same source file)
- Implement a nested static self-test suite (e.g., SelfTest) with multiple focused checks: initial state, legal/illegal control changes, state transitions affecting counters, boundary/self-constraint failures, and restart.
- Each failing check should throw AssertionError (no reflection; no access to private members except via the test hooks).
- Provide `SelfTest.runAll(<MainClass> app)` that executes all tests and prints a concise summary.
- **Self-Tests suite MUST IN <MainClass>!!!**

Main Orchestration (baseline)
- main(String[] args):
  1) Construct the app instance and start its logic loop/scheduler.
  2) If NOT headless, create and show a window (e.g., Swing) safely; if headless, skip window creation.
  3) After initialization (e.g., via SwingUtilities.invokeLater or a one-shot scheduler), run `SelfTest.runAll(...)`.
  4) On any AssertionError: print stack trace and `System.exit(1)`; on success: print `ALL SELF-TESTS PASSED` and continue running (or exit gracefully in headless mode).

Output Policy (baseline)
- Output ONLY the two files’ contents (pom.xml, <MainClass>.java). Keep code concise and self-contained. Avoid sleeps/brittle timing in tests.

Acceptance Checklist (baseline)
- ✅ Exactly 2 files at the exact paths; placeholders resolved to <package>/<MainClass>.
- ✅ Compiles with Java 11; no preview; runs via exec-maven-plugin.
- ✅ No external resources; standard Java APIs only.
- ✅ Public/Test API Summary present and consistent with self-tests.
- ✅ Self-tests cover initial state, control rules, state transitions, boundary/self-constraint failures, and restart.
- ✅ Headless execution does not crash; failures exit non-zero; success prints the fixed pass message.
"""