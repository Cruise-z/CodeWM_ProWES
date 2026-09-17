# processors.py

import copy
from dataclasses import dataclass
from enum import Enum
import hashlib
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from fastapi import HTTPException
from transformers import LogitsProcessorList, LogitsProcessor

ProcessorFactory = Callable[[], LogitsProcessorList]
ParametricBuilder = Callable[..., Any]
MethodPluginBuilder = Callable[["MethodBuildResources", Mapping[str, Any]], Any]
MethodContractSelector = Callable[[Mapping[str, Any]], "MethodDecodeContract"]
GenerationEvidenceFinalizer = Callable[[LogitsProcessor, Sequence[Sequence[int]]], None]


class WatermarkPlacement(str, Enum):
    PRE_WARPER = "pre_warper"
    POST_TOPP = "post_topp"


class DecodeAnchor(str, Enum):
    """Stable names for host-owned nodes in the sampling graph."""

    HOST_PROCESSORS = "host.processors"
    TEMPERATURE = "sampling.temperature"
    TOP_K = "sampling.top_k"
    TOP_P = "sampling.top_p"
    SAMPLER = "sampling.sampler"


@dataclass(frozen=True)
class DecodeOrder:
    """Relative ordering declared by a method component or adapter."""

    after: tuple[str, ...]
    before: tuple[str, ...]

    def __post_init__(self) -> None:
        def node_name(item: Any) -> str:
            return str(getattr(item, "value", item)).strip()

        normalized_after = tuple(node_name(item) for item in self.after)
        normalized_before = tuple(node_name(item) for item in self.before)
        if not normalized_after or not normalized_before:
            raise ValueError("decode order requires at least one after and one before constraint")
        if any(not item for item in (*normalized_after, *normalized_before)):
            raise ValueError("decode order constraints must not be empty")
        if set(normalized_after).intersection(normalized_before):
            raise ValueError("decode order cannot place a component both after and before the same node")
        object.__setattr__(self, "after", normalized_after)
        object.__setattr__(self, "before", normalized_before)

    def as_dict(self) -> dict[str, list[str]]:
        return {"after": list(self.after), "before": list(self.before)}

    @classmethod
    def between(cls, after: str, before: str) -> "DecodeOrder":
        return cls(after=(after,), before=(before,))


class VocabDomain(str, Enum):
    """Framework-owned dense token domains available to watermark methods."""

    TOKENIZER_BASE = "tokenizer_base"
    TOKENIZER_FULL = "tokenizer_full"
    MODEL_CONFIG = "model_config"
    SCORE = "score"


class ScoreDomain(str, Enum):
    """Physical score tensor supplied through the Hugging Face processor API."""

    MODEL_OUTPUT_LOGITS = "model_output_logits"


class SupportEffect(str, Enum):
    """Declared effect of a method component on the incoming finite support."""

    PRESERVE = "preserve"
    MAY_REDUCE = "may_reduce"
    MAY_EXPAND = "may_expand"
    METHOD_DEFINED = "method_defined"


class OutOfDomainPolicy(str, Enum):
    """Declared treatment of score IDs outside the selected watermark vocab."""

    PASS_THROUGH = "pass_through"
    REJECT = "reject"
    METHOD_DEFINED = "method_defined"


class FrameworkComponent(str, Enum):
    """Model-deployment objects a method may explicitly request at build time."""

    TOKENIZER = "tokenizer"
    MODEL = "model"
    DEVICE = "device"


class MethodDetectionMode(str, Enum):
    """Detection capability exposed by a method's outer integration adapter."""

    PROCESSOR_STATE = "processor_state"
    UNAVAILABLE = "unavailable"


class DetectionScoreDirection(str, Enum):
    HIGHER = "higher"
    LOWER = "lower"


@dataclass(frozen=True)
class MethodParameterContract:
    """Method-owned request parameter names accepted by its outer builder."""

    accepted: tuple[str, ...]
    required: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        accepted = tuple(str(name).strip() for name in self.accepted)
        required = tuple(str(name).strip() for name in self.required)
        if any(not name for name in (*accepted, *required)):
            raise ValueError("method parameter names must not be empty")
        if len(set(accepted)) != len(accepted):
            raise ValueError("accepted method parameters must not contain duplicates")
        if len(set(required)) != len(required):
            raise ValueError("required method parameters must not contain duplicates")
        unknown_required = sorted(set(required).difference(accepted))
        if unknown_required:
            raise ValueError(
                f"required method parameters are not accepted: {unknown_required}"
            )
        reserved = sorted(
            set(accepted).intersection(
                {"vocab", "runtime_context", "component_resources"}
            )
        )
        if reserved:
            raise ValueError(
                f"method parameter contract contains reserved resources: {reserved}"
            )
        object.__setattr__(self, "accepted", accepted)
        object.__setattr__(self, "required", required)

    def validate(self, params: Mapping[str, Any]) -> None:
        unknown = sorted(set(params).difference(self.accepted))
        if unknown:
            raise ValueError(f"unsupported method parameters: {unknown}")
        missing = sorted(set(self.required).difference(params))
        if missing:
            raise ValueError(f"missing required method parameters: {missing}")

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "accepted": list(self.accepted),
            "required": list(self.required),
        }


