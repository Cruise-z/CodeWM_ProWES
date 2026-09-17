import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "project" / "srcMarker" / "SrcMarker" / "validate_mbxp_rq2.py"
spec = importlib.util.spec_from_file_location("validate_mbxp", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_original_string_schema_cpp_program_composition():
    sample = {
        "prompt": "#include <cassert>\nint f(int x) {\n",
        "original_string": "int f(int x) { return x + 1; }",
        "test": "\nint main() { assert(f(1) == 2); }\n",
    }
    program = m.compose_program(sample)
    assert program.count("int f(int x)") == 1
    assert "return x + 1" in program


def test_original_string_schema_java_closes_wrapper_class():
    sample = {
        "prompt": "class F {\n  public static int f(int x) {\n",
        "original_string": "public static int f(int x) { return x; }",
        "test": "\nclass Main {}\n",
    }
    program = m.compose_program(sample)
    assert program.index("\n}\n") < program.index("class Main")
