"""CodeWM contracts for CodeIP's released optional PDA composition."""

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
from .codeipLP import build_codewm
from .codeipLP import (
    finalize_codewm_generation_evidence,
    resolve_codewm_use_pda,
)


_PRE_WARPER = DecodeOrder.between(
    DecodeAnchor.HOST_PROCESSORS,
    DecodeAnchor.TEMPERATURE,
)
_WATERMARK_NODE = "method.codeip.watermark"
_PDA_TYPE_NODE = "method.codeip.pda_type"
_WATERMARK_ORDER = DecodeOrder(
    after=_PRE_WARPER.after,
    before=(_PDA_TYPE_NODE,),
)
_PDA_TYPE_ORDER = DecodeOrder(
    after=(_WATERMARK_NODE,),
    before=_PRE_WARPER.before,
)

CODEWM_INTEGRATION = MethodDecodeContract(
    name="codeip",
    variant="random",
    components=("watermark",),
    component_orders=(_PRE_WARPER,),
    component_resources=(
        MethodResourceContract(
            vocab_domain=VocabDomain.TOKENIZER_FULL,
            score_domain=ScoreDomain.MODEL_OUTPUT_LOGITS,
            support_effect=SupportEffect.PRESERVE,
            out_of_domain_policy=OutOfDomainPolicy.PASS_THROUGH,
        ),
    ),
)

CODEWM_COMPOSITE_INTEGRATION = MethodDecodeContract(
    name="codeip",
    variant="composite",
    components=("watermark", "pda_type"),
    component_orders=(_WATERMARK_ORDER, _PDA_TYPE_ORDER),
    component_resources=(
        MethodResourceContract(
            vocab_domain=VocabDomain.TOKENIZER_FULL,
            score_domain=ScoreDomain.MODEL_OUTPUT_LOGITS,
            support_effect=SupportEffect.PRESERVE,
            out_of_domain_policy=OutOfDomainPolicy.PASS_THROUGH,
        ),
        MethodResourceContract(
            vocab_domain=VocabDomain.TOKENIZER_BASE,
            score_domain=ScoreDomain.MODEL_OUTPUT_LOGITS,
            support_effect=SupportEffect.PRESERVE,
            out_of_domain_policy=OutOfDomainPolicy.PASS_THROUGH,
        ),
    ),
)


def _select_codewm_contract(params):
    if resolve_codewm_use_pda(params):
        return CODEWM_COMPOSITE_INTEGRATION
    return CODEWM_INTEGRATION


CODEWM_PLUGIN = MethodIntegrationPlugin(
    contract=CODEWM_INTEGRATION,
    builder=build_codewm,
    required_framework_components=(
        FrameworkComponent.TOKENIZER,
        FrameworkComponent.DEVICE,
    ),
    parameter_contract=MethodParameterContract(
        accepted=(
            "use_pda",
            "mode",
            "language",
            "delta",
            "gamma",
            "message_code_len",
            "encode_ratio",
            "top_k",
            "message",
            "pda_model_path",
        ),
    ),
    detection_contract=MethodDetectionContract(
        mode=MethodDetectionMode.PROCESSOR_STATE,
        score_fields=("z_score", "bit_accuracy"),
        score_direction=DetectionScoreDirection.HIGHER,
    ),
    generation_evidence_finalizer=finalize_codewm_generation_evidence,
    variant_contracts=(CODEWM_COMPOSITE_INTEGRATION,),
    contract_selector=_select_codewm_contract,
)