@dataclass(frozen=True)
class MethodDetectionContract:
    """Method-owned declaration of generation-coupled detector capability."""

    mode: MethodDetectionMode
    score_fields: tuple[str, ...] = ()
    score_direction: Optional[DetectionScoreDirection] = None

    def __post_init__(self) -> None:
        mode = MethodDetectionMode(self.mode)
        fields = tuple(str(field).strip() for field in self.score_fields)
        direction = (
            None
            if self.score_direction is None
            else DetectionScoreDirection(self.score_direction)
        )
        if any(not field for field in fields):
            raise ValueError("detection score fields must not be empty")
        if len(set(fields)) != len(fields):
            raise ValueError("detection score fields must not contain duplicates")
        if mode is MethodDetectionMode.PROCESSOR_STATE and not fields:
            raise ValueError("processor-state detection requires at least one score field")
        if mode is MethodDetectionMode.PROCESSOR_STATE and direction is None:
            raise ValueError("processor-state detection requires a score direction")
        if mode is MethodDetectionMode.UNAVAILABLE and (fields or direction is not None):
            raise ValueError(
                "unavailable detection must not declare score fields or direction"
            )
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "score_fields", fields)
        object.__setattr__(self, "score_direction", direction)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "score_fields": list(self.score_fields),
            "score_direction": (
                None if self.score_direction is None else self.score_direction.value
            ),
            "independent_text_detection": False,
        }


@dataclass(frozen=True)
class MethodResourceContract:
    """Method-owned choice of framework-provided score and token resources."""

    vocab_domain: VocabDomain
    score_domain: ScoreDomain
    support_effect: SupportEffect
    out_of_domain_policy: OutOfDomainPolicy

    def __post_init__(self) -> None:
        object.__setattr__(self, "vocab_domain", VocabDomain(self.vocab_domain))
        object.__setattr__(self, "score_domain", ScoreDomain(self.score_domain))
        object.__setattr__(self, "support_effect", SupportEffect(self.support_effect))
        object.__setattr__(
            self,
            "out_of_domain_policy",
            OutOfDomainPolicy(self.out_of_domain_policy),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "vocab_domain": self.vocab_domain.value,
            "score_domain": self.score_domain.value,
            "support_effect": self.support_effect.value,
            "out_of_domain_policy": self.out_of_domain_policy.value,
        }


@dataclass(frozen=True)
class RuntimeDomainCatalog:
    """Authoritative request-local sizes; unequal domains remain explicit."""

    tokenizer_base_size: int
    tokenizer_full_size: int
    model_config_size: int
    score_size: int

    def __post_init__(self) -> None:
        for name in (
            "tokenizer_base_size",
            "tokenizer_full_size",
            "model_config_size",
            "score_size",
        ):
            value = int(getattr(self, name))
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")
            object.__setattr__(self, name, value)
        if self.tokenizer_base_size > self.tokenizer_full_size:
            raise ValueError(
                "tokenizer base vocabulary cannot exceed the full tokenizer domain"
            )
        if self.tokenizer_full_size > self.score_size:
            raise ValueError(
                "full tokenizer domain cannot exceed the model score domain"
            )

    def size(self, domain: VocabDomain) -> int:
        normalized = VocabDomain(domain)
        return {
            VocabDomain.TOKENIZER_BASE: self.tokenizer_base_size,
            VocabDomain.TOKENIZER_FULL: self.tokenizer_full_size,
            VocabDomain.MODEL_CONFIG: self.model_config_size,
            VocabDomain.SCORE: self.score_size,
        }[normalized]

    def as_dict(self) -> dict[str, int]:
        return {
            VocabDomain.TOKENIZER_BASE.value: self.tokenizer_base_size,
            VocabDomain.TOKENIZER_FULL.value: self.tokenizer_full_size,
            VocabDomain.MODEL_CONFIG.value: self.model_config_size,
            VocabDomain.SCORE.value: self.score_size,
        }


@dataclass(frozen=True)
class ResolvedMethodResources:
    """A component contract resolved against one request's runtime domains."""

    contract: MethodResourceContract
    vocab_size: int
    score_vocab_size: int

    @property
    def vocab_ids(self) -> range:
        return range(self.vocab_size)

    @property
    def out_of_domain_size(self) -> int:
        return self.score_vocab_size - self.vocab_size

    def contains(self, token_id: int) -> bool:
        return 0 <= int(token_id) < self.vocab_size

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.contract.as_dict(),
            "vocab_size": self.vocab_size,
            "score_vocab_size": self.score_vocab_size,
            "out_of_domain_size": self.out_of_domain_size,
        }


