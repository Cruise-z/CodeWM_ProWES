"""CodeWM decode-order contract for the independently verified MCGMark adapter."""

from processors import (
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
from .mcgMarkLP import build_codewm


CODEWM_INTEGRATION = MethodDecodeContract(
    name="mcgmark",
    component_orders=(
        DecodeOrder.between(DecodeAnchor.HOST_PROCESSORS, DecodeAnchor.TEMPERATURE),
    ),
    component_resources=(
        MethodResourceContract(
            vocab_domain=VocabDomain.TOKENIZER_FULL,
            score_domain=ScoreDomain.MODEL_OUTPUT_LOGITS,
            support_effect=SupportEffect.PRESERVE,
            out_of_domain_policy=OutOfDomainPolicy.METHOD_DEFINED,
        ),
    ),
)

CODEWM_PLUGIN = MethodIntegrationPlugin(
    contract=CODEWM_INTEGRATION,
    builder=build_codewm,
    required_framework_components=(FrameworkComponent.TOKENIZER,),
    parameter_contract=MethodParameterContract(
        accepted=("watermark_info", "gamma", "delta", "hash_key"),
    ),
    detection_contract=MethodDetectionContract(
        mode=MethodDetectionMode.UNAVAILABLE,
    ),
)
