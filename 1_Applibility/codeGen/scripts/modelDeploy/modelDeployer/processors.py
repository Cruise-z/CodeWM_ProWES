# processors.py

from typing import Any, Dict, List, Optional, Callable
import copy
from fastapi import HTTPException
from transformers import LogitsProcessorList, LogitsProcessor

from runtime import vocab_ids

ProcessorFactory = Callable[[], LogitsProcessorList]
ParametricBuilder = Callable[..., Any]

# Internal processors namespace (stored as zero-arg factories)
INTERNAL_PROCESSORS: Dict[str, ProcessorFactory] = {}

# Legacy external processors namespace (kept for compatibility, not used in resolve path)
EXTERNAL_PROCESSORS: Dict[str, ProcessorFactory] = {}

# External builders namespace (parametric; request provides params)
EXTERNAL_BUILDERS: Dict[str, ParametricBuilder] = {}

def register_external_builder(name: str, builder: ParametricBuilder) -> None:
    """Register a parametric external builder. Request can pass parameters via external_processor_params[name]."""
    if not callable(builder):
        raise TypeError(f"external builder for '{name}' must be callable")
    EXTERNAL_BUILDERS[name] = builder

def _ensure_lp_list(p: Any) -> LogitsProcessorList:
    """
    Normalize into LogitsProcessorList with strict type checks:
      - disallow None
      - allow: LogitsProcessor, LogitsProcessorList, list/tuple[LogitsProcessor]
    """
    if p is None:
        raise TypeError("LogitsProcessor is None (expected LogitsProcessor or LogitsProcessorList).")
    if isinstance(p, LogitsProcessorList):
        for it in p:
            if not isinstance(it, LogitsProcessor):
                raise TypeError(f"Invalid item in LogitsProcessorList: {type(it)}")
        return p
    if isinstance(p, LogitsProcessor):
        return LogitsProcessorList([p])
    if isinstance(p, (list, tuple)):
        if not all(isinstance(it, LogitsProcessor) for it in p):
            bad = [type(it) for it in p if not isinstance(it, LogitsProcessor)]
            raise TypeError(f"Invalid items in processor list: {bad}")
        return LogitsProcessorList(list(p))
    raise TypeError(f"Expected LogitsProcessor/LogitsProcessorList/list[LogitsProcessor], got {type(p)}")

def _clone_lp_list(lp: LogitsProcessorList) -> LogitsProcessorList:
    """
    Clone processors per request to avoid cross-request/shared-state interference.
    Falls back to reusing the original object if deepcopy fails.
    """
    new = []
    for p in lp:
        try:
            new.append(copy.deepcopy(p))
        except Exception:
            new.append(p)
    return LogitsProcessorList(new)

def _as_factory(factory_or_obj: Any) -> ProcessorFactory:
    """
    Convert into a zero-arg factory:
      1) If it's an instance (even callable), treat as instance and return a deepcopy clone per call.
      2) Else if it's a zero-arg callable factory, call and validate.
    """
    if isinstance(factory_or_obj, (LogitsProcessor, LogitsProcessorList, list, tuple)):
        inst_lp = _ensure_lp_list(factory_or_obj)
        def _factory_from_instance() -> LogitsProcessorList:
            return _clone_lp_list(inst_lp)
        return _factory_from_instance

    if callable(factory_or_obj):
        def _factory_from_callable() -> LogitsProcessorList:
            prod = factory_or_obj()
            return _ensure_lp_list(prod)
        return _factory_from_callable

    raise TypeError(
        "register_* expects a LogitsProcessor/LogitsProcessorList/list[LogitsProcessor] "
        f"or a zero-arg factory that returns one, got {type(factory_or_obj)}"
    )

def register_internal(name: str, factory_or_obj: Any) -> None:
    """Register into internal namespace (stored as factory)."""
    INTERNAL_PROCESSORS[name] = _as_factory(factory_or_obj)

def register_external(name: str, factory_or_obj: Any) -> None:
    """
    Compatibility function: kept to avoid breaking old code that calls register_external().
    Not used in the generation path (builders are used instead).
    """
    EXTERNAL_PROCESSORS[name] = _as_factory(factory_or_obj)

def resolve_internal(internal_names: Optional[List[str]]) -> Optional[LogitsProcessorList]:
    """Instantiate and chain internal processors in the provided order."""
    chain: List[LogitsProcessor] = []
    if internal_names:
        for n in internal_names:
            if n not in INTERNAL_PROCESSORS:
                raise HTTPException(status_code=400, detail=f"Unknown internal processor: {n}")
            try:
                lp = INTERNAL_PROCESSORS[n]()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Internal processor '{n}' factory error: {e}") from e
            for it in lp:
                if not isinstance(it, LogitsProcessor):
                    raise HTTPException(status_code=400, detail=f"Internal processor '{n}' produced invalid item: {type(it)}")
            chain.extend(list(lp))
    return LogitsProcessorList(chain) if chain else None

def resolve_external(
    external_names: Optional[List[str]],
    *,
    external_params: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[LogitsProcessorList]:
    """
    Instantiate and chain external processors (via builders) in the provided order.
    Enforces vocab=vocab_ids and ignores any incoming vocab parameter.
    """
    chain: List[LogitsProcessor] = []
    if external_names:
        for n in external_names:
            if n not in EXTERNAL_BUILDERS:
                raise HTTPException(status_code=400, detail=f"Unknown external builder: {n}")
            cfg = dict((external_params or {}).get(n) or {})
            cfg.pop("vocab", None)
            try:
                obj = EXTERNAL_BUILDERS[n](vocab=vocab_ids, **cfg)
                lp = _ensure_lp_list(obj)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"External builder '{n}' error: {e}") from e
            for it in lp:
                if not isinstance(it, LogitsProcessor):
                    raise HTTPException(status_code=400, detail=f"External builder '{n}' produced invalid item: {type(it)}")
            chain.extend(list(lp))
    return LogitsProcessorList(chain) if chain else None

def concat_lp(a: Optional[LogitsProcessorList], b: Optional[LogitsProcessorList]) -> Optional[LogitsProcessorList]:
    """Concatenate two LogitsProcessorLists preserving order."""
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return LogitsProcessorList(list(a) + list(b))