@dataclass(frozen=True)
class ScoreSupportView:
    """Non-mutating derived views of scores seen at a component's decode node."""

    logits: Any
    finite_mask: Any
    candidate_ids: tuple[Any, ...]
    candidate_counts: tuple[int, ...]
    probabilities: Any

    @classmethod
    def from_scores(
        cls,
        scores: Any,
        *,
        expected_width: Optional[int] = None,
    ) -> "ScoreSupportView":
        import torch

        if not isinstance(scores, torch.Tensor) or scores.ndim != 2:
            raise TypeError("scores must be a rank-2 torch.Tensor")
        width = int(scores.shape[-1])
        if expected_width is not None and width != int(expected_width):
            raise ValueError(
                f"score width mismatch: expected {int(expected_width)}, got {width}"
            )
        finite_mask = torch.isfinite(scores)
        candidate_counts = tuple(
            int(value) for value in finite_mask.sum(dim=-1).detach().cpu().tolist()
        )
        if any(count == 0 for count in candidate_counts):
            raise ValueError("score support must contain at least one finite candidate per row")
        candidate_ids = tuple(
            torch.nonzero(row, as_tuple=False).flatten()
            for row in finite_mask
        )
        masked_logits = scores.masked_fill(~finite_mask, float("-inf"))
        probabilities = torch.softmax(masked_logits, dim=-1)
        return cls(
            logits=scores,
            finite_mask=finite_mask,
            candidate_ids=candidate_ids,
            candidate_counts=candidate_counts,
            probabilities=probabilities,
        )


@dataclass(frozen=True)
class MethodDecodeContract:
    """Method-owned decode ordering and runtime-resource selections."""

    name: str
    component_orders: tuple[DecodeOrder, ...]
    component_resources: tuple[MethodResourceContract, ...]
    components: tuple[str, ...] = ()
    variant: str = "default"

    def __post_init__(self) -> None:
        normalized_name = str(self.name).strip().lower()
        normalized_variant = str(self.variant).strip().lower()
        normalized_components = tuple(
            str(component).strip().lower() for component in self.components
        )
        if not normalized_name:
            raise ValueError("method decode contract name must not be empty")
        if not normalized_variant:
            raise ValueError("method decode contract variant must not be empty")
        if not self.component_orders:
            raise ValueError("method decode contract requires at least one component order")
        if not all(isinstance(order, DecodeOrder) for order in self.component_orders):
            raise TypeError("method decode contract orders must be DecodeOrder values")
        if not self.component_resources:
            raise ValueError("method decode contract requires component resource contracts")
        if not all(
            isinstance(resource, MethodResourceContract)
            for resource in self.component_resources
        ):
            raise TypeError(
                "method decode contract resources must be MethodResourceContract values"
            )
        if len(self.component_resources) != len(self.component_orders):
            raise ValueError(
                "method decode contract resources and orders must have equal lengths"
            )
        if any(not component for component in normalized_components):
            raise ValueError("method decode contract component names must not be empty")
        if len(set(normalized_components)) != len(normalized_components):
            raise ValueError(
                "method decode contract component names must not contain duplicates"
            )
        if normalized_components and len(normalized_components) != len(self.component_orders):
            raise ValueError("method decode contract components and orders must have equal lengths")
        if not normalized_components and len(self.component_orders) != 1:
            raise ValueError("multi-component decode contracts require component names")
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "variant", normalized_variant)
        object.__setattr__(self, "components", normalized_components)

    def as_dict(self) -> dict[str, Any]:
        return {
            "variant": self.variant,
            "components": list(self.components or (self.name,)),
            "decode_orders": [order.as_dict() for order in self.component_orders],
            "resources": [resource.as_dict() for resource in self.component_resources],
        }


