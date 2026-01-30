from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Todo list App, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

=============================
PROJECT MODULE: Todo List App
=============================

Package & Paths

* Package: com.example.todo
* Main class: TodoApp
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/todo/TodoApp.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (Todo)

* Task model:

  * Fields (minimum): `id` (monotonic long or UUID string), `title` (non-empty), `completed` (boolean), `createdAt`, `updatedAt`.
  * Optional but recommended: `dueAt` (nullable), `priority` (LOW/MED/HIGH), `notes` (short text).
* Core operations:

  * **Create**: validate non-empty title; set `completed=false`; set timestamps; assign unique `id`.
  * **Read**: get by `id`; list all.
  * **Update**: edit title/dueAt/priority/notes; toggle `completed`; update `updatedAt`. Preserve `createdAt`.
  * **Delete**: remove by `id`; provide “clear completed” to remove all completed tasks.
* Filtering & sorting:

  * Filters: ALL, ACTIVE (not completed), COMPLETED, OVERDUE (dueAt < now and not completed).
  * Sorting: by `dueAt` ascending (nulls last), then by `priority` (HIGH→LOW), then by `createdAt` ascending. Document the exact ordering.
* Search:

  * Case-insensitive substring match over `title` and optionally `notes`.
* UI:

  * Console menu or minimal Swing panel (list + controls) is acceptable.
  * Must **not** crash in headless mode; skip window creation if headless.
* Determinism:

  * Deterministic `Clock`/time supplier hook for timestamps and overdue checks.
  * Deterministic ID generator (configurable start/seed).

Keep Typical Single-File Architecture (Todo)

* Single source file `TodoApp.java` containing:

  * Private state: in-memory store (e.g., `Map<Long, Task>` + `ArrayList<Long>` for order), `Clock`/time supplier, ID generator, active filter/search state.
  * Private helpers: validation (`requireNonEmptyTitle`), normalization, filtering/sorting pipelines, rendering (if GUI), CLI command routing (if console).
  * Nested `Task` class (POJO) and optional small enums (`Priority`, `Filter`).
* Without exposing raw internals, add minimal **test hooks** and a nested **self-test suite** per the BASELINE. Prefer thin wrappers that expose capabilities (create/update/toggle/delete/list/filter/sort/search/reset/time control) rather than leaking collections.

Todo-Specific Test Guidance

* Create:

  * Valid title → task persisted with `completed=false`, timestamps set, unique `id`.
  * Blank title → throws documented exception (`IllegalArgumentException`) with a clear message.
* Update & toggle:

  * Edit title/notes/priority/dueAt updates only those fields and bumps `updatedAt`; `createdAt` unchanged.
  * Toggle completion flips `completed` and updates `updatedAt`.
* Filtering & sorting:

  * With fixed `Clock`, verify ACTIVE/COMPLETED/OVERDUE sets are correct.
  * Verify sorting order: `dueAt` asc (nulls last), then `priority` HIGH→LOW, then `createdAt` asc; confirm stable after updates.
* Search:

  * Case-insensitive match over title/notes returns the expected subset; combining search + filter yields intersection.
* Delete & clear:

  * Deleting unknown `id` is a no-op or throws per documented contract (choose and document).
  * “Clear completed” removes only completed tasks; active ones remain.
* Determinism:

  * With injected `Clock` and ID seed, sequences of operations yield stable IDs and timestamps; overdue calculations match expectations.
* Restart:

  * Reset hook clears storage, resets ID generator and `Clock`; subsequent create behaves like a fresh app.

pom.xml Requirements (Todo)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.todo.TodoApp`.
* Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (Todo)

* Output exactly two complete files, in this order:

  1. pom.xml (full content)
  2. src/main/java/com/example/todo/TodoApp.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests use them)
"""
