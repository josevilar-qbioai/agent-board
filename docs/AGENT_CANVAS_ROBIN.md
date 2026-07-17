# Agent Canvas — Agent-Board × Robin Benchmark

**Proyecto:** Q · Agent Board (perfil `biocomputacion`)
**Fecha:** 2026-07-10
**Autor:** Jose Antonio Vilar — QMetrika Labs
**Benchmark:** Robin (Nature 655, 496–505, julio 2026, doi:10.1038/s41586-026-10652-y)
**Framework:** Agent Canvas Model v2.0

---

## Contexto

Este documento aplica el framework Agent Canvas a cada agente del perfil
`biocomputacion` del Agent-Board, usando Robin como benchmark arquitectónico.
Robin es un sistema multi-agente publicado en Nature (julio 2026) que automatiza
descubrimiento científico — propuso ripasudil como candidato terapéutico para
degeneración macular seca (dAMD) y lo validó experimentalmente.

### Mapeo Robin → Agent-Board

| Robin | Función | Agent-Board (biocomputacion) | Función |
|-------|---------|------------------------------|---------|
| **Crow** | Revisión de literatura concisa | **Analista de Genómica del Cáncer** + **Analista de Variantes Genómicas** | Curación de datos, inventario |
| **Falcon** | Evaluación profunda de candidatos | **Reviewer** | Verificación adversarial |
| **Finch** | Análisis autónomo de datos (Jupyter) | **Motor Biofísico** | Cómputo ΔG, ESM, CNN |
| **Robin (orquestador)** | Interpreta resultados, propone experimentos | **Broker + Tablero** | Orquestación con puerta humana |
| — | — | **Diseñador de mRNA** | Sin equivalente en Robin |
| — | — | **Escritor Científico** | Sin equivalente en Robin |

### Lecciones clave de Robin para Agent-Board

1. **La ablación demuestra que cada agente es esencial.** Sin Crow, las referencias
   alucinadas suben de ~6% a niveles inaceptables. Sin Falcon, la calidad de los
   informes finales se degrada. Implicación: cada agente del Agent-Board debe tener
   una métrica de ablación definida.

2. **Lab-in-the-loop valida human-in-the-loop.** Robin genera hipótesis → humanos
   ejecutan experimentos → resultados retroalimentan a Robin. Esto es exactamente
   el patrón gate del Agent-Board (agente propone → humano aprueba → efecto se
   ejecuta), validado experimentalmente en Nature.

3. **Multi-modelo funciona.** Robin usa OpenAI o4-mini para agentes y Claude 3.7
   Sonnet como juez. Agent-Board ya lleva esto más lejos: mistral-local, gemini-flash,
   gpt-4o, opus, sonnet — cada agente con su modelo óptimo.

4. **El entorno de ejecución importa.** Finch usa Aviary (contenedor Docker
   estandarizado). Motor Biofísico usa PyTorch local. Ambos validan que el agente
   computacional necesita un sandbox determinista, no solo un prompt.

5. **Guardrails como arquitectura, no parche.** Robin filtra compuestos inseguros
   antes de proponerlos. Agent-Board tiene 15 amenazas catalogadas con mitigaciones.
   Robin valida que este nivel de rigor es publicable en Nature.

---

## Canvas 1: Analista de Genómica del Cáncer

**ID:** `genomica` · **Role:** `read` · **Model:** `mistral-local` · **Unit:** Genómica
**Equivalente Robin:** Crow (revisión de literatura concisa)