@dataclass(frozen=True)
class MethodRuntimeContext:
    """Request-local model/sampling facts exposed to future method builders."""

    rng_seed: Optional[int]
    do_sample: bool
    temperature: float
    top_p: float
    prompt_input_ids: tuple[tuple[int, ...], ...]
    tokenizer_vocab_size: int
    tokenizer_length: int
    model_vocab_size: int
    score_vocab_size: int
    eos_token_ids: tuple[int, ...]
    pad_token_id: Optional[int]

    def __post_init__(self) -> None:
        catalog = self.domain_catalog
        special_ids = (*self.eos_token_ids,)
        if self.pad_token_id is not None:
            special_ids = (*special_ids, int(self.pad_token_id))
        invalid_special = [
            token for token in special_ids if token < 0 or token >= catalog.score_size
        ]
        if invalid_special:
            raise ValueError(
                f"special token IDs outside score domain: {invalid_special}"
            )
        invalid_prompt = [
            token
            for row in self.prompt_input_ids
            for token in row
            if token < 0 or token >= catalog.score_size
        ]
        if invalid_prompt:
            raise ValueError(
                f"prompt token IDs outside score domain: {invalid_prompt[:8]}"
            )

    @property
    def domain_catalog(self) -> RuntimeDomainCatalog:
        return RuntimeDomainCatalog(
            tokenizer_base_size=self.tokenizer_vocab_size,
            tokenizer_full_size=self.tokenizer_length,
            model_config_size=self.model_vocab_size,
            score_size=self.score_vocab_size,
        )

    def resolve_resources(
        self,
        contract: MethodResourceContract,
    ) -> ResolvedMethodResources:
        normalized = normalize_resource_contract(contract)
        vocab_size = self.domain_catalog.size(normalized.vocab_domain)
        if vocab_size > self.score_vocab_size:
            raise ValueError(
                f"selected {normalized.vocab_domain.value} domain size {vocab_size} "
                f"exceeds score domain size {self.score_vocab_size}"
            )
        if (
            normalized.out_of_domain_policy is OutOfDomainPolicy.REJECT
            and vocab_size != self.score_vocab_size
        ):
            raise ValueError(
                f"{normalized.vocab_domain.value} leaves "
                f"{self.score_vocab_size - vocab_size} score IDs outside the selected "
                "domain, but the method declares out_of_domain_policy=reject"
            )
        return ResolvedMethodResources(
            contract=normalized,
            vocab_size=vocab_size,
            score_vocab_size=self.score_vocab_size,
        )

    def score_support(self, scores: Any) -> ScoreSupportView:
        return ScoreSupportView.from_scores(
            scores,
            expected_width=self.score_vocab_size,
        )

    def derive_seed(self, namespace: str) -> Optional[int]:
        if self.rng_seed is None:
            return None
        payload = f"{int(self.rng_seed)}:{str(namespace)}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & ((1 << 63) - 1)

    def torch_generator(self, namespace: str, device: Any):
        seed = self.derive_seed(namespace)
        if seed is None:
            return None
        import torch

        generator = torch.Generator(device=device)
        generator.manual_seed(seed)
        return generator


@dataclass(frozen=True)
class FrameworkRuntimeComponents:
    """Host-owned objects available to method plugins through declared access."""

    tokenizer: Any
    model: Any
    tokenizer_vocab_ids: Sequence[int]
    device: Any = None

    def __post_init__(self) -> None:
        if self.tokenizer is None:
            raise ValueError("framework tokenizer must not be None")
        if self.model is None:
            raise ValueError("framework model must not be None")
        if self.tokenizer_vocab_ids is None:
            raise ValueError("framework tokenizer vocab IDs must not be None")

    def resolved_device(self) -> Any:
        if self.device is not None:
            return self.device

        import torch

        model_device = getattr(self.model, "device", None)
        if model_device is not None and model_device != torch.device("meta"):
            return model_device
        try:
            return next(self.model.parameters()).device
        except StopIteration:
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def for_method(
        self,
        *,
        runtime_context: MethodRuntimeContext,
        component_resources: tuple[ResolvedMethodResources, ...],
        required_components: tuple[FrameworkComponent, ...],
    ) -> "MethodBuildResources":
        return MethodBuildResources(
            runtime_context=runtime_context,
            component_resources=component_resources,
            required_framework_components=required_components,
            _framework=self,
        )


@dataclass(frozen=True)
class MethodBuildResources:
    """Validated, method-facing view of host resources for one request."""

    runtime_context: MethodRuntimeContext
    component_resources: tuple[ResolvedMethodResources, ...]
    required_framework_components: tuple[FrameworkComponent, ...]
    _framework: FrameworkRuntimeComponents

    def __post_init__(self) -> None:
        normalized = tuple(
            FrameworkComponent(component)
            for component in self.required_framework_components
        )
        if len(set(normalized)) != len(normalized):
            raise ValueError("required framework components must not contain duplicates")
        if not self.component_resources:
            raise ValueError("method build resources require component resources")
        object.__setattr__(self, "required_framework_components", normalized)

    def _require(self, component: FrameworkComponent) -> None:
        if component not in self.required_framework_components:
            raise RuntimeError(
                f"method did not declare framework component: {component.value}"
            )

    @property
    def tokenizer(self) -> Any:
        self._require(FrameworkComponent.TOKENIZER)
        return self._framework.tokenizer

    @property
    def model(self) -> Any:
        self._require(FrameworkComponent.MODEL)
        return self._framework.model

    @property
    def device(self) -> Any:
        self._require(FrameworkComponent.DEVICE)
        return self._framework.resolved_device()

    def component(self, index: int = 0) -> ResolvedMethodResources:
        if index < 0 or index >= len(self.component_resources):
            raise IndexError(f"method component resource index out of range: {index}")
        return self.component_resources[index]

    def vocab_ids(self, index: int = 0) -> Sequence[int]:
        resource = self.component(index)
        dense_ids = self._framework.tokenizer_vocab_ids
        if resource.vocab_size == len(dense_ids):
            return dense_ids
        return resource.vocab_ids

    def score_support(self, scores: Any) -> ScoreSupportView:
        return self.runtime_context.score_support(scores)


