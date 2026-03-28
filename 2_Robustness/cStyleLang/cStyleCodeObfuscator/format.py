from enum import Enum
from dataclasses import dataclass, fields, is_dataclass
from typing import List, Optional, Tuple, Any
from difflib import SequenceMatcher
from math import tanh
from pathlib import Path
import subprocess
import textwrap
import re
import os

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR  = SCRIPT_PATH.parent 

def highlight_print(text, fg='white', bg='yellow', bold=True):
    color_codes = {
        'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
        'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37
    }
    bg_codes = {k: v + 10 for k, v in color_codes.items()}

    parts = ['\033[']
    if bold:
        parts.append('1;')
    parts.append(str(color_codes.get(fg, 37)))  # default to white

    if bg:
        parts.append(f';{bg_codes.get(bg, 40)}')  # default bg to black if unknown

    parts.append('m')
    parts.append(str(text))
    parts.append('\033[0m\n')

    print(''.join(parts))

def preprocess_code(code: str) -> str:
    """
    Preprocess Java and other C-style code strings:
    - Remove line breaks and indentation characters (\r \n \t, etc.)
    - Remove both single-line (//...) and multi-line (/*...*/) comments
    - Preserve string and character literals, including escaped characters
    - Output a clean single-line code string
    """

    _STRING_PLACEHOLDER = "__<STR:%d>__"
    literals: List[str] = []

    def freeze_literals(src: str) -> str:
        """Replace string and character literals with placeholders."""
        def _store(match):
            idx = len(literals)
            literals.append(match.group(0))
            return _STRING_PLACEHOLDER % idx

        pattern = r'"(?:\\.|[^"\\])*"' + r"|'(?:\\.|[^'\\])'"  # Supports both strings and chars
        return re.sub(pattern, _store, src)

    def remove_comments(src: str) -> str:
        """Remove single-line and multi-line comments."""
        no_block_comments = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
        no_line_comments = re.sub(r'//.*$', '', no_block_comments, flags=re.MULTILINE)
        return no_line_comments

    def collapse_whitespace(src: str) -> str:
        """Collapse all whitespace into a single space."""
        return re.sub(r'\s+', ' ', src).strip()

    def restore_literals(src: str) -> str:
        """Restore previously frozen string literals."""
        def _restore(match):
            idx = int(match.group(1))
            return literals[idx]
        return re.sub(r'__<STR:(\d+)>__', _restore, src)

    # === Execution flow ===
    code_frozen = freeze_literals(code)
    code_no_comments = remove_comments(code_frozen)
    code_flat = collapse_whitespace(code_no_comments)
    code_restored = restore_literals(code_flat)

    return code_restored

