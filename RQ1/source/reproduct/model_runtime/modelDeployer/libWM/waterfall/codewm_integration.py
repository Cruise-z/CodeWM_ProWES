"""CodeWM decode-order contract for WATERFALL."""

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
from .waterfallLP import build_codewm, finalize_codewm_generation_evidence


CODEWM_INTEGRATION = MethodDecodeContract(
    name="waterfall",
    component_orders=(
        DecodeOrder.between(DecodeAnchor.TOP_P, DecodeAnchor.SAMPLER),
    ),
    component_resources=(
        MethodResourceContract(
            vocab_domain=VocabDomain.TOKENIZER_BASE,
            score_domain=ScoreDomain.MODEL_OUTPUT_LOGITS,
            support_effect=SupportEffect.PRESERVE,
            out_of_domain_policy=OutOfDomainPolicy.PASS_THROUGH,
        ),
    ),
)

CODEWM_PLUGIN = MethodIntegrationPlugin(
    contract=CODEWM_INTEGRATION,
    builder=build_codewm,
    required_framework_components=(FrameworkComponent.TOKENIZER,),
    parameter_contract=MethodParameterContract(
        accepted=(
            "id_mu",
            "k_p",
            "kappa",
            "n_gram",
            "wm_fn",
            "auto_reset",
            "detect_mode",
        ),
    ),
    detection_contract=MethodDetectionContract(
        mode=MethodDetectionMode.PROCESSOR_STATE,
        score_fields=("q_score",),
        score_direction=DetectionScoreDirection.HIGHER,
    ),
    generation_evidence_finalizer=finalize_codewm_generation_evidence,
)
