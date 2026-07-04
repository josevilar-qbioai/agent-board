# 0008 — Rate limiting y cuotas agregadas

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0003](0003-persistencia-y-estado.md), [0004](0004-motor-de-politicas.md), [THREAT_MODEL](../../THREAT_MODEL.md) #11

## Contexto

La política puede expresar umbrales por llamada (p. ej. `delete_* deny_if count>50`),
pero el **threat model #11** señala la evasión obvia: **trocear** — 60 borrados de 1 en
1 en lugar de 1 de 60. Cada llamada pasa el umbral individual; el daño agregado no se
contabiliza. Tampoco hay límite de frecuencia ni *cost tracking* por agente/workflow,
que la lista pide explícitamente.

## Decisión

Añadir **contabilidad agregada en ventana deslizante** como entrada de primera clase
para el `Decider` y como mecanismo de protección independiente:

1. **Contadores por dimensión**: el broker mantiene acumulados por `(agente |
   workflow | tool | recurso)` en ventanas configurables (p. ej. 1m / 1h / 24h),
   persistidos en el `Store` (ADR-0003).
2. **Cuotas en política**: la política puede referirse al acumulado, no solo al valor
   de la llamada. Ej.: "denegar si `sum(deleted, 1h) > 100`" o "pedir aprobación a
   partir del N-ésimo `deploy` en la ventana".
3. **Rate limiting** por agente/workflow: techo de operaciones con efectos por unidad
   de tiempo; al superarlo → `ask` o `deny` según config (fail-closed por defecto).
4. **Cost tracking**: se contabilizan tokens (ya estimados en las tarjetas: `tokens +=
   600` por `PreToolUse`), latencia y coste estimado por agente/workflow, visibles en
   el tablero (ADR-0005) y disponibles para cuotas de presupuesto.

Todo se evalúa **antes** del efecto, en el mismo punto que la política (proxy/`@gated`).
La ventana es atómica respecto a la decisión para evitar carreras de conteo.

## Consecuencias

**Positivas**
- Cierra la evasión por troceo (#11): el límite real es el agregado.
- *Cost tracking* por agente da visibilidad y control de presupuesto, no solo seguridad.
- Reutiliza el `Store` con consultas; no necesita infraestructura nueva en Solo.

**Negativas / coste**
- Estado adicional con escrituras frecuentes; en Scale conviene mover contadores
  calientes a Redis (opcional) para no presionar el `Store` primario.
- Definir las dimensiones y ventanas correctas requiere iteración; el **dry-run**
  (ADR-0004) ayuda a calibrar umbrales sin bloquear de golpe.
- Contadores persistentes deben sobrevivir reinicios pero también poder expirar.

## Alternativas descartadas

- **Solo umbrales por llamada**: evadibles por troceo (#11).
- **Rate limit en un proxy genérico externo (nginx/envoy)**: no entiende la semántica
  de tool/recurso ni alimenta la política; pierde el cost tracking por agente.
