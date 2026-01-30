# pyCodeObfuscator/patterns/AL/expression/format_percent_usage_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

import libcst as cst


class FormatPercentForm(str, Enum):
    """
    两种形态：
    - PERCENT:  "%s,%s" % (h, w)
    - FORMAT :  "{},{}".format(h, w) 或 "{0},{1}".format(h, w)
    """
    PERCENT = "percent"
    FORMAT = "format"


@dataclass
class FormatPercentUsageMatch:
    """
    "%s" % args  <->  "{}".format(args) 的一次命中信息。
    """
    form: FormatPercentForm
    expr: cst.BaseExpression               # 整个表达式（BinaryOperation 或 Call）
    template: cst.SimpleString             # 字符串模板字面量
    args: List[cst.BaseExpression]         # 参数列表（按顺序）


# --------- 字符串内部内容工具函数（去掉引号等） ---------


def _extract_string_inner_bounds(text: str) -> Tuple[int, int]:
    """
    从 SimpleString.value 文本中，找出字符串内容部分的左右边界 [inner_start, inner_end)。

    支持前缀 (u/r/b/...) + 单引号/双引号 + 可选三引号。
    """
    n = len(text)
    i = 0
    # 跳过前缀
    while i < n and text[i] not in ("'", '"'):
        i += 1
    if i >= n:
        return 0, n

    # 三引号
    if text[i:i + 3] in ("'''", '"""'):
        quote = text[i:i + 3]
        inner_start = i + 3
        inner_end = text.rfind(quote)
        if inner_end < inner_start:
            inner_end = n
        return inner_start, inner_end

    # 单/双引号
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


# --------- 模板模式检查 ---------


def _check_percent_template(tmpl: cst.SimpleString, arg_count: int) -> Optional[str]:
    """
    检查是否是简单的 %s 模板：
      - 只能出现 %s（不支持 %d、%(name)s、%% 等）
      - %s 个数 == 参数个数

    满足时返回 inner 字符串；否则返回 None。
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
            # 只接受 %s
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
    检查是否是“简单”的 .format 模板：

      - 只接受：
          "{}"         自动位置
          "{0}", "{1}" 显式下标（必须从 0..n-1 且顺序与参数一致）
      - 不允许：
          {name}, {0:.2f}, {0!r}, {{, }}, 嵌套等复杂形式
      - 占位符个数 == 参数个数
    """
    inner = _get_string_inner(tmpl)
    i = 0
    n = len(inner)
    placeholders: List[tuple[str, Optional[int]]] = []  # (kind, index)

    while i < n:
        ch = inner[i]
        if ch == "{":
            # 找到对应的 '}'
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
                # {name}, {0:.2f}, {0!r}, 等复杂形式：不支持
                return None

            i = j + 1
        elif ch == "}":
            # 孤立的 '}' 视为非法（也排除 "}}"/"{{" 等复杂用法）
            return None
        else:
            i += 1

    if not placeholders or len(placeholders) != arg_count:
        return None

    kinds = {k for (k, _) in placeholders}
    # 不能混用 "{}" 和 "{0}"
    if len(kinds) > 1:
        return None

    # 如果是 "{0}/{1}/..."，要求是 [0,1,...,arg_count-1] 且按顺序出现
    if kinds == {"index"}:
        indices = [idx for (_, idx) in placeholders if idx is not None]
        if indices != list(range(arg_count)):
            return None

    return inner


def _extract_args_from_percent_right(
    expr: cst.BaseExpression,
) -> Optional[List[cst.BaseExpression]]:
    """
    从 "%s" % right 中提取参数：
      - right 为 Tuple -> 每个元素的 .value
      - 否则视为单个参数
    """
    if isinstance(expr, cst.Tuple):
        return [elt.value for elt in expr.elements]
    else:
        # 单个参数
        return [expr]


# --------- 主匹配函数 ---------


def match_format_percent_usage(
    expr: cst.BaseExpression,
) -> Optional[FormatPercentUsageMatch]:
    """
    尝试在一个表达式上匹配：
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

    # 2) "{}".format(args) 或 "{0}".format(args)
    if isinstance(expr, cst.Call):
        func = expr.func
        if not isinstance(func, cst.Attribute):
            return None
        if not isinstance(func.attr, cst.Name) or func.attr.value != "format":
            return None

        tmpl = func.value
        if not isinstance(tmpl, cst.SimpleString):
            return None

        # 不接受关键字参数 / *args
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
