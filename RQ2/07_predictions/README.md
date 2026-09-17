# Prediction index

Predictions are kept beside the transformation that produced them to preserve
one-to-one auditability:

- clean: `../../results/RQ2/02_training/clean_predictions/`;
- rule attacked: `../../results/RQ2/03_rule_attacks/evaluated/`;
- LLM attacked: `../../results/RQ2/05_llm_rag/main_eval/`.

Every evaluated row retains true bits, clean prediction, attacked prediction,
stable attack UID, attack metadata, and detector status.
