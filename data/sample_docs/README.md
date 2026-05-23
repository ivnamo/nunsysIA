# Documentos mock de demo

Estos PDFs son datos ficticios para validar la POC con consultas RAG realistas.

Para regenerarlos:

```powershell
.\.venv\Scripts\python.exe scripts\generate_sample_pdfs.py
```

Documentos base generados, conservados solo como historico de desarrollo:

- `contrato_marco_logistica_2026.pdf`: plazos de entrega, trazabilidad y exclusiones.
- `anexo_penalizaciones_sla.pdf`: penalizaciones por retrasos y evidencias necesarias.
- `procedimiento_produccion_bloqueos.pdf`: estados, bloqueos, retrasos y escalado.
- `politica_calidad_entregas.pdf`: controles de calidad y documentacion de entrega.
- `condiciones_comerciales_northwind.pdf`: reglas comerciales, ERP e impacto economico.

Documentos oficiales de entrega y demo (`v2_*`):

- `v2_contrato_marco_logistica_2026.pdf`: contrato logistico en 4 paginas con alcance, plazos, trazabilidad y casos de decision.
- `v2_anexo_penalizaciones_sla.pdf`: anexo SLA en 4 paginas con matriz, evidencias, exclusiones y calculo economico.
- `v2_procedimiento_produccion_bloqueos.pdf`: procedimiento productivo en 4 paginas con estados, bloqueos, retrasos y escalado.
- `v2_politica_calidad_entregas.pdf`: politica de calidad en 3 paginas con controles, incidencias e indicadores.
- `v2_condiciones_comerciales_northwind.pdf`: condiciones comerciales en 4 paginas con ERP, importes, prioridad y trazabilidad.

Cada pagina extendida incluye un marcador de validacion, por ejemplo `CM-V2-P03`
o `SLA-V2-P02`, para comprobar si el sistema recupera la pagina concreta.
