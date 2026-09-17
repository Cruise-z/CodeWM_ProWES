"""CodeWM decode-order contract for EWD."""

from processors import (
    DetectionScoreDirection,
    DecodeAnchor,
    DecodeOrder,
    FrameworkComponent,
    MethodDecodeContract,
    MethodDetectionContract,
    MethodDetectionMode,
    MethodIntegrationPlugin,
    MethodParameterContract,
    MethodResourceContract,
    OutOfDomainPolicy,
    ScoreDomain,
    SupportEffect,
    VocabDomain,
)
from .ewdLP import build_codewm, finalize_codewm_generation_evidence


CODEWM_INTEGRATION = MethodDecodeContract(
    name="ewd",
    component_orders=(
        DecodeOrder.between(DecodeAnchor.HOST_PROCESSORS, DecodeAnchor.TEMPERATURE),
    ),
    component_resources=(
        MethodResourceContract(
            vocab_domain=VocabDomain.TOKENIZER_FULL,
            score_domain=ScoreDomain.MODEL_OUTPUT_LOGITS,
            support_effect=SupportEffect.PRESERVE,
            out_of_domain_policy=OutOfDomainPolicy.PASS_THROUGH,
        ),
    ),
)

CODEWM_PLUGIN = MethodIntegrationPlugin(
    contract=CODEWM_INTEGRATION,
    builder=build_codewm,
    required_framework_components=(
        FrameworkComponent.TOKENIZER,
        FrameworkComponent.MODEL,
        FrameworkComponent.DEVICE,
    ),
    parameter_contract=MethodParameterContract(
        accepted=("gamma", "delta", "hash_key", "z_threshold", "prefix_length"),
    ),
    detection_contract=MethodDetectionContract(
        mode=MethodDetectionMode.PROCESSOR_STATE,
        score_fields=("score",),
        score_direction=DetectionScoreDirection.HIGHER,
    ),
    generation_evidence_finalizer=finalize_codewm_generation_evidence,
)