```
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 8. INTEGRACIONES   | 7. ACTIVIDADES     | 2. PROPUESTA DE        | 4. PERSONALIDAD    | 1. SEGMENTO        |
|                    |                    | VALOR                  |                    |                    |
| ClinVar API        | Inventario de      | Reduce de horas a      | Rol: curador de    | Primario:          |
| UniProt API        | variantes          | minutos la curación    | datos              | investigador PI    |
| gnomAD API         | missense por gen   | de datasets genómicos  |                    | (Jose Antonio)     |
| InterPro API       |                    | para entrenamiento     | Tono: técnico,     |                    |
|                    | Filtrado de        | de CNN                 | conciso, estructu- | Secundario:        |
| TCGA MC3 (datos    | etiquetas ClinVar  |                        | rado (JSON)        | pipeline auto-     |
| somáticos locales) | (encode_label)     | Robin Crow: reduce     |                    | matizado (L1)      |
|                    |                    | revisión lit. de       | Autonomía:         |                    |
| FASTA locales      | Ratio P/B y        | días a minutos.        | SOLO LECTURA       |                    |
| (CDS por gen)      | validación de      | Aquí: curación de      | — nunca escribe,   |                    |
|                    | dataset            | datos de horas a       | solo reporta       |                    |
|                    |--------------------+ minutos                +--------------------+                    |
|                    | 6. RECURSOS        |                        | 3. CANALES         |                    |
|                    |                    |                        |                    |                    |
|                    | ClinVar VCF/XML    |                        | CLI (orchestrator  |                    |
|                    | Tablas gnomAD      |                        | .py)               |                    |
|                    | FASTA de CDS       |                        | Tablero Kanban     |                    |
|                    | encode_label()     |                        | (tarjeta)          |                    |
|                    | rules (CLAUDE.md)  |                        | JSON estructurado  |                    |
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 9. COSTES Y RIESGOS                             | 5. KPIs                                            |
|                                                  |                                                    |
| Coste: ~0 €/M tok (mistral-local)               | Tasa de etiquetas correctas (encode_label) >99%    |
| Riesgo técnico: parsing ClinVar "Conflicting"    | Ratio P/B del dataset generado (target ≥3)         |
| mal clasificado como patogénico (ver CLAUDE.md)  | Variantes descartadas por ambigüedad (monitorizar) |
| Riesgo de datos: NCBI bloqueado desde sandbox    | Tiempo de curación por gen (<5 min)                |
| Mitigación: scripts de descarga en LOCAL         | Ablación: sin este agente, ¿cuántas etiquetas      |
|                                                  | erróneas entran al pipeline? (benchmark Robin)     |
+--------------------------------------------------+----------------------------------------------------+
```

### Nota de ablación (patrón Robin)

Sin el Analista de Genómica, el pipeline L1 recibiría variantes con etiquetas
ambiguas ("Conflicting classifications of pathogenicity" clasificado como
pathogenic). El error documentado en CLAUDE.md demuestra que este agente es
esencial — su función de filtrado es la primera línea de defensa contra datos
contaminados. Equivale a la demostración de Robin de que sin Crow, las
referencias alucinadas se disparan.

---

## Canvas 2: Analista de Variantes Genómicas

**ID:** `variantes` · **Role:** `read` · **Model:** `gemini-2.0-flash` · **Unit:** Genómica
**Equivalente Robin:** Crow (segunda instancia, exploración rápida)

```
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 8. INTEGRACIONES   | 7. ACTIVIDADES     | 2. PROPUESTA DE        | 4. PERSONALIDAD    | 1. SEGMENTO        |
|                    |                    | VALOR                  |                    |                    |
| ClinVar API        | Consulta rápida    | Responde preguntas     | Rol: explorador    | Primario:          |
| dbSNP API          | de variantes       | sobre variantes        | analítico          | investigador PI    |
| AlphaFold API      | individuales       | específicas en         |                    |                    |
| OpenTargets        |                    | segundos, no horas     | Tono: informativo, | Secundario:        |
| GWAS Catalog       | Análisis de        |                        | basado en evidencia| verificador        |
| PubMed             | frecuencias        | Robin Crow: sintetiza  |                    | clínico (humano)   |
| Semantic Scholar   | alélicas           | literatura rápido.     | Autonomía:         |                    |
|                    |                    | Aquí: sintetiza datos  | SOLO LECTURA       |                    |
|                    | Cross-referencia   | genómicos rápido       | — reporta hallaz-  |                    |
|                    | multi-base de      |                        | gos, no decide     |                    |
|                    | datos              |                        |                    |                    |
|                    |--------------------+                        +--------------------+                    |
|                    | 6. RECURSOS        |                        | 3. CANALES         |                    |
|                    |                    |                        |                    |                    |
|                    | Bases públicas     |                        | CLI / API          |                    |
|                    | (ClinVar, gnomAD,  |                        | Tablero Kanban     |                    |
|                    | UniProt, dbSNP)    |                        | Informe JSON       |                    |
|                    | Literatura PubMed  |                        |                    |                    |
|                    | Anotaciones AlphaF.|                        |                    |                    |
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 9. COSTES Y RIESGOS                             | 5. KPIs                                            |
|                                                  |                                                    |
| Coste: 0.12 €/M tok (gemini-2.0-flash)          | Precisión de cross-referencia (% correcto)         |
| Muy bajo — ideal para consultas de alto volumen  | Latencia media por consulta (<10s)                 |
| Riesgo: alucinación en síntesis de literatura    | Cobertura de fuentes consultadas (≥3 bases/query)  |
| Mitigación: solo lectura + verificación humana   | Tasa de hallazgos confirmados por Reviewer         |
| Riesgo: API rate limits en bases públicas        | Ablación: sin este agente, cuántas consultas       |
| Mitigación: caché local + retry con backoff      | manuales haría el PI por gen (~20-30 consultas)    |
+--------------------------------------------------+----------------------------------------------------+
```

