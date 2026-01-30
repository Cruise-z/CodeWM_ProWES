# pyCodeObfuscator/rules/NL/naming_style.py
from __future__ import annotations

from typing import Optional

import libcst as cst

from ...core.rule_base import BaseRule, RuleDirection, register_rule
from ...patterns.NL.naming_style_pattern import (
    match_naming_style,
    NamingStyle,
    NamingStyleMatch,
    build_name,
)


def _pick_auto_target_style(current: NamingStyle) -> NamingStyle:
    """
    AUTO 模式下的“互转”策略（确定性轮转，方便测试）：
      CAMEL             -> SNAKE
      SNAKE             -> PASCAL_UNDERSCORE
      PASCAL_UNDERSCORE -> CAMEL
    """
    if current is NamingStyle.CAMEL:
        return NamingStyle.SNAKE
    if current is NamingStyle.SNAKE:
        return NamingStyle.PASCAL_UNDERSCORE
    if current is NamingStyle.PASCAL_UNDERSCORE:
        return NamingStyle.CAMEL
    return current


# 允许的一些别名 -> NamingStyle
_VARIANT_KEY_TO_STYLE: dict[str, NamingStyle] = {
    # camel 风格
    "camel": NamingStyle.CAMEL,
    "pascal": NamingStyle.CAMEL,
    "camelcase": NamingStyle.CAMEL,
    "pascalcase": NamingStyle.CAMEL,

    # snake 风格
    "snake": NamingStyle.SNAKE,
    "snake_case": NamingStyle.SNAKE,
    "snakecase": NamingStyle.SNAKE,

    # user_Add_Num 这种
    "underscore": NamingStyle.PASCAL_UNDERSCORE,
    "pascal_underscore": NamingStyle.PASCAL_UNDERSCORE,
    "user_add_num_style": NamingStyle.PASCAL_UNDERSCORE,
}


@register_rule
class NamingStyleRule(BaseRule):
    """
    三种命名风格互转：

        UserAddNum    # CAMEL
        user_add_num  # SNAKE
        user_Add_Num  # PASCAL_UNDERSCORE

    多形态方向约定（基于 RuleDirection）：

      - direction.mode == "AUTO":
            识别当前风格，在三种风格之间轮转：
                CAMEL -> SNAKE -> PASCAL_UNDERSCORE -> CAMEL

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "camel" / "snake" / "underscore" / "pascal_underscore" / ...
            本规则将这些 key 映射到 NamingStyle，并统一改写为目标风格。
    """

    rule_id = "refactoring.naming_style"
    description = "变量/参数命名风格互转（Camel / snake / user_Add_Num）"

    # 声明一下本规则支持的变体名称（主要用于 CLI/文档，可选）
    variants = ("camel", "snake", "pascal_underscore")

    def _target_style_for(self, match: NamingStyleMatch) -> Optional[NamingStyle]:
        cur = match.style
        direction = self.direction

        # ---- AUTO：在三种风格之间轮转 ----
        if direction.mode == "AUTO":
            target = _pick_auto_target_style(cur)

        # ---- TO_VARIANT：根据字符串 key 选目标风格 ----
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            style = _VARIANT_KEY_TO_STYLE.get(key.lower())
            if style is None:
                # 不认识的变体 key：不改
                return None
            target = style

        else:
            # 未知 mode：安全起见不做改写
            return None

        # 如果本来就是这个风格，就不动
        if target is cur:
            return None
        return target

    def leave_Name(
        self,
        original_node: cst.Name,
        updated_node: cst.Name,
    ) -> cst.Name:
        """
        对所有 Name 节点尝试做命名风格转换。

        当前简单实现：只根据 name 本身判断风格，不区分变量/参数/函数名等。
        如果以后你想更细粒度控制，可以结合 metadata 做过滤。
        """
        match = match_naming_style(updated_node)
        if match is None:
            return updated_node

        target_style = self._target_style_for(match)
        if target_style is None:
            return updated_node

        new_name = build_name(target_style, match.words)
        return updated_node.with_changes(value=new_name)
