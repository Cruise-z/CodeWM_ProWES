# pyCodeObfuscator/core/rule_base.py
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Iterable, Type, List, Optional

import libcst as cst


@dataclass(frozen=True)
class RuleDirection:
    """
    Unified direction descriptor for the multi-variant architecture:

      - mode    : "AUTO" or "TO_VARIANT"
      - variant : when mode == "TO_VARIANT", the desired target variant name
                  for example "camel" / "snake" / "percent" / "format"

    Notes:
      1. The direction no longer cares about binary relationships such as
         "original/transformed"; instead it is abstracted as one of the variants
         defined by a specific rule.

      2. The specific variants and their names are defined and interpreted by
         each concrete rule.
         For example, a naming rule might define:
             variants = ["camel", "snake", "underscore"]
         and then interpret "camel" as PascalCase, "snake" as snake_case, and so on.
    """
    mode: str                # "AUTO" or "TO_VARIANT"
    variant: Optional[str] = None

    # Convenience constructors
    @classmethod
    def auto(cls) -> RuleDirection:
        """AUTO mode: the rule decides how to convert among variants (flip/rotate/random, etc.)."""
        return cls(mode="AUTO", variant=None)

    @classmethod
    def to_variant(cls, variant: str) -> RuleDirection:
        """
        Convert to a specific variant (variant is interpreted by each rule itself).

        For example:
            RuleDirection.to_variant("snake")
            RuleDirection.to_variant("camel")
        """
        return cls(mode="TO_VARIANT", variant=variant)


# Provide a default AUTO constant for convenient use as a function default argument
RuleDirection.AUTO = RuleDirection.auto()  # type: ignore[attr-defined]


class BaseRule(cst.CSTTransformer, ABC):
    """
    Abstract base class for all rules (multi-variant architecture version).

    Each rule is a CSTTransformer that performs local rewrites on the syntax tree
    via visit/leave_xxx methods.

    Conventions:
      - rule_id      : unique rule id, for example "refactoring.remove_unnecessary_else"
      - description  : short description for CLI help
      - direction    : RuleDirection, the multi-variant conversion direction
      - variants     : optional, declares the supported variant names for the rule
                       for example ("camel", "snake", "underscore")
    """

    #: Unique rule id, for example "refactoring.remove_unnecessary_else"
    rule_id: str

    #: Short description used by the CLI help
    description: str

    #: Optional: declare variant names supported by this rule (for docs/CLI only, not enforced)
    #: For example ("camel", "snake", "underscore") means:
    #:   this rule will use these strings as variant keys internally
    variants: tuple[str, ...] = ()

    def __init__(self, direction: RuleDirection = RuleDirection.AUTO) -> None:
        super().__init__()
        self.direction = direction


# ---- Rule registry ----

_RULES: List[Type[BaseRule]] = []


def register_rule(cls: Type[BaseRule]) -> Type[BaseRule]:
    """
    Class decorator used to register rules automatically.

    Usage:
        @register_rule
        class SomeRule(BaseRule):
            ...
    """
    _RULES.append(cls)
    return cls


def get_all_rules() -> Iterable[Type[BaseRule]]:
    """
    Return all currently registered rule types.
    """
    return list(_RULES)
