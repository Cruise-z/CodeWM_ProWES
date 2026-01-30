from typing import Final
from .baseline import baseline

# 简短描述，可自由修改
desc: Final[str] = "Build tiny Java project (QRCode Generator Detector, Maven, Java 11, strict 2-file repo)."

idea: Final[str] = f"""
========================
BASELINE
========================
{baseline}

=======================================
PROJECT MODULE: QRCodeGeneratorDetector
=======================================

Package & Paths

* Package: com.example.qr
* Main class: QRCodeGeneratorDetector
* File list (and ONLY these two):

  1. pom.xml
  2. src/main/java/com/example/qr/QRCodeGeneratorDetector.java
* Whitelist is exactly the two paths above; any other path/file is forbidden.

Functional Requirements (QR)

* Scope (single-version subset):

  * Implement **QR Code Version 1–L** only (21×21 modules, error correction level **L**).
  * Support **Byte mode (ISO-8859-1)**; optionally support Numeric and Alphanumeric modes if simple.
  * Respect quiet zone (≥ 4 modules), finder patterns, timing patterns; no alignment pattern for v1.
* Encoding (Generator):

  * Build the bit stream for Byte mode: mode indicator, character count, data bytes, terminator, pad to full data capacity with `11101100` / `00010001` alternation.
  * For v1-L: total codewords 26; ECC codewords 7; data codewords 19 (document these constants).
  * Implement **Reed–Solomon** over GF(256) with primitive poly 0x11D and α=2; generate 7 EC codewords using the standard generator polynomial for v1-L.
  * Place data+EC codewords in the v1 placement pattern (zigzag).
  * Apply one **mask pattern** (mask 0 is sufficient) OR choose the best of the 8 using the penalty rules (document choice). Write **format information** for level L and chosen mask (BCH(15,5)).
  * Render to a `BufferedImage` with configurable `moduleSize` (e.g., 8 px) and quiet zone; black/white pixels only. Save/load via `javax.imageio.ImageIO` (PNG/BMP). No external libraries.
* Decoding (Detector):

  * Input: `BufferedImage` (from file path or in-memory). Binarize via luminance threshold (e.g., per-pixel average or Otsu—simple threshold acceptable).
  * Assumptions to simplify: **upright** (no rotation), **no perspective skew**, sufficient contrast, image roughly cropped to QR with quiet zone visible. (State these assumptions in code comments.)
  * Locate module grid by estimating the QR bounding box using finder pattern positions (simple run-length ratio 1:1:3:1:1 checks) or by assuming the full image is the code; sample a 21×21 grid.
  * Read **format information**, recover the mask and level; unmask data; read codewords; **Reed–Solomon decode** to correct up to ⌊7/2⌋=3 codeword errors (or document the exact correction capability implemented).
  * Parse Byte mode payload and return decoded text (ISO-8859-1).
* CLI/GUI:

  * Provide a simple CLI menu or minimal Swing UI with two actions:

    * **Generate**: input text → render QR to image file (e.g., `out.png`) and show preview if not headless.
    * **Detect**: load image file → decode text → print/result label.
  * Must **not** crash in headless mode; skip window creation when `GraphicsEnvironment.isHeadless()`.

Keep Typical Single-File Architecture (QR)

* Single source file with private state and helpers, e.g.:

  * Constants for v1-L sizes, masks, format info tables; GF(256) log/antilog tables; generator polynomial for EC=7.
  * Private helpers: `encodeBytes(..)`, `rsEncode(..)`, `placeModules(..)`, `applyMask(..)`, `writeFormatInfo(..)`, `renderImage(..)`, `binarize(..)`, `locateGrid(..)`, `sampleGrid21(..)`, `readFormat(..)`, `unmask(..)`, `readCodewords(..)`, `rsDecode(..)`, `parseByteMode(..)`, plus tiny UI/CLI glue.
* Without exposing raw internals, add minimal **test hooks** and a nested **self-test suite** per BASELINE. Prefer thin wrappers exposing capabilities (encode/decode/inspect/grid/tweak) rather than leaking arrays.

QR-Specific Test Guidance

* Encode/Decode Roundtrip:

  * Roundtrip “HELLO WORLD” → render to `BufferedImage` → decode → equals input.
  * Roundtrip mixed bytes (e.g., `\u00A9ISO-8859-1`) under ISO-8859-1 → equals input bytes.
* Capacity & Padding:

  * Strings at/near v1-L Byte capacity (≤17 bytes after headers) encode successfully; padding alternation applied correctly.
* Mask & Format:

  * If using a fixed mask (e.g., mask 0), verify format bits correspond; if choosing best mask, verify penalty computation picks a valid mask and format matches.
* ECC Robustness:

  * Programmatically flip up to **3 codeword-level errors** (or equivalent module bits) and ensure decode succeeds after RS correction.
* Binarization & Sampling:

  * Downscale/upsample the rendered image (integer scaling), then decode; verify tolerance to small noise (e.g., add salt-and-pepper noise below threshold).
* File I/O:

  * Save PNG, reload via `ImageIO.read(..)`, then decode successfully.
* Determinism & Hooks:

  * Provide hooks to: get/set random seed (if used), flip specific module(s) for tests, emit/read the 21×21 bit matrix directly, and run a single “decode from matrix” path (bypassing image I/O) for pure logic tests.
* Restart:

  * A reset hook clears transient buffers/state so repeated runs behave identically.

pom.xml Requirements (QR)

* maven-compiler-plugin: Java 11 (`<source>11</source>`, `<target>11</target>`, `<release>11</release>`); no preview flags.
* exec-maven-plugin: main class is `com.example.qr.QRCodeGeneratorDetector`.
* Do NOT add ZXing or any other dependencies; implement the minimal v1-L stack in pure Java. Only these two files exist.

Output Style (QR)

* Output exactly two complete files, in this order:

  1. pom.xml (full content)
  2. src/main/java/com/example/qr/QRCodeGeneratorDetector.java (full content with a top-of-file **Public/Test API Summary** comment that documents the chosen test hooks and how the self-tests exercise encode/decode/ECC/binarization assumptions)
"""