@dataclass(frozen=True)
class MethodIntegrationPlugin:
    """Complete method-owned binding consumed by the generic host registry."""

    contract: MethodDecodeContract
    builder: MethodPluginBuilder
    required_framework_components: tuple[FrameworkComponent, ...]
    parameter_contract: MethodParameterContract
    detection_contract: MethodDetectionContract
    generation_evidence_finalizer: Optional[GenerationEvidenceFinalizer] = None
    variant_contracts: tuple[MethodDecodeContract, ...] = ()
    contract_selector: Optional[MethodContractSelector] = None

    def __post_init__(self) -> None:
        if not isinstance(self.contract, MethodDecodeContract):
            raise TypeError("method plugin contract must be a MethodDecodeContract")
        if not callable(self.builder):
            raise TypeError(f"method plugin '{self.contract.name}' builder must be callable")
        if not isinstance(self.parameter_contract, MethodParameterContract):
            raise TypeError(
                f"method plugin '{self.contract.name}' parameter contract must be "
                "MethodParameterContract"
            )
        if not isinstance(self.detection_contract, MethodDetectionContract):
            raise TypeError(
                f"method plugin '{self.contract.name}' detection contract must be "
                "MethodDetectionContract"
            )
        variants = tuple(self.variant_contracts)
        if not all(isinstance(contract, MethodDecodeContract) for contract in variants):
            raise TypeError(
                f"method plugin '{self.contract.name}' variants must be "
                "MethodDecodeContract values"
            )
        wrong_names = sorted(
            {
                contract.name
                for contract in variants
                if contract.name != self.contract.name
            }
        )
        if wrong_names:
            raise ValueError(
                f"method plugin '{self.contract.name}' variants use other method names: "
                f"{wrong_names}"
            )
        variant_names = tuple(
            contract.variant for contract in (self.contract, *variants)
        )
        if len(set(variant_names)) != len(variant_names):
            raise ValueError(
                f"method plugin '{self.contract.name}' contract variants contain duplicates"
            )
        if variants and not callable(self.contract_selector):
            raise ValueError(
                f"method plugin '{self.contract.name}' contract variants require a selector"
            )
        if self.contract_selector is not None and not callable(self.contract_selector):
            raise TypeError(
                f"method plugin '{self.contract.name}' contract selector must be callable"
            )
        normalized = tuple(
            FrameworkComponent(component)
            for component in self.required_framework_components
        )
        if len(set(normalized)) != len(normalized):
            raise ValueError(
                f"method plugin '{self.contract.name}' framework components contain duplicates"
            )
        if self.generation_evidence_finalizer is not None and not callable(
            self.generation_evidence_finalizer
        ):
            raise TypeError(
                f"method plugin '{self.contract.name}' evidence finalizer must be callable"
            )
        if (
            self.detection_contract.mode is MethodDetectionMode.PROCESSOR_STATE
            and self.generation_evidence_finalizer is None
        ):
            raise ValueError(
                f"method plugin '{self.contract.name}' processor-state detection "
                "requires a generation evidence finalizer"
            )
        object.__setattr__(self, "required_framework_components", normalized)
        object.__setattr__(self, "variant_contracts", variants)

    @property
    def contracts(self) -> tuple[MethodDecodeContract, ...]:
        return (self.contract, *self.variant_contracts)

    def contract_for(self, params: Mapping[str, Any]) -> MethodDecodeContract:
        if self.contract_selector is None:
            return self.contract
        selected = self.contract_selector(params)
        if not isinstance(selected, MethodDecodeContract):
            raise TypeError(
                f"method plugin '{self.contract.name}' contract selector must return "
                "a MethodDecodeContract"
            )
        for declared in self.contracts:
            if selected == declared:
                return declared
        raise ValueError(
            f"method plugin '{self.contract.name}' selected undeclared contract "
            f"variant '{selected.variant}'"
        )


@dataclass(frozen=True)
class SampledTokenEvent:
    step: int
    token_ids: tuple[int, ...]
    sequence_ids: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class ExternalPlacementSpec:
    placement: Optional[WatermarkPlacement]
    components: tuple[str, ...] = ()
    component_orders: tuple[Optional[DecodeOrder], ...] = ()
    component_resources: tuple[MethodResourceContract, ...] = ()
    generation_evidence_finalizer: Optional[GenerationEvidenceFinalizer] = None

# Internal processors namespace (stored as zero-arg factories)
INTERNAL_PROCESSORS: Dict[str, ProcessorFactory] = {}