### Diferencia clave con Robin Crow

Robin Crow produce revisiones de literatura; este agente produce síntesis de
datos genómicos multi-fuente. Robin demostró que la separación entre búsqueda
concisa (Crow) y evaluación profunda (Falcon) es esencial. Aquí esa separación
se mantiene: el Analista explora, el Reviewer verifica.

---

## Canvas 3: Diseñador de mRNA

**ID:** `mrna` · **Role:** `effect` · **Model:** `gpt-4o` · **Unit:** Terapéutica
**Equivalente Robin:** Sin equivalente directo (Robin no opera en diseño de secuencias)

```
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 8. INTEGRACIONES   | 7. ACTIVIDADES     | 2. PROPUESTA DE        | 4. PERSONALIDAD    | 1. SEGMENTO        |
|                    |                    | VALOR                  |                    |                    |
| Biohub ESMFold2    | Selección de       | Optimiza codones de    | Rol: ingeniero de  | Primario:          |
| (estructura RNA)   | codones óptimos    | mRNA terapéutico       | secuencias         | investigador PI    |
|                    |                    | integrando ΔG de       |                    |                    |
| ViennaRNA/RNAfold  | Evaluación de      | apilamiento + MFE      | Tono: técnico,     | Secundario:        |
| (MFE predicción)   | estructura 2ria    |                        | cuantitativo       | pharma/biotech     |
|                    |                    | Resultados superan     |                    | (futuro BIZ-5)     |
| Motor ΔG local     | Comparativa con    | BNT162b2 y mRNA-1273   | Autonomía:         |                    |
| (energy.py)        | vacunas existentes | (Pfizer y Moderna)     | CON EFECTOS        |                    |
|                    |                    |                        | — ejecuta beam     |                    |
| Tabla de uso de    | Beam search con    | Protegido por          | search, requiere   |                    |
| codones (humano)   | MFE integrado      | patente P202630522     | gate humano para   |                    |
|                    |--------------------+                        | resultados finales +--------------------+
|                    | 6. RECURSOS        |                        | 3. CANALES         |                    |
|                    |                    |                        |                    |                    |
|                    | 08_codon_optimizer | Código NO publicado    | CLI pipeline L2    |                    |
|                    | .py (propietario)  |                        | Tablero Kanban     |                    |
|                    | Parámetros SantaLu-|                        | FASTA + informe    |                    |
|                    | cia/Turner (NN)    |                        |                    |                    |
|                    | Tablas de uso de   |                        |                    |                    |
|                    | codones por org.   |                        |                    |                    |
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 9. COSTES Y RIESGOS                             | 5. KPIs                                            |
|                                                  |                                                    |
| Coste: 5.0 €/M tok (gpt-4o) + local (beam)      | ΔG medio optimizado vs nativo (target <-1.5)      |
| Beam search: 13s por gen (1273 codones, bw=5)    | MFE/nt del mRNA optimizado (target <-0.35)        |
| Riesgo IP: código propietario, no publicar       | Mejora vs BNT162b2/mRNA-1273 (ambas métricas)     |
| Riesgo técnico: RNAfold lento para beam anchos   | GC% en rango óptimo (55-65%)                       |
| Mitigación: ESMFold2 como alternativa (TECH-5)   | Frontera de Pareto ΔG×MFE (Fase A roadmap)        |
| Riesgo regulatorio: PCT deadline abril 2027      | Ablación: sin optimizador, solo GC-max → pierde   |
|                                                  | ~0.11 kcal/mol en ΔG y ~0.05 en MFE vs beam       |
+--------------------------------------------------+----------------------------------------------------+
```

### Nota estratégica