def format_func(class_name:str, code:str, lang:str) -> str:
    """
    1. Use google-java-format to format Java source code.
    2. Use javaparser-core-3.25.4.jar for custom Java formatting.
    3. Define formatting rules in RestoreJavaFormat.java.
    """
    toolpath = SCRIPT_DIR / "CodeFormat_adapter"
    code = preprocess_code(code)  # Preprocess the code by removing comments and extra spaces
    if lang == 'java':
        code = f"public class {class_name} {{\n{code}\n}}"
        code = code
        testjar_path = os.path.join(toolpath, "google-java-format-1.27.0-all-deps.jar")
        process = subprocess.Popen(
            ["java", "-jar", testjar_path, "--aosp", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        fcode, stderr = process.communicate(code)
        if process.returncode != 0:
            raise RuntimeError(f"Preprocessing failed: {stderr.strip()}")
        class_name = "RestoreJavaFormat"
        jar_path = f"{toolpath}:{toolpath}/javaparser-core-3.25.4.jar"
        process = subprocess.Popen(
            ["java", "-cp", jar_path, class_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        fcode, stderr = process.communicate(input=fcode)
        if process.returncode != 0:
            raise RuntimeError(f"Formatting failed: {stderr.strip()}")
        lines = fcode.splitlines()
        non_blank_lines = [line for line in lines if line.strip() != ""]
        fcode = "\n".join(non_blank_lines)
    else:
        fcode = code
    
    format_func = fcode
    return format_func

# 1. Normalize lines (with literal abstraction)
def semantically_normalize_line(line: str) -> str:
    """
    Normalize a code line while preserving code structure:
    - Remove spaces inside string literals (e.g., "error msg" → "errormsg")
    - Preserve structural whitespace in code
    - Lowercase and strip trailing semicolons
    """
    def extract_and_mask_literals(line: str):
        string_literals = {}
        pattern = r'(["\'])(.*?)(\1)'  # Match "..." or '...'
        idx = 0

        def replacer(match):
            nonlocal idx
            full_match = match.group(0)
            key = f"__STR{idx}__"
            string_literals[key] = full_match
            idx += 1
            return key

        masked_line = re.sub(pattern, replacer, line)
        return masked_line, string_literals

    def restore_literals(masked_line: str, string_literals: dict):
        for key, value in string_literals.items():
            cleaned = value[0] + value[1:-1].replace(' ', '') + value[-1]  # remove inner spaces
            masked_line = masked_line.replace(key, cleaned)
        return masked_line

    line = line.strip()
    masked_line, str_map = extract_and_mask_literals(line)
    masked_line = re.sub(r'\s+', ' ', masked_line)        # Collapse spaces
    masked_line = re.sub(r';+\s*$', '', masked_line)      # Remove trailing semicolons
    masked_line = masked_line.lower()
    normalized_line = restore_literals(masked_line, str_map)
    return normalized_line

# 2. Reverse token similarity with normalization
def extract_assignment_parts(line: str) -> Optional[Tuple[str, str]]:
    """
    Try to split a line into (lhs, rhs) if it's an assignment statement.
    Only works for simple single '=' assignments.
    """
    if '=' not in line:
        return None
    parts = line.split('=', 1)
    lhs = parts[0].strip()
    rhs = parts[1].strip()
    return lhs, rhs

def reversed_suffix_similarity(line1: str, line2: str) -> float:
    """
    Assignment-sensitive similarity function:
    - Boosts score when both lines are equivalent assignments (with or without type)
    - Falls back to reversed suffix similarity
    - Long matches rewarded more heavily with tanh scaling
    """
    s1 = semantically_normalize_line(line1)
    s2 = semantically_normalize_line(line2)

    # First try to extract assignment (var = value) parts
    assign1 = extract_assignment_parts(s1)
    assign2 = extract_assignment_parts(s2)

    # Strong match: identical assignment (var and value match)
    if assign1 and assign2 and assign1 == assign2:
        return 1.2

    # Partial match: same RHS, variable name matches with type prefix allowed
    if assign1 and assign2:
        lhs1, rhs1 = assign1
        lhs2, rhs2 = assign2
        if rhs1 == rhs2 and lhs1.endswith(lhs2):
            return 1.1

    # === Fallback: reversed suffix match ===
    rev1 = s1[::-1]
    rev2 = s2[::-1]

    match_len = 0
    for c1, c2 in zip(rev1, rev2):
        if c1 == c2:
            match_len += 1
        else:
            break

    if match_len == 0:
        return 0.0

    base_score = (match_len / max(len(s1), 1)) * (match_len / max(len(s2), 1))
    length_boost = tanh(match_len / 10)

    return base_score * length_boost

# 3. Dynamic-programming global alignment (Needleman-Wunsch)
def dp_align(A: List[str], B: List[str], gap_cost=0.3) -> Tuple[List[str], List[str]]:
    n, m = len(A), len(B)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]  # Record the traceback path

    # Initialize boundaries
    for i in range(1, n + 1):
        dp[i][0] = -i * gap_cost
        back[i][0] = 'up'
    for j in range(1, m + 1):
        dp[0][j] = -j * gap_cost
        back[0][j] = 'left'

    # Fill the DP table
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match = dp[i-1][j-1] + reversed_suffix_similarity(A[i-1], B[j-1])
            delete = dp[i-1][j] - gap_cost
            insert = dp[i][j-1] - gap_cost

            dp[i][j] = max(match, delete, insert)
            if dp[i][j] == match:
                back[i][j] = 'diag'
            elif dp[i][j] == delete:
                back[i][j] = 'up'
            else:
                back[i][j] = 'left'

    # Trace back
    alignedA, alignedB = [], []
    i, j = n, m
    while i > 0 or j > 0:
        if back[i][j] == 'diag':
            alignedA.append(A[i-1])
            alignedB.append(B[j-1])
            i -= 1
            j -= 1
        elif back[i][j] == 'up':
            alignedA.append(A[i-1])
            alignedB.append("")
            i -= 1
        else:  # 'left'
            alignedA.append("")
            alignedB.append(B[j-1])
            j -= 1

    return alignedA[::-1], alignedB[::-1]

# 4. Align wrapper with blank-line filtering
def align_CodeBlocks(code1: str, code2: str) -> Tuple[str, str]:
    lines1 = code1.splitlines()
    lines2 = code2.splitlines()
    
    aligned_clean1, aligned_clean2 = dp_align(lines1, lines2)
    return "\n".join(aligned_clean1), "\n".join(aligned_clean2)

def attach_lineNum_func(formatcode: str) -> str:
    lines = formatcode.splitlines()
    width = len(str(len(lines)))  # Compute the maximum line-number width
    numbered_lines = [
        f"{str(idx).rjust(width)} | {line}"
        for idx, line in enumerate(lines, start=1)
    ]
    return "\n".join(numbered_lines)

def print_nodeNText(node, prefix="", is_last=True):
    connector = "└── " if is_last else "├── "

    # Decide how to display the current node
    if node.type == "identifier" or node.type.endswith("_identifier") or node.type == "type_identifier":
        display = f'{node.type}'
    elif node.is_named:
        display = f"{node.type}"
    else:
        # Anonymous terminal: print the symbol directly (for example `{`, `;`, etc.)
        display = f'"{node.type}"'

    print(f"{prefix}{connector}{display}")

    # Recurse through child nodes
    child_prefix = prefix + ("    " if is_last else "│   ")
    child_count = len(node.children)
    for i, child in enumerate(node.children):
        is_last_child = (i == child_count - 1)
        print_nodeNText(child, child_prefix, is_last_child)

def print_nodeText(node, source_code, prefix="", is_last=True):
    # Prefix symbol for the current node
    connector = "└── " if is_last else "├── "

    # Get the current node text (avoid line breaks)
    text = source_code[node.start_byte:node.end_byte].strip().replace("\n", "\\n")
    if node.type == "identifier" or node.type.endswith("_identifier") or node.type == "type_identifier":
        display = f'{node.type} "{text}"'
    elif node.is_named:
        display = f"{node.type}"
    else:
        display = f'"{text}"'

    print(f"{prefix}{connector}{display}")

    # Process child nodes
    child_prefix = prefix + ("    " if is_last else "│   ")
    child_count = len(node.children)
    for i, child in enumerate(node.children):
        is_last_child = (i == child_count - 1)
        print_nodeText(child, source_code, child_prefix, is_last_child)

def printAST(parser, format_code: str, lang: str, text:bool=False):
    tree = parser.parse(format_code.encode("utf8"))
    root = tree.root_node
    if text:
        print_nodeText(root, format_code)
    else:
        print_nodeNText(root)

# Format a single entity as a string
def field_formatter(entity: Any, field) -> str:
    name = field.name
    value = getattr(entity, name)

    #! For renameableEntity entities
    if name == "scope" and isinstance(value, list):
        return f"  - scope: {' -> '.join(value)}"
    elif name == "modifiers" and value:
        return f"  - modifiers: {', '.join(value)}"
    elif name == "decPos":
        return (
            f"  - declared at line {value[1]}: {value[0]}"
            if value else
            "  - declared at: [unknown]"
        )
    elif name == "initPos":
        return (
            f"  - initialized at line {value[1]}: {value[0]}"
            if value else
            "  - initialized at: [unknown]"
        )
    elif name == "useFPos":
        return (
            f"  - first used at line {value[1]}: {value[0]}"
            if value else
            "  - first used at: [not found]"
        )
    #! For entities shared by all diffTag variants
    elif name == "strategy":
        return f"  - strategy: \n{textwrap.indent(value, '    ')}"
    #! For diffTag1_2 entities
    elif name == "decPosDiff":
        if value[0] and value[1]:
            return f"  - declared at line: {value[0][1]}: {value[0][0]}\n    →obfuscated to line {value[1][1]}: {value[1][0]}"
        else:
            return "  - declared at: [unknown]"
    elif name == "initPosDiff":
        if value[0] and value[1]:
            return f"  - first init at line: {value[0][1]}: {value[0][0]}\n    →obfuscated to line {value[1][1]}: {value[1][0]}"
        else:
            return "  - first init at: [unknown]"
    else:
        return f"  - {name}: {value}"

def format_entity(entity: Any) -> str:
    if not is_dataclass(entity):
        raise TypeError("format_entity() expects a dataclass instance.")

    kind = getattr(entity, "kind", "[unknown kind]")
    entityName = getattr(entity, "entity", "[unknown name]")

    lines = [f"[{kind}] {entityName}"]

    for field in fields(entity):
        if field.name in ("kind", "entity"):
            continue
        lines.append(field_formatter(entity, field))

    lines.append("")
    return "\n".join(lines)
