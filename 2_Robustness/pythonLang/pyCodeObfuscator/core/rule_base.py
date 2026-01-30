# pyCodeObfuscator/core/rule_base.py
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Iterable, Type, List, Optional

import libcst as cst


@dataclass(frozen=True)
class RuleDirection:
    """
    多形态架构下的统一“方向”描述：

      - mode    : "AUTO" 或 "TO_VARIANT"
      - variant : 当 mode == "TO_VARIANT" 时，表示希望转换到的目标形态名称
                  例如 "camel" / "snake" / "percent" / "format" 等

    说明：
      1. 方向本身不再关心“original/transformed”这样的二元关系，
         而是抽象成“某条规则自己的若干变体之一”。

      2. 具体有哪些变体、每个变体叫什么名字，由 **具体规则** 自己定义和解释。
         比如命名规则可以定义：
             variants = ["camel", "snake", "underscore"]
         然后把 "camel" 理解为 PascalCase，"snake" 理解为 snake_case 等。
    """
    mode: str                # "AUTO" or "TO_VARIANT"
    variant: Optional[str] = None

    # 便捷构造方法
    @classmethod
    def auto(cls) -> RuleDirection:
        """自动模式，由规则自行决定如何在多种形态之间转换（翻转/轮转/随机等）。"""
        return cls(mode="AUTO", variant=None)

    @classmethod
    def to_variant(cls, variant: str) -> RuleDirection:
        """
        转换到指定形态（variant 由每条规则自己解释）。

        例如：
            RuleDirection.to_variant("snake")
            RuleDirection.to_variant("camel")
        """
        return cls(mode="TO_VARIANT", variant=variant)


# 提供一个默认的 AUTO 常量，方便作为函数缺省参数使用
RuleDirection.AUTO = RuleDirection.auto()  # type: ignore[attr-defined]


class BaseRule(cst.CSTTransformer, ABC):
    """
    所有规则的抽象基类（多形态架构版）。

    每条规则都是一个 CSTTransformer，通过 visit/leave_xxx
    在语法树上做局部改写。

    约定：
      - rule_id      : 规则唯一 id，例如 "refactoring.remove_unnecessary_else"
      - description  : 简要描述，用于 CLI 帮助
      - direction    : RuleDirection，多形态转换方向
      - variants     : 可选，用于声明该规则支持的变体名字列表（纯信息，非强制）
                       例如 ("camel", "snake", "underscore")
    """

    #: 规则唯一 id，例如 "refactoring.remove_unnecessary_else"
    rule_id: str

    #: 简要描述，用于 CLI 帮助
    description: str

    #: 可选：声明该规则支持的变体名称（仅用于文档/CLI，不强制使用）
    #: 比如 ("camel", "snake", "underscore") 表示：
    #:   该规则内会把这些字符串当作形态 key 使用
    variants: tuple[str, ...] = ()

    def __init__(self, direction: RuleDirection = RuleDirection.AUTO) -> None:
        super().__init__()
        self.direction = direction


# ---- 规则注册表 ----

_RULES: List[Type[BaseRule]] = []


def register_rule(cls: Type[BaseRule]) -> Type[BaseRule]:
    """
    class 装饰器，用于自动注册规则。

    使用方式：
        @register_rule
        class SomeRule(BaseRule):
            ...
    """
    _RULES.append(cls)
    return cls


def get_all_rules() -> Iterable[Type[BaseRule]]:
    """
    返回当前已注册的所有规则类型。
    """
    return list(_RULES)