# Legacy external processors namespace (kept for compatibility, not used in resolve path)
EXTERNAL_PROCESSORS: Dict[str, ProcessorFactory] = {}

# External builders namespace (parametric; request provides params)
EXTERNAL_BUILDERS: Dict[str, ParametricBuilder] = {}
EXTERNAL_PLACEMENTS: Dict[str, ExternalPlacementSpec] = {}
EXTERNAL_METHOD_PLUGINS: Dict[str, MethodIntegrationPlugin] = {}

def register_external_builder(
    name: str,
    builder: ParametricBuilder,
    *,
    placement: Optional[WatermarkPlacement] = None,
    components: tuple[str, ...] = (),
    component_orders: tuple[Optional[DecodeOrder], ...] = (),
    component_resources: tuple[MethodResourceContract, ...] = (),
    generation_evidence_finalizer: Optional[GenerationEvidenceFinalizer] = None,
) -> None:
    """Register a builder with a legacy placement or component-relative orders."""
    if not callable(builder):
        raise TypeError(f"external builder for '{name}' must be callable")
    if generation_evidence_finalizer is not None and not callable(
        generation_evidence_finalizer
    ):
        raise TypeError(
            f"generation evidence finalizer for '{name}' must be callable"
        )
    if placement is None:
        resolved_placement = None
    else:
        try:
            resolved_placement = WatermarkPlacement(placement)
        except ValueError as exc:
            raise ValueError(f"unsupported placement for external builder '{name}': {placement}") from exc
    normalized_component_orders = tuple(
        None if item is None else normalize_decode_order(item)
        for item in component_orders
    )
    normalized_component_resources = tuple(
        normalize_resource_contract(item) for item in component_resources
    )
    if not normalized_component_resources:
        raise ValueError(
            f"external builder '{name}' requires component resource contracts"
        )
    if normalized_component_orders and components and len(normalized_component_orders) != len(components):
        raise ValueError(
            f"external builder '{name}' component_orders must match components"
        )
    expected_components = len(components) if components else 1
    if len(normalized_component_resources) != expected_components:
        raise ValueError(
            f"external builder '{name}' component_resources must match components"
        )
    EXTERNAL_BUILDERS[name] = builder
    EXTERNAL_PLACEMENTS[name] = ExternalPlacementSpec(
        placement=resolved_placement,
        components=tuple(components),
        component_orders=normalized_component_orders,
        component_resources=normalized_component_resources,
        generation_evidence_finalizer=generation_evidence_finalizer,
    )


def register_method_builder(
    contract: MethodDecodeContract,
    builder: ParametricBuilder,
    *,
    generation_evidence_finalizer: Optional[GenerationEvidenceFinalizer] = None,
) -> None:
    """Register a method-owned contract for mandatory topology compilation."""
    if not isinstance(contract, MethodDecodeContract):
        raise TypeError("contract must be a MethodDecodeContract")
    register_external_builder(
        contract.name,
        builder,
        components=contract.components,
        component_orders=contract.component_orders,
        component_resources=contract.component_resources,
        generation_evidence_finalizer=generation_evidence_finalizer,
    )


def register_method_plugin(plugin: MethodIntegrationPlugin) -> None:
    """Register one complete method-owned plugin without host method knowledge."""
    if not isinstance(plugin, MethodIntegrationPlugin):
        raise TypeError("plugin must be a MethodIntegrationPlugin")
    name = plugin.contract.name
    if name in EXTERNAL_BUILDERS or name in EXTERNAL_METHOD_PLUGINS:
        raise ValueError(f"duplicate method plugin registration: {name}")
    register_method_builder(
        plugin.contract,
        plugin.builder,
        generation_evidence_finalizer=plugin.generation_evidence_finalizer,
    )
    EXTERNAL_METHOD_PLUGINS[name] = plugin


def normalize_decode_order(value: Any) -> DecodeOrder:
    if isinstance(value, DecodeOrder):
        return value
    if isinstance(value, Mapping):
        after = value.get("after") or ()
        before = value.get("before") or ()
        if isinstance(after, str):
            after = (after,)
        if isinstance(before, str):
            before = (before,)
        return DecodeOrder(after=tuple(after), before=tuple(before))
    raise TypeError(f"decode order must be DecodeOrder or mapping, got {type(value)}")


def normalize_resource_contract(value: Any) -> MethodResourceContract:
    if isinstance(value, MethodResourceContract):
        return value
    if isinstance(value, Mapping):
        return MethodResourceContract(**dict(value))
    raise TypeError(
        "resource contract must be MethodResourceContract or mapping, "
        f"got {type(value)}"
    )