Este agente no tiene equivalente en Robin porque Robin opera en drug repurposing
(identificar compuestos existentes), no en diseño de secuencias. Esto posiciona
a Agent-Board como más ambicioso: no solo descubre, sino que **diseña**.
El optimizador dual (greedy + beam search) es propiedad intelectual protegida
por P202630522.

---

## Canvas 4: Motor Biofísico

**ID:** `biofisico` · **Role:** `effect` · **Model:** `opus` · **Unit:** Terapéutica
**Equivalente Robin:** Finch (análisis autónomo de datos)

```
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 8. INTEGRACIONES   | 7. ACTIVIDADES     | 2. PROPUESTA DE        | 4. PERSONALIDAD    | 1. SEGMENTO        |
|                    |                    | VALOR                  |                    |                    |
| PyTorch (local)    | Perfiles ΔG        | Genera la señal        | Rol: motor de      | Primario:          |
| ESM-1v / ESMC-6B   | (energy.py)        | biofísica que alimenta | cómputo            | pipeline L1/L2     |
| (Biohub API o HF)  |                    | toda la plataforma     |                    | automatizado       |
|                    | Scoring ESM-1v     |                        | Tono: determinista |                    |
| EnergySignalCNN    | (log-likelihood    | Sin este agente, no    | — sin creatividad, | Secundario:        |
| (~228K params)     | ratio por posición)| hay clasificación ni   | solo precisión     | investigador PI    |
|                    |                    | optimización           | numérica           | (diagnóstico)      |
| GradCAM1D          | Tensorización      |                        |                    |                    |
| (explicabilidad)   | (11ch × 128nt)     | Robin Finch: escribe   | Autonomía:         |                    |
|                    |                    | código Python en       | CON EFECTOS        |                    |
| CUDA/GPU local     | Forward CNN +      | Jupyter. Aquí: ejecuta | — cómputo pesado   |                    |
|                    | GradCAM            | código determinista    | local, gate para   |                    |
|                    |--------------------+ preexistente (más      | resultados finales +--------------------+
|                    | 6. RECURSOS        | fiable, menos flexible)|                    |                    |
|                    |                    |                        | 3. CANALES         |                    |
|                    | core/energy.py     |                        |                    |                    |
|                    | core/model.py      |                        | CLI pipeline       |                    |
|                    | core/genetics.py   |                        | Tablero Kanban     |                    |
|                    | Params NN (Santa-  |                        | Tensores + modelos |                    |
|                    | Lucia 98, Turner04)|                        | en studies/{gen}/  |                    |
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 9. COSTES Y RIESGOS                             | 5. KPIs                                            |
|                                                  |                                                    |
| Coste modelo: ~0 € (PyTorch local, GPU propia)   | AUC intra-gen (target >0.85 para genes validados) |
| Coste Opus: 15 €/M tok (solo para razonamiento   | AUC zero-shot cross-gen (gradiente de transf.)    |
| complejo, no para el cómputo en sí)              | Tiempo de generación de tensores por gen (<2 min)  |
| Riesgo: ESM-1v windowing para proteínas >1022 aa | Concordancia GradCAM con dominios UniProt          |
| Mitigación: windowing documentado, ESMC-6B       | Ablación (Robin): sin motor biofísico, el pipeline |
| Riesgo: GPU insuficiente para ESMC-6B            | no tiene señal — AUC cae a 0.5 (aleatorio).       |
| Mitigación: API Biohub como fallback             | Este es el agente con mayor impacto de ablación    |
+--------------------------------------------------+----------------------------------------------------+
```

### Comparativa directa con Robin Finch

| Dimensión | Robin Finch | Motor Biofísico |
|-----------|-------------|-----------------|
| Ejecución | Genera código Python/R en tiempo real | Ejecuta código determinista preexistente |
| Entorno | Aviary (Docker estandarizado) | PyTorch local + GPU |
| Flexibilidad | Alta (escribe código ad hoc) | Baja (pipeline fijo, pero reproducible) |
| Fiabilidad | 22.8 ± 1.7% en BixBench | >99% (determinista, mismo input → mismo output) |
| Coste | API o4-mini | ~0 € (local) |
| Patrón | ReAct (razona → actúa → observa) | Execute (ejecuta → reporta) |

**Lección de Robin:** Finch demuestra que un agente de análisis necesita un entorno
de ejecución estructurado. El Motor Biofísico ya lo tiene (PyTorch + scripts
validados), lo que lo hace más fiable que Finch pero menos flexible. Para tareas
exploratorias (E7, E3), considerar un agente tipo Finch con Jupyter.

