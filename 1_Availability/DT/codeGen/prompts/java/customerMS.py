from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (Customer Management System, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

==========================================
PROJECT MODULE: Customer Management System
==========================================

Package & Paths

* Package: com.example.cms
* Main class: CustomerApp
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/cms/CustomerApp.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (CMS)

* Domain Model (single entity):

  * `Customer` fields (minimum): `id` (monotonic long or UUID string), `name`, `email`, `phone`, `status` (ACTIVE/INACTIVE), `createdAt`, `updatedAt`.
  * Optional: `notes` (short free text).
* Core Operations (CRUD):

  * **Create**: validate non-empty `name`, valid `email` format, normalize `phone` (digits + optional `+`), enforce **unique email** among ACTIVE customers; set `status=ACTIVE`; set timestamps.
  * **Read**: get by `id`; list all; list with **filters** (by `status`, name substring case-insensitive, email exact); optional limit/offset parameters.
  * **Update**: partial update; cannot change `id`; preserve `createdAt`; update `updatedAt`; re-validate `email` uniqueness and format; re-normalize `phone`.
  * **Delete**: implement **soft delete** (set `status=INACTIVE` and update `updatedAt`). Hard delete is optional; if implemented, document behavior.
* Search & Sorting:

  * Search by name substring (case-insensitive).
  * Filter by `status`.
  * Sort by `createdAt` ascending/descending (document default).
* Persistence:

  * **In-memory only** using standard collections (e.g., `Map<Long, Customer>` + `ArrayList`); **no I/O**, **no external libs**.
* UI:

  * Console menu or minimal Swing panel is acceptable. Must **not** crash in headless mode; skip window creation when headless.
  * Provide clear command handlers for create/read/update/delete/search/list/sort/restart.
* Determinism:

  * Deterministic ID generator (e.g., monotonic `long` starting from configurable seed).
  * Deterministic `Clock`/time source hook for timestamps used by self-tests.

Keep Typical Single-File Architecture (CMS)

* Single source file `CustomerApp.java` containing:

  * Private state: in-memory store, ID generator, a `Clock`/time supplier, configuration (e.g., default sort).
  * Private helpers: validation (`validateEmail`, `normalizePhone`, `requireNonEmptyName`), converters/formatters, predicates for search/filter, and console routing if a CLI is provided.
  * Nested `Customer` class (POJO) and optional tiny enums (`Status`).
* Without exposing raw internals, add minimal **test hooks** and a nested **self-test suite** (per BASELINE). Prefer thin wrappers that expose capabilities (control/inspect/reset/determinism) rather than leaking collections.

CMS-Specific Test Guidance

* Create:

  * Valid customer → persisted with ACTIVE status, non-null timestamps, normalized phone, unique ID.
  * Invalid email / blank name → throws documented exception (e.g., `IllegalArgumentException`) with clear message.
  * Duplicate email (ACTIVE) → rejected; after soft-deleting original, creating with same email succeeds.
* Read/List/Search:

  * `findById` returns exact match; unknown ID returns empty/exception per documented contract.
  * Name substring search (case-insensitive) returns expected set; email exact filter works; status filter works.
  * Sorting by `createdAt` ascending/descending produces the expected order.
* Update:

  * Partial update changes only specified fields; `updatedAt` changes; `createdAt` preserved.
  * Changing to an email already used by another ACTIVE customer is rejected.
* Delete (Soft):

  * Soft-deleted customer becomes INACTIVE; appears only when filtering by INACTIVE; updatedAt changes.
* Determinism:

  * With injected `Clock` and ID seed, sequences of operations yield stable IDs and timestamps for assertions.
* Restart:

  * Reset hook clears storage, resets ID generator and clock; subsequent create behaves like a fresh app.

pom.xml Requirements (CMS)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.cms.CustomerApp`.
* Do NOT add JUnit or any other dependencies; only these two files exist.

Output Style (CMS)

* Output exactly two complete files, in this order:

  1. pom.xml (full content)
  2. src/main/java/com/example/cms/CustomerApp.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests use them)
"""
