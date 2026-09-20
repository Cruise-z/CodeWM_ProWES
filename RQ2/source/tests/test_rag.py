from pathlib import Path
from pipeline.rag import BM25RuleRetriever
from pipeline.llm_rag import build_messages, parse_llm_output, rewrite_with_rag
from pipeline.llm_provider import MockIdentityProvider

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "pipeline" / "rules" / "hard_rules.json"


def test_retrieval_is_channel_scoped_and_deterministic():
    r = BM25RuleRetriever.from_json(RULES)
    a = r.retrieve("indexOf null size expression", "java", "expr", top_k=4)
    b = r.retrieve("indexOf null size expression", "java", "expr", top_k=4)
    assert [x.id for x in a] == [x.id for x in b]
    assert a
    assert all(x.channel == "expr" for x in a)
    assert any(x.id == "expr.default_param_indexof" for x in a)


def test_all_channel_includes_diverse_rule_channels():
    r = BM25RuleRetriever.from_json(RULES)
    rules = r.retrieve("rename loop if null", "java", "all", top_k=6)
    assert {x.channel for x in rules} == {"id", "expr", "block"}


def test_mock_llm_rag_roundtrip_and_prompt_contract():
    r = BM25RuleRetriever.from_json(RULES)
    code = "int f(int x) { return x; }"
    out, meta = rewrite_with_rag(code, "java", "expr", 42, "sample-1", MockIdentityProvider(), r, parser_lib=None)
    assert out == code
    assert meta["retriever"] == "BM25-local-hard-rules"
    assert meta["changed"] is False
    assert meta["retrieved_rule_ids"]


def test_parse_output():
    code, rules = parse_llm_output("<applied_rules>expr.null_operand_swap</applied_rules>\n```java\nreturn null != x;\n```")
    assert code == "return null != x;"
    assert rules == ["expr.null_operand_swap"]
