# Scripts

Scripts activos de entrega:

- `run_delivery_validation.py`: validacion Docker/API oficial de entrega. Debe
  terminar con `PASS=18, FAIL=0`.
- `beta_validation_support.py`: catalogo compartido de preguntas y criterios de
  validacion usados por la validacion oficial.
- `generate_sample_pdfs.py`: regeneracion controlada de PDFs mock versionados.
- `seed_rag.py`: limpia ChromaDB y carga solo los PDFs `v2_*` oficiales de
  entrega.

Scripts legacy o historicos:

- `archive/run_beta_validation_legacy.py`: conserva validaciones reales opt-in del flujo
  estable anterior para regresion.
- `archive/run_deepagents_comparison_legacy.py`: comparativa historica entre DeepAgents,
  sidecar y legacy.
- `archive/evaluate_api_responses_legacy.py`: evaluador critico anterior,
  reemplazado por `run_delivery_validation.py`.