---

## Canvas 5: Escritor Científico

**ID:** `escritor` · **Role:** `write` · **Model:** `sonnet` · **Unit:** Publicación
**Equivalente Robin:** No tiene equivalente directo (Robin no genera manuscritos)

```
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 8. INTEGRACIONES   | 7. ACTIVIDADES     | 2. PROPUESTA DE        | 4. PERSONALIDAD    | 1. SEGMENTO        |
|                    |                    | VALOR                  |                    |                    |
| Quarto (render)    | Redacción de       | Transforma resultados  | Rol: escritor      | Primario:          |
| LaTeX / BibTeX     | informes clínicos  | técnicos en prosa      | científico         | investigador PI    |
| Zenodo API         | estructurados      | científica publicable  |                    | (publicación)      |
|                    |                    |                        | Tono: académico    |                    |
| GitHub (repos      | Generación de      | Ahorra 20-40 horas     | formal, preciso,   | Secundario:        |
| públicos)          | abstracts, intros, | por manuscrito en      | pasivo científico  | co-autores,        |
|                    | discusiones        | redacción              |                    | revisores          |
| Overleaf (futuro)  |                    |                        | Autonomía:         |                    |
|                    | CHANGELOG y docs   | Robin no tiene este    | ESCRITURA          |                    |
|                    | técnicos           | agente — genera solo   | — escribe docs,    |                    |
|                    |                    | informes internos      | NUNCA código       |                    |
|                    |--------------------+                        +--------------------+                    |
|                    | 6. RECURSOS        |                        | 3. CANALES         |                    |
|                    |                    |                        |                    |                    |
|                    | Resultados de CNN  |                        | Quarto Manuscript  |                    |
|                    | Figuras generadas  |                        | Tablero Kanban     |                    |
|                    | CLAUDE.md (contexto|                        | .md / .docx / .tex |                    |
|                    | del proyecto)      |                        |                    |                    |
|                    | Papers previos     |                        |                    |                    |
|                    | (estilo referencia)|                        |                    |                    |
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 9. COSTES Y RIESGOS                             | 5. KPIs                                            |
|                                                  |                                                    |
| Coste: 3.0 €/M tok (sonnet) — moderado          | Aceptación por PI sin reescritura mayor (>70%)     |
| Riesgo: tono no académico o demasiado "IA"       | Tiempo ahorrado vs redacción manual (horas/paper)  |
| Mitigación: prompt con estilo de papers previos  | Consistencia terminológica (Λ, Φ, S, ⊗)           |
| Riesgo: citar papers inexistentes (alucinación)  | Tasa de citas verificadas (target 100%)            |
| Mitigación: el Reviewer verifica toda cita       | Ablación: sin este agente, el PI escribe todo      |
| Riesgo: inconsistencia entre secciones           | manualmente — ~40h/paper → este agente reduce a ~8 |
+--------------------------------------------------+----------------------------------------------------+
```

---

## Canvas 6: Reviewer

**ID:** `reviewer` · **Role:** `verify` · **Model:** `sonnet` · **Unit:** QA
**Equivalente Robin:** Falcon (evaluación profunda de candidatos)

