"""Shared method configuration for fresh RQ2 training and evaluation."""

import mutable_tree.transformers as ast_transformers


DATASET_LANG = {
    "github_c_funcs": "cpp",
    "github_java_funcs": "java",
    "csn_java": "java",
    "csn_js": "javascript",
}


def build_code_transformers(method: str):
    if method == "srcmarker":
        return [
            ast_transformers.IfBlockSwapTransformer(),
            ast_transformers.CompoundIfTransformer(),
            ast_transformers.ConditionTransformer(),
            ast_transformers.LoopTransformer(),
            ast_transformers.InfiniteLoopTransformer(),
            ast_transformers.UpdateTransformer(),
            ast_transformers.SameTypeDeclarationTransformer(),
            ast_transformers.VarDeclLocationTransformer(),
            ast_transformers.VarInitTransformer(),
            ast_transformers.VarNameStyleTransformer(),
        ]
    if method == "codemark":
        return [ast_transformers.VarNameStyleTransformer()]
    raise ValueError(f"Unknown method: {method}")


def validate_dataset_language(dataset: str, lang: str) -> None:
    expected = DATASET_LANG[dataset]
    if lang != expected:
        raise ValueError(
            f"Dataset {dataset!r} requires --lang={expected}, received {lang!r}"
        )
