# pyCodeObfuscator/rules/__init__.py

# AL.expression 规则
from .AL.expression import boolean_explicit_true_false
from .AL.expression import condition_parentheses  
from .AL.expression.dict_keys_usage import DictKeysUsageRule
from .AL.expression.none_usage import NoneUsageRule

# AL.block 规则
from .AL.block import unnecessary_else
from .AL.block import loop_index_direct_reference

# NL 规则
from .NL.naming_style import NamingStyleRule
# 如果将来在 NL 下也有规则，同样在这里导入