```
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 8. INTEGRACIONES   | 7. ACTIVIDADES     | 2. PROPUESTA DE        | 4. PERSONALIDAD    | 1. SEGMENTO        |
|                    |                    | VALOR                  |                    |                    |
| CADD / REVEL /     | Verificación       | Garantiza que ningún   | Rol: verificador   | Primario:          |
| AlphaMissense      | adversarial de     | resultado sale del     | adversarial        | pipeline (QA       |
| (benchmark L1)     | predicciones CNN   | pipeline sin           |                    | automatizado)      |
|                    |                    | validación cruzada     | Tono: escéptico,   |                    |
| ClinGen / ACMG     | Cross-referencia   |                        | riguroso, basado   | Secundario:        |
| guidelines         | con predictores    | Robin Falcon: sin él,  | en evidencia       | genetista clínico  |
|                    | establecidos       | la calidad del informe |                    | (futuro BIZ-4)     |
| UniProt dominios   |                    | final se degrada.      | Autonomía:         |                    |
|                    | Verificación de    | Aquí: sin Reviewer,    | VERIFICACIÓN       |                    |
| PubMed / Europe    | citas y referencias| variantes mal          | — solo juzga,      |                    |
| PMC (verificar     |                    | clasificadas llegarían | NUNCA corrige      |                    |
| que citas existen) | Validación ACMG    | al informe clínico     |                    |                    |
|                    |--------------------+                        +--------------------+                    |
|                    | 6. RECURSOS        |                        | 3. CANALES         |                    |
|                    |                    |                        |                    |                    |
|                    | Resultados de CNN  |                        | JSON estructurado  |                    |
|                    | + GradCAM          |                        | {passed, issues,   |                    |
|                    | Bases de referencia|                        |  summary}          |                    |
|                    | (CADD, REVEL)      |                        | Tablero Kanban     |                    |
|                    | ACMG criteria      |                        | (columna Review)   |                    |
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 9. COSTES Y RIESGOS                             | 5. KPIs                                            |
|                                                  |                                                    |
| Coste: 3.0 €/M tok (sonnet)                     | Tasa de detección de errores (target >95%)         |
| Riesgo: aprobar falsos positivos por deferencia  | Concordancia con ACMG guidelines (%)              |
| Mitigación: prompt adversarial ("intenta         | Concordancia con CADD/REVEL en variantes de test   |
| demostrar que NO cumple")                        | Tasa de falsos negativos (errores no detectados)   |
| Riesgo: bloquear pipeline con falsos negativos   | Ablación (Robin Falcon): sin Reviewer, ¿cuántas   |
| Mitigación: output estructurado con evidencia    | predicciones incorrectas llegan al informe final?  |
| → el PI puede overridear con justificación       | Robin: sin Falcon, calidad del informe cae         |
+--------------------------------------------------+----------------------------------------------------+
```

### Comparativa directa con Robin Falcon

| Dimensión | Robin Falcon | Reviewer |
|-----------|-------------|----------|
| Función | Evalúa candidatos terapéuticos con literatura profunda | Verifica predicciones CNN contra bases de referencia |
| Modelo | OpenAI o4-mini | Sonnet (Claude) |
| Output | Informe de evaluación por candidato | Veredicto estructurado {passed, issues, summary} |
| Autonomía | No puede aprobar — Robin decide | No puede corregir — solo juzga, el PI decide |
| Ablación | Sin Falcon, la calidad del informe final se degrada | Sin Reviewer, variantes incorrectas podrían llegar al clínico |

**Lección de Robin:** La separación autor/juez es fundamental. Robin no deja que
Crow (que generó la búsqueda) evalúe su propio trabajo — Falcon es independiente.
Agent-Board replica esto: el Motor Biofísico genera, el Reviewer verifica. Nunca
son el mismo agente.

---

## Canvas 0: Agent-Board como sistema (meta-canvas)

Este canvas describe el sistema completo, no un agente individual.

```
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 8. INTEGRACIONES   | 7. ACTIVIDADES     | 2. PROPUESTA DE        | 4. PERSONALIDAD    | 1. SEGMENTO        |
|                    |                    | VALOR                  |                    |                    |
| Claude Code        | Orquestación       | Hace que los agentes   | Rol: capa de       | Primario:          |
| LangGraph          | multi-agente con   | autónomos sean         | gobernanza         | equipos que        |
| CrewAI             | puerta humana      | OBSERVABLES y          |                    | operan agentes     |
| AutoGen            |                    | GOBERNABLES            | No tiene "tono"    | IA con efectos     |
| OpenAI Agents SDK  | Auditoría hash-    |                        | — es infraestruc-  |                    |
|                    | chain verificable  | Robin valida en Nature | tura invisible     | Secundario:        |
| Cualquier LLM      |                    | que el patrón multi-   |                    | reguladores        |
| (agentboard_client | Control de costes  | agente + human-in-the- | Autonomía:         | (FDA/SaMD),        |
| .py = ~60 LOC)     | multi-modelo       | loop FUNCIONA.         | FAIL-CLOSED        | auditores          |
|                    |                    | Agent-Board lo         | — sin aprobación,  |                    |
| MCP Gate (@gated)  | Políticas RBAC     | IMPLEMENTA como        | nada se ejecuta    |                    |
|                    | declarativas       | producto               |                    |                    |
|                    |--------------------+                        +--------------------+                    |
|                    | 6. RECURSOS        |                        | 3. CANALES         |                    |
|                    |                    |                        |                    |                    |
|                    | policy.json        |                        | Tablero HTML       |                    |
|                    | models.json        |                        | (5+1 columnas)     |                    |
|                    | config.json        |                        | Broker HTTP        |                    |
|                    | THREAT_MODEL.md    |                        | CLI (hooks)        |                    |
|                    | 15 amenazas        |                        | Webhook (futuro)   |                    |
+--------------------+--------------------+------------------------+--------------------+--------------------+
| 9. COSTES Y RIESGOS                             | 5. KPIs                                            |
|                                                  |                                                    |
| Coste: 0 dependencias (stdlib Python)            | Operaciones con efectos gateadas: 100%             |
| Coste multi-LLM: ~80% ahorro vs todo-Opus       | Latencia de aprobación (<5s human response)        |
| Riesgo #7: auto-aprobación (mitigado: token)     | Auditoría verificable (hash-chain válida)          |
| Riesgo #8: replay (mitigado: binding + TTL)      | WIP dentro de límites (agents, cost_eur)           |
| Riesgo #9: manipulación de política              | Cuotas respetadas (borrados/h, deploys/h)          |
| Riesgo regulatorio: SaMD requiere trazabilidad   | Tasa de incidentes de gobernanza: 0                |
| Robin valida: Nature acepta este nivel de rigor  | Adopción: ¿el operador usa el tablero o lo ignora? |
+--------------------------------------------------+----------------------------------------------------+
```