def processor_decode_order(processor: LogitsProcessor) -> Optional[DecodeOrder]:
    """Read an order declared by the processor itself or an integration adapter."""
    declaration = getattr(processor, "codewm_decode_order", None)
    if declaration is None:
        declaration = getattr(processor, "_codewm_decode_order", None)
    if callable(declaration):
        declaration = declaration()
    if declaration is None:
        return None
    return normalize_decode_order(declaration)

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
    runtime_context: Optional[MethodRuntimeContext] = None,
    framework_components: Optional[FrameworkRuntimeComponents] = None,
) -> Optional[LogitsProcessorList]:
    """
    Instantiate and chain external processors (via builders) in the provided order.
    Resolves method-owned resource declarations and ignores reserved request values.
    """
    chain: List[LogitsProcessor] = []
    if external_names:
        for n in external_names:
            if n not in EXTERNAL_BUILDERS:
                raise HTTPException(status_code=400, detail=f"Unknown external builder: {n}")
            if n not in EXTERNAL_PLACEMENTS:
                raise HTTPException(status_code=500, detail=f"External builder '{n}' has no placement contract")
            cfg = dict((external_params or {}).get(n) or {})
            reserved_keys = sorted(
                set(cfg).intersection(
                    {"vocab", "runtime_context", "component_resources"}
                )
            )
            if reserved_keys:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"External builder '{n}' request cannot override reserved "
                        f"runtime resources: {reserved_keys}"
                    ),
                )
            if runtime_context is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"External builder '{n}' requires a runtime context",
                )
            plugin = EXTERNAL_METHOD_PLUGINS.get(n)
            if plugin is not None:
                try:
                    plugin.parameter_contract.validate(cfg)
                    active_contract = plugin.contract_for(MappingProxyType(cfg))
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"External builder '{n}' error: {e}",
                    ) from e
                spec = ExternalPlacementSpec(
                    placement=None,
                    components=active_contract.components,
                    component_orders=active_contract.component_orders,
                    component_resources=active_contract.component_resources,
                    generation_evidence_finalizer=(
                        plugin.generation_evidence_finalizer
                    ),
                )
            else:
                spec = EXTERNAL_PLACEMENTS[n]
            try:
                resolved_resources = tuple(
                    runtime_context.resolve_resources(contract)
                    for contract in spec.component_resources
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"External builder '{n}' resource contract error: {e}",
                ) from e
            try:
                if plugin is not None:
                    if framework_components is None:
                        raise ValueError(
                            f"method plugin '{n}' requires framework runtime components"
                        )
                    method_resources = framework_components.for_method(
                        runtime_context=runtime_context,
                        component_resources=resolved_resources,
                        required_components=plugin.required_framework_components,
                    )
                    obj = plugin.builder(
                        method_resources,
                        MappingProxyType(cfg),
                    )
                else:
                    cfg["runtime_context"] = runtime_context
                    cfg["component_resources"] = resolved_resources
                    if len(resolved_resources) == 1:
                        cfg["vocab"] = resolved_resources[0].vocab_ids
                    obj = EXTERNAL_BUILDERS[n](**cfg)
                lp = _ensure_lp_list(obj)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"External builder '{n}' error: {e}") from e
            for it in lp:
                if not isinstance(it, LogitsProcessor):
                    raise HTTPException(status_code=400, detail=f"External builder '{n}' produced invalid item: {type(it)}")
            if spec.components and len(spec.components) != len(lp):
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"External builder '{n}' produced {len(lp)} processors; "
                        f"placement contract requires {len(spec.components)}"
                    ),
                )
            if spec.component_orders and len(spec.component_orders) != len(lp):
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"External builder '{n}' produced {len(lp)} processors; "
                        f"order contract requires {len(spec.component_orders)}"
                    ),
                )
            if len(spec.component_resources) != len(lp):
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"External builder '{n}' produced {len(lp)} processors; "
                        f"resource contract requires {len(spec.component_resources)}"
                    ),
                )
            if plugin is not None:
                detector_count = sum(
                    1
                    for item in lp
                    if callable(getattr(item, "detect_last", None))
                )
                detection_mode = plugin.detection_contract.mode
                if (
                    detection_mode is MethodDetectionMode.PROCESSOR_STATE
                    and detector_count == 0
                ):
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"method plugin '{n}' declares processor-state detection "
                            "but produced no detect_last() component"
                        ),
                    )
                if (
                    detection_mode is MethodDetectionMode.UNAVAILABLE
                    and detector_count != 0
                ):
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"method plugin '{n}' declares detection unavailable but "
                            f"produced {detector_count} detect_last() component(s)"
                        ),
                    )
            for index, item in enumerate(lp):
                declared_order = processor_decode_order(item)
                registered_order = (
                    spec.component_orders[index]
                    if spec.component_orders
                    else None
                )
                if (
                    declared_order is not None
                    and registered_order is not None
                    and declared_order != registered_order
                ):
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"External builder '{n}' component {index} processor order "
                            "conflicts with its registered method contract"
                        ),
                    )
                resolved_order = registered_order or declared_order
                if resolved_order is None and spec.placement is None:
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"External builder '{n}' component {index} has no placement "
                            "or decode-order contract"
                        ),
                    )
                item._codewm_external_processor = True
                item._codewm_method = n
                item._codewm_placement = (
                    spec.placement.value if spec.placement is not None else None
                )
                item._codewm_decode_order = (
                    resolved_order.as_dict() if resolved_order is not None else None
                )
                item._codewm_component = (
                    spec.components[index] if spec.components else n
                )
                item._codewm_contract_variant = (
                    active_contract.variant if plugin is not None else "default"
                )
                item._codewm_runtime_context = runtime_context
                item._codewm_resources = resolved_resources[index]
                item._codewm_resource_contract = (
                    resolved_resources[index].as_dict()
                )
                if plugin is not None:
                    item._codewm_detection_contract = (
                        plugin.detection_contract.as_dict()
                    )
                if spec.generation_evidence_finalizer is not None:
                    item._codewm_generation_evidence_finalizer = (
                        spec.generation_evidence_finalizer
                    )
            chain.extend(list(lp))
    return LogitsProcessorList(chain) if chain else None


