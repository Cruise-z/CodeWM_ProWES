# pyCodeObfuscator/patterns/AL/expression/format_percent_usage_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

import libcst as cst


class FormatPercentForm(str, Enum):
    """
    Two forms:
    - PERCENT:  "%s,%s" % (h, w)
    - FORMAT :  "{},{}".format(h, w) or "{0},{1}".format(h, w)
    """
    PERCENT = "percent"
    FORMAT = "format"


@dataclass
class FormatPercentUsageMatch:
    """
    Match information for one occurrence of "%s" % args  <->  "{}".format(args).
    """
    form: FormatPercentForm
    expr: cst.BaseExpression               # Entire expression, either BinaryOperation or Call
    template: cst.SimpleString             # String template literal
    args: List[cst.BaseExpression]         # Argument list in order


# --------- Utility functions for string internals, such as stripping quotes ---------


def _extract_string_inner_bounds(text: str) -> Tuple[int, int]:
    """
    Given SimpleString.value, find the left/right bounds of the string content: [inner_start, inner_end).

    Supports prefixes (u/r/b/...) plus single quotes, double quotes, and optional triple quotes.
    """
    n = len(text)
    i = 0
    # Skip the prefix
    while i < n and text[i] not in ("'", '"'):
        i += 1
    if i >= n:
        return 0, n

    # Triple quotes
    if text[i:i + 3] in ("'''", '"""'):
        quote = text[i:i + 3]
        inner_start = i + 3
        inner_end = text.rfind(quote)
        if inner_end < inner_start:
            inner_end = n
        return inner_start, inner_end

    # Single/double quotes
    quote = text[i]
    inner_start = i + 1
    inner_end = text.rfind(quote)
    if inner_end < inner_start:
        inner_end = n
    return inner_start, inner_end


def _get_string_inner(s: cst.SimpleString) -> str:
    text = s.value
    start, end = _extract_string_inner_bounds(text)
    return text[start:end]


def _replace_string_inner(s: cst.SimpleString, new_inner: str) -> cst.SimpleString:
    text = s.value
    start, end = _extract_string_inner_bounds(text)
    new_text = text[:start] + new_inner + text[end:]
    return s.with_changes(value=new_text)


# --------- Template-pattern checks ---------


def _check_percent_template(tmpl: cst.SimpleString, arg_count: int) -> Optional[str]:
    """
    Check whether this is a simple %s template:
      - only %s is allowed, not %d, %(name)s, %% and similar forms
      - the number of %s placeholders must equal the number of arguments

    Return the inner string on success, otherwise return None.
    """
    inner = _get_string_inner(tmpl)
    i = 0
    count = 0
    n = len(inner)

    while i < n:
        ch = inner[i]
        if ch == "%":
            if i + 1 >= n:
                return None
            nxt = inner[i + 1]
            # Only accept %s
            if nxt != "s":
                return None
            count += 1
            i += 2
        else:
            i += 1

    if count == 0 or count != arg_count:
        return None

    return inner


def _check_format_template(tmpl: cst.SimpleString, arg_count: int) -> Optional[str]:
    """
    Check whether this is a simple .format template:

      - Accepted:
          "{}"         automatic position
          "{0}", "{1}" explicit indices, which must run from 0..n-1 in order
      - Rejected:
          {name}, {0:.2f}, {0!r}, {{, }}, nested forms, and other complex variants
      - the number of placeholders must equal the number of arguments
    """
    inner = _get_string_inner(tmpl)
    i = 0
    n = len(inner)
    placeholders: List[tuple[str, Optional[int]]] = []  # (kind, index)

    while i < n:
        ch = inner[i]
        if ch == "{":
            # Find the matching '}'
            j = inner.find("}", i + 1)
            if j == -1:
                return None

            content = inner[i + 1:j]

            if content == "":
                # "{}"
                placeholders.append(("empty", None))
            elif content.isdigit():
                # "{0}" / "{1}" ...
                placeholders.append(("index", int(content)))
            else:
                # {name}, {0:.2f}, {0!r}, and other complex forms are not supported
                return None

            i = j + 1
        elif ch == "}":
            # A standalone '}' is invalid; this also excludes complex cases such as "}}" / "{{"
            return None
        else:
            i += 1

    if not placeholders or len(placeholders) != arg_count:
        return None

    kinds = {k for (k, _) in placeholders}
    # Mixing "{}" and "{0}" is not allowed
    if len(kinds) > 1:
        return None

    # If using "{0}/{1}/...", require [0,1,...,arg_count-1] in order
    if kinds == {"index"}:
        indices = [idx for (_, idx) in placeholders if idx is not None]
        if indices != list(range(arg_count)):
            return None

    return inner


def _extract_args_from_percent_right(
    expr: cst.BaseExpression,
) -> Optional[List[cst.BaseExpression]]:
    """
    Extract arguments from "%s" % right:
      - if right is a Tuple, use each element's .value
      - otherwise treat it as a single argument
    """
    if isinstance(expr, cst.Tuple):
        return [elt.value for elt in expr.elements]
    else:
        # Single argument
        return [expr]


# --------- Main matching function ---------


def match_format_percent_usage(
    expr: cst.BaseExpression,
) -> Optional[FormatPercentUsageMatch]:
    """
    Try to match on an expression:
      - "%s,%s" % (h, w)
      - "{},{}".format(h, w)
      - "{0},{1}".format(h, w)
    """
    # 1) "%s" % args
    if isinstance(expr, cst.BinaryOperation) and isinstance(expr.operator, cst.Modulo):
        left = expr.left
        right = expr.right
        if not isinstance(left, cst.SimpleString):
            return None

        args = _extract_args_from_percent_right(right)
        if args is None:
            return None

        inner = _check_percent_template(left, len(args))
        if inner is None:
            return None

        return FormatPercentUsageMatch(
            form=FormatPercentForm.PERCENT,
            expr=expr,
            template=left,
            args=args,
        )

    # 2) "{}".format(args) or "{0}".format(args)
    if isinstance(expr, cst.Call):
        func = expr.func
        if not isinstance(func, cst.Attribute):
            return None
        if not isinstance(func.attr, cst.Name) or func.attr.value != "format":
            return None

        tmpl = func.value
        if not isinstance(tmpl, cst.SimpleString):
            return None

        # Do not accept keyword arguments or *args
        if any(arg.keyword is not None for arg in expr.args):
            return None
        if any(arg.star for arg in expr.args):
            return None

        args = [arg.value for arg in expr.args]
        inner = _check_format_template(tmpl, len(args))
        if inner is None:
            return None

        return FormatPercentUsageMatch(
            form=FormatPercentForm.FORMAT,
            expr=expr,
            template=tmpl,
            args=args,
        )

    return None
