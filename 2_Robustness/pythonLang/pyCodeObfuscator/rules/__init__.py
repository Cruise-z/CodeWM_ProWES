# pyCodeObfuscator/rules/__init__.py

# AL.expression rules
from .AL.expression import boolean_explicit_true_false
from .AL.expression import condition_parentheses  
from .AL.expression.dict_keys_usage import DictKeysUsageRule
from .AL.expression.none_usage import NoneUsageRule

# AL.block rules
from .AL.block import unnecessary_else
from .AL.block import loop_index_direct_reference

# NL rules
from .NL.naming_style import NamingStyleRule
# If more NL rules are added in the future, import them here as well
