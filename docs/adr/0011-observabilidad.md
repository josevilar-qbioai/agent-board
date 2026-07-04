# 0011 — Observabilidad

- Estado: **propuesto**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0001](0001-niveles-de-despliegue.md), [0008](0008-rate-limiting-y-cuotas.md)

## Contexto

El tablero ya es una forma de observabilidad de cara al humano (tarjetas, estados,
tokens estimados). Pero no hay telemetría exportable para operar el propio broker/proxy
ni para integrarse con el *stack* de monitorización de un equipo. La lista pide
**OpenTelemetry + Prometheus + Grafana**. Aplicando [ADR-0001](0001-niveles-de-despliegue.md),
no puede ser un requisito del nivel Solo.

## Decisión

Adoptar **OpenTelemetry como interfaz de telemetría, detrás de un flag, opcional**:

- **Solo** (default): sin telemetría externa. El tablero y los logs bastan. Cero
  dependencias.
- **Team/Scale**: activando `AGENT_BOARD_OTEL=1` (o config equivalente), el broker/proxy
  emite **trazas, métricas y logs** vía OTel a cualquier *collector*:
  - **Métricas** clave: decisiones por resultado (allow/deny/ask), latencia de la
    puerta, tiempo de espera de aprobación humana, profundidad de la cola de `needs`,
    tasa de fail-closed, contadores de cuota (ADR-0008), tokens/coste por
    agente·workflow.
  - **Trazas**: una operación = un span (intercepción → decisión → [espera] →
    ejecución), correlacionable con el `req_id`/`payload_hash`.
- Exportadores estándar (OTLP) → Prometheus/Grafana/Tempo o el backend que el equipo
  use. No acoplamos a un vendor.

La telemetría y la **auditoría** (ADR-0006) son cosas distintas: auditoría = registro
*tamper-evident* de gobernanza (fuente de verdad legal); observabilidad = señales
operativas (efímeras, agregables). No se mezclan.

## Consecuencias

**Positivas**
- Operar el broker/proxy en serio (alertas si el broker no responde — el threat model
  #15 lo pide, latencias, saturación de la cola de aprobación).
- OTel es estándar y neutral; se integra con lo que el equipo ya tenga.
- Las mismas métricas de coste alimentan la vista del tablero.

**Negativas / coste**
- Instrumentar añade dependencias (SDK OTel) — por eso opcional y aislada por flag.
- Riesgo de fuga de datos sensibles en atributos de span: hay que **redactar** payloads
  (solo `payload_hash`, nunca contenido) en la telemetría.

## Alternativas descartadas

- **Métricas Prometheus nativas sin OTel**: más simple pero acopla a un formato; OTel
  cubre métricas+trazas+logs con un solo SDK.
- **Telemetría siempre activa**: rompe el nivel Solo y arrastra dependencias.
- **Reusar la auditoría como observabilidad**: confunde dos responsabilidades con
  requisitos opuestos (inmutable vs. agregable/efímero).