---

## Resumen de métricas de ablación (patrón Robin)

Robin demostró con datos que cada agente es esencial. Para Agent-Board,
las métricas de ablación propuestas son:

| Agente | Métrica de ablación | Impacto esperado sin el agente |
|--------|---------------------|-------------------------------|
| Analista Genómica | Etiquetas ClinVar erróneas en dataset | "Conflicting" → pathogenic (contaminación) |
| Analista Variantes | Consultas manuales por gen | +20-30 consultas manuales por gen nuevo |
| Diseñador mRNA | ΔG/MFE del mRNA optimizado | Solo GC-max: -0.11 kcal/mol ΔG, -0.05 MFE |
| Motor Biofísico | AUC de clasificación | Cae a 0.5 (aleatorio) — sin señal biofísica |
| Escritor Científico | Horas por manuscrito | +32h de redacción manual por paper |
| Reviewer | Errores en informe final | Predicciones sin cross-validación → riesgo clínico |
| Agent-Board (sistema) | Operaciones no auditadas | Pierde trazabilidad → incompatible con SaMD/FDA |

---

## Acciones derivadas

### Corto plazo (julio-agosto 2026)

1. **Formalizar prompts de rol** — Los archivos `agents/*.md` actuales son
   genéricos (auditor, implementer, verifier, documenter). Crear versiones
   específicas para el perfil `biocomputacion` con el contexto biofísico,
   los recursos concretos (energy.py, model.py) y las métricas de ablación.

2. **Implementar test de ablación** — Para cada agente, crear un test que
   ejecute el pipeline sin ese agente y mida el impacto en la métrica
   correspondiente. Robin lo hizo; nosotros también debemos.

3. **Documentar mapeo Robin → Agent-Board** — Usar este documento como
   base para la sección de "Related Work" del paper de Agent-Board,
   citando Robin como validación del paradigma.

### Medio plazo (septiembre-diciembre 2026)

4. **Agente tipo Finch para exploración** — Para las líneas exploratorias
   (E3, E6, E7), considerar un agente que escriba y ejecute código ad hoc
   en Jupyter, similar a Finch. El Motor Biofísico es determinista (bueno
   para producción), pero la exploración necesita flexibilidad.

5. **LLM Judge (patrón Robin)** — Robin usa Claude 3.7 Sonnet como juez
   para rankear hipótesis. Considerar un agente-juez que rankee variantes
   por confianza usando pairwise comparisons (método Bradley-Terry-Luce),
   como complemento al Reviewer.

6. **Lab-in-the-loop para Paper 3** — El ciclo de Robin (hipótesis →
   experimento → resultados → nueva hipótesis) es exactamente lo que
   necesita Paper 3 (DMS-MaPseq + Reporter). Diseñar el pipeline L1×L2
   experimental como lab-in-the-loop con Agent-Board.

---

*Framework: Agent Canvas Model v2.0 — Jose Antonio Vilar, QMetrika Labs*
*Benchmark: Robin (Nature 655, 496–505, 2026) — Lu, Haber, Kern et al.*
