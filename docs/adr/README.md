# Architecture Decision Records (ADR)

Registro de las decisiones de arquitectura para llevar **agent-board** de plugin/demo
a OSS self-hostable. Cada ADR captura *contexto*, *decisión*, *consecuencias* y
*alternativas descartadas*. Son documentos vivos: si el contexto cambia, se añade un
ADR que supersede al anterior (no se reescribe la historia).

Convención: [MADR](https://adr.github.io/madr/) ligero. Estados posibles:
`propuesto` · `aceptado` · `superseded por NNNN` · `descartado`.

## Índice

| # | Título | Estado | Decide |
|---|---|---|---|
| [0001](0001-niveles-de-despliegue.md) | Niveles de despliegue (Solo/Team/Scale) | aceptado | Cero-dep por defecto; infra pesada opcional |
| [0002](0002-capa-de-interceptacion.md) | Capa de interceptación: proxy MCP + adaptadores | aceptado | Proxy MCP como núcleo; hooks/SDK como adaptadores |
| [0003](0003-persistencia-y-estado.md) | Persistencia y estado | aceptado | SQLite por defecto, Postgres opcional vía `Store` |
| [0004](0004-motor-de-politicas.md) | Motor de políticas + Rego + simulación | aceptado | Motor nativo default, Rego opcional, dry-run |
| [0005](0005-tiempo-real-sse.md) | Tiempo real en el tablero | aceptado | SSE sobre WebSocket |
| [0006](0006-auditoria-hash-chain.md) | Auditoría append-only con hash-chain | **implementado** (v0.10.0) | Log encadenado verificable, export SIEM opcional |
| [0007](0007-binding-de-aprobacion.md) | Binding de aprobación al payload | **implementado** (v0.8.0) | Decisión ligada a hash(tool+payload), 1 uso, TTL |
| [0008](0008-rate-limiting-y-cuotas.md) | Rate limiting y cuotas agregadas | **implementado** (v0.9.0) | Contabilidad por ventana contra troceo |
| [0009](0009-dx-adaptadores-sdk.md) | DX: adaptadores SDK y "2 líneas" | aceptado | Cliente genérico + adaptadores con test de contrato |
| [0010](0010-identidad-y-auth.md) | Identidad y auth (humanos y agentes) | propuesto | OIDC para humanos, Ed25519 por agente |
| [0011](0011-observabilidad.md) | Observabilidad | propuesto | OTel opcional detrás de flag |
| [0012](0012-empaquetado-y-despliegue.md) | Empaquetado y despliegue | aceptado | Compose primero, Helm en Scale |

## Cómo leerlos

- Empieza por [0001](0001-niveles-de-despliegue.md): condiciona a todos los demás.
- [0002](0002-capa-de-interceptacion.md) es el diferenciador del producto.
- [0007](0007-binding-de-aprobacion.md) y [0008](0008-rate-limiting-y-cuotas.md)
  cierran amenazas que el [THREAT_MODEL](../../THREAT_MODEL.md) marca como pendientes.

Para el plan que los ordena en el tiempo, ver [PRODUCTION_PLAN.md](../PRODUCTION_PLAN.md).