def audit_processor_resource_contract(
    processor: LogitsProcessor,
    resources: ResolvedMethodResources,
    input_ids: Any,
    scores: Any,
) -> dict[str, Any]:
    """Execute one admission-test step and verify declared support/OOD behavior."""
    import torch

    if not isinstance(processor, LogitsProcessor):
        raise TypeError("processor contract audit requires a LogitsProcessor")
    if not isinstance(scores, torch.Tensor) or scores.ndim != 2:
        raise TypeError("processor contract audit scores must be a rank-2 tensor")
    if int(scores.shape[-1]) != resources.score_vocab_size:
        raise ValueError(
            "processor contract audit score width mismatch: "
            f"expected {resources.score_vocab_size}, got {int(scores.shape[-1])}"
        )

    before = scores.detach().clone()
    output = processor(input_ids, scores.detach().clone())
    if not isinstance(output, torch.Tensor) or output.shape != before.shape:
        raise ValueError(
            "processor contract audit requires a tensor output with unchanged shape"
        )
    after = output.detach()
    before_finite = torch.isfinite(before)
    after_finite = torch.isfinite(after)
    effect = resources.contract.support_effect

    if effect is SupportEffect.PRESERVE and not torch.equal(
        before_finite, after_finite
    ):
        raise ValueError("support_effect=preserve violated")
    if effect is SupportEffect.MAY_REDUCE and bool(
        torch.any(after_finite & ~before_finite).item()
    ):
        raise ValueError("support_effect=may_reduce expanded finite support")
    if effect is SupportEffect.MAY_EXPAND and bool(
        torch.any(before_finite & ~after_finite).item()
    ):
        raise ValueError("support_effect=may_expand reduced finite support")

    out_of_domain_size = resources.out_of_domain_size
    if (
        resources.contract.out_of_domain_policy is OutOfDomainPolicy.PASS_THROUGH
        and out_of_domain_size > 0
    ):
        before_ood = before[..., resources.vocab_size :]
        after_ood = after[..., resources.vocab_size :]
        if not torch.allclose(
            before_ood,
            after_ood,
            rtol=0.0,
            atol=0.0,
            equal_nan=True,
        ):
            raise ValueError("out_of_domain_policy=pass_through violated")

    return {
        "support_effect": effect.value,
        "out_of_domain_policy": resources.contract.out_of_domain_policy.value,
        "input_candidate_counts": [
            int(value) for value in before_finite.sum(dim=-1).cpu().tolist()
        ],
        "output_candidate_counts": [
            int(value) for value in after_finite.sum(dim=-1).cpu().tolist()
        ],
        "vocab_size": resources.vocab_size,
        "score_vocab_size": resources.score_vocab_size,
        "passed": True,
    }


def validate_processor_detection_result(
    processor: LogitsProcessor,
    result: Any,
) -> None:
    """Verify that a detector result exposes at least one declared score field."""
    contract = getattr(processor, "_codewm_detection_contract", None)
    if not isinstance(contract, Mapping):
        return
    if contract.get("mode") != MethodDetectionMode.PROCESSOR_STATE.value:
        return
    if not isinstance(result, Mapping):
        raise ValueError("processor-state detection result must be a mapping")
    fields = tuple(contract.get("score_fields") or ())
    if not any(field in result for field in fields):
        raise ValueError(
            "processor-state detection result contains none of its declared score "
            f"fields: declared={list(fields)}, returned={sorted(result)}"
        )

def concat_lp(a: Optional[LogitsProcessorList], b: Optional[LogitsProcessorList]) -> Optional[LogitsProcessorList]:
    """Concatenate two LogitsProcessorLists preserving order."""
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return LogitsProcessorList(list(a) + list(b))
