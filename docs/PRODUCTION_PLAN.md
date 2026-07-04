# agent-board — Plan técnico hacia producción (OSS self-hostable)

> Estado: **propuesta de diseño** · Versión base del repo: **v0.7.0** · Objetivo:
> proyecto **open source serio y self-hostable**, no SaaS empresarial de día 1.

Este documento traduce la lista de mejoras "para llevarlo a producción" en un plan
ejecutable y **opinado**, anclado en lo que el repo ya es: un plugin de Claude Code
con un broker local (Python stdlib, estado en JSON), un gate determinista `@gated`
para servidores MCP, una `policy.json` con motor propio, un hook adapter y un tablero
HTML. Las decisiones concretas viven en los [ADRs](adr/README.md); aquí está la
visión, la lectura del estado actual y la secuencia.

---

## 1. Principio rector: no traicionar el "self-host de 2 minutos"

La lista de mejoras propone, con buen criterio, un stack potente: MCP Gateway,
Postgres + Redis, OPA/Rego, SSE/WebSocket, hash-chain, SSO/OIDC, identidades Ed25519,
OpenTelemetry + Prometheus + Grafana, Docker + Helm. Todo es correcto **para un
producto comercial**. Pero el objetivo aquí es OSS adoptable, y la mayor ventaja
competitiva actual del repo es que **arranca con `python3 broker.py` y cero
dependencias**.

Por eso el principio que ordena todo el plan es:

> **El camino por defecto se mantiene en un solo proceso, sin servicios externos.
> Postgres, Redis, OPA, OIDC, OTel, K8s son _adaptadores opcionales_ detrás de
> interfaces estables, nunca requisitos.**

Esto se traduce en tres niveles de despliegue que deben funcionar todos:

| Nivel | Para quién | Stack |
|---|---|---|
| **Solo** (default) | dev individual, prueba, CI | 1 binario/proceso, SQLite/JSON, sin red externa |
| **Team** | equipo self-host | Docker Compose, Postgres opcional, OIDC opcional |
| **Scale** | quien lo necesite | Helm, Postgres+Redis, OTel, SSO/SIEM |

Si una mejora rompe el nivel **Solo**, se rediseña como adaptador. Esta es la
decisión transversal y está registrada en **[ADR-0001](adr/0001-niveles-de-despliegue.md)**.

---

## 2. Lectura honesta del estado actual (qué hay y qué falta)

### Lo que ya está bien resuelto

- **El invariante de gobernanza es sólido**: "ningún efecto se ejecuta sin pasar por
  la política de la puerta", con la puerta *dentro* de la tool (`@gated`) en vez de
  confiar en el prompt. Esto es lo correcto y lo difícil de copiar.
- **Motor de política propio funcional**: globs por tool, predicados (`==`, `glob`,
  `startswith`, `in`…), `ask_if`/`deny_if`, restricción por rol, `default: ask`.
- **Doble vía de aprobación** con persistencia atómica del estado y fail-closed.
- **Token de operador** en `/api/decide` (cierra la auto-aprobación, amenaza #7).
- **Threat model explícito** con catálogo de bypass y estado por cada vía.
- **Agnóstico de runtime**: contrato HTTP + cliente genérico para LangGraph/CrewAI/etc.

### Las grietas reales para producción (priorizadas)

1. **Aprobación no ligada al payload** (threat #8). Hoy se aprueba un `req_id`; nada
   ata la decisión al *hash exacto* de tool+payload. Replay y race posibles. **Alta.**
2. **Sin contabilidad agregada** (threat #11). El umbral `count>50` se evade
   troceando. No hay rate limit ni cuotas por ventana. **Alta.**
3. **Estado en JSON con un único escritor**. Sirve para Solo, no para varios
   operadores ni alta concurrencia. Falta abstracción de almacenamiento. **Media.**
4. **Tablero por polling** (`GET /api/state` + `GET /api/decision` cada 1.5s). Vale
   para demo; en uso real se quiere push (SSE). **Media.**
5. **Auditoría como log plano** (`gate-audit.log`) sin encadenado ni firma; no es
   *tamper-evident* ni exportable a SIEM. **Media.**
6. **Sin identidad de agente ni de operador real**. El token es un secreto
   compartido; no hay OIDC para humanos ni identidad criptográfica por agente. **Media.**
7. **Interceptación atada a hooks de Claude Code**. El gate `@gated` solo cubre tu
   *propio* servidor MCP en Python; "gobernar lo que no controlas" exige un **proxy
   MCP** real delante de servidores de terceros. **Alta (es el diferenciador).**
8. **Política poco expresiva para casos compuestos** y sin "modo simulación". **Media.**
9. **DX de integración**: existe el cliente genérico, faltan los "2 líneas para
   gobernar X" empaquetados y probados por framework. **Media.**

---

## 3. Arquitectura objetivo

El núcleo no cambia de filosofía; se **descompone en interfaces** para que cada
mejora entre como implementación intercambiable.

```
                 ┌──────────────────────────────────────────────┐
   Agentes  ───▶ │  CAPA DE INTERCEPTACIÓN                       │
 (cualquier      │  · MCP Gateway/Proxy  (gobierna terceros)     │
  runtime)       │  · @gated decorator   (tu propio server)      │
                 │  · SDK adapters       (LangGraph/CrewAI/…)    │
                 │  · CC hooks           (adaptador, no núcleo)  │
                 └───────────────────┬──────────────────────────┘
                                     ▼
                 ┌──────────────────────────────────────────────┐
                 │  POLICY ENGINE (interfaz `Decider`)           │
                 │  · nativo (rápido, cero-dep)  ── default      │
                 │  · adaptador Rego/OPA (opcional)              │
                 │  · simulación / dry-run                       │
                 └───────────────────┬──────────────────────────┘
            allow│              ask  │              │deny
                 ▼                   ▼              ▼
              ejecuta        ┌───────────────┐   bloquea
                             │  BROKER       │
                             │  · Store      │── SQLite(def)/Postgres(opt)
                             │  · Bus (SSE)  │── in-proc(def)/Redis(opt)
                             │  · Audit      │── hash-chain → file/SIEM
                             │  · Identity   │── token(def)/OIDC+Ed25519(opt)
                             └───────┬───────┘
                                     ▼
                          Tablero (SSE, swimlanes, métricas)
                          + Notificaciones (Slack/Teams/Email)
```

Cuatro interfaces estables son el contrato del proyecto:

- **`Interceptor`** — produce un *intento de operación* (tool + payload + contexto).
- **`Decider`** — `decide(tool, payload, ctx) -> allow|deny|ask` (+ motivo).
- **`Store`** — persistencia de tarjetas, decisiones y cuentas agregadas.
- **`AuditSink`** — escribe el registro append-only encadenado.

Mientras esas firmas no cambien, el nivel **Solo** y el nivel **Scale** comparten
código y tests.

---

## 4. Roadmap por fases

Cada fase es **enviable** y mantiene el nivel Solo funcionando. El orden prioriza
(a) cerrar grietas de seguridad que el propio threat model ya marca como pendientes y
(b) el diferenciador (proxy MCP), antes que la infraestructura pesada.

### Fase 0 — Endurecimiento del núcleo (cierra el threat model)
*Objetivo: que el invariante aguante sin añadir dependencias.*

- **Binding de aprobación al payload**: `req_id` de un solo uso + decisión ligada al
  `sha256(tool+payload_canónico)` + TTL corto. Cierra threat #8. → [ADR-0007](adr/0007-binding-de-aprobacion.md)
- **Contabilidad agregada / rate limit** por agente·workflow·tool en ventana
  deslizante; el umbral se evalúa sobre el acumulado. Cierra threat #11. → [ADR-0008](adr/0008-rate-limiting-y-cuotas.md)
- **Auditoría hash-chain** append-only sobre el actual log, con verificador. → [ADR-0006](adr/0006-auditoria-hash-chain.md)
- **Resumen canónico** compuesto por el servidor desde campos validados (threat #12).
- **CI que verifica** que toda tool con efectos está decorada (threat #5).

*Sin Postgres, sin Redis. Todo cabe en el proceso actual.*

### Fase 1 — La capa de interceptación de verdad (el diferenciador)
*Objetivo: "gobierna incluso lo que no controlas".*

- **MCP Gateway/Proxy**: un servidor MCP que se interpone entre el cliente y los
  servidores reales, aplica el `Decider` a cada llamada y reenvía. Gobierna
  servidores de terceros sin modificarlos ni depender de los hooks del cliente. →
  [ADR-0002](adr/0002-capa-de-interceptacion.md)
- **Abstracción `Store`** con dos implementaciones: SQLite (default, sustituye al
  JSON) y memoria. → [ADR-0003](adr/0003-persistencia-y-estado.md)
- **Adaptadores SDK probados** (LangGraph, CrewAI, AutoGen, OpenAI Agents) sobre el
  cliente genérico, con un test de contrato común. → [ADR-0009](adr/0009-dx-adaptadores-sdk.md)

### Fase 2 — Política expresiva y segura de operar
- **Política compuesta**: condiciones AND/OR anidadas, globs por dominio, overrides
  temporales ("aprobar por 1h / siempre en este contexto"). → [ADR-0004](adr/0004-motor-de-politicas.md)
- **Importar Rego (opcional)**: adaptador `Decider` que delega en OPA para quien ya
  tiene políticas Rego; el motor nativo sigue siendo el default. → ADR-0004
- **Modo simulación / dry-run** ("trust ladder"): evaluar una política contra tráfico
  real o histórico **sin aplicarla**, ver qué habría hecho, y promoverla. → ADR-0004

### Fase 3 — UX del tablero (la killer feature)
- Kanban real con **swimlanes** por workflow/equipo de agentes.
- **SSE** para actualizaciones en vivo (sustituye al polling). → [ADR-0005](adr/0005-tiempo-real-sse.md)
- Métricas embebidas en tarjeta (tokens, latencia, riesgo), filtros + búsqueda,
  vista "solo lo que necesita mi aprobación".
- **Modal de aprobación rápido** con razón obligatoria y overrides temporales.
- **Notificaciones** Slack/Teams/Email vía webhook (`approval_routing: webhook`,
  hoy marcado "por implementar" en `config.json`).
- Vista de **topología** (grafo de agentes y dependencias) — al final, es lo menos
  crítico.

### Fase 4 — Identidad y multi-operador
- **OIDC/OAuth** para humanos + tokens de aprobación de corta duración. → [ADR-0010](adr/0010-identidad-y-auth.md)
- **Identidades Ed25519** por agente: cada intento de operación va firmado; el broker
  verifica y audita la identidad real, no un secreto compartido. → ADR-0010

### Fase 5 — Escala y operación (opcional, solo nivel Scale)
- Adaptadores **Postgres** (Store) y **Redis** (bus/colas de aprobación). → ADR-0003
- **OpenTelemetry** + Prometheus + Grafana detrás de un flag. → [ADR-0011](adr/0011-observabilidad.md)
- **Helm chart** además del Docker Compose. → [ADR-0012](adr/0012-empaquetado-y-despliegue.md)
- Exportador de auditoría a **SIEM**.

---

## 5. Mapa: mejora propuesta → dónde se atiende

| Mejora de la lista | Fase | ADR |
|---|---|---|
| MCP Gateway/Proxy + adaptadores SDK | 1 | 0002, 0009 |
| Política YAML + OPA/Rego, expresividad, overrides | 2 | 0004 |
| Postgres + Redis + WebSocket/SSE | 3, 5 | 0003, 0005 |
| Auditoría append-only hash-chain + SIEM | 0, 5 | 0006 |
| Auth: SSO/OIDC + Ed25519 por agente | 4 | 0010 |
| Kanban swimlanes, topología, métricas, filtros | 3 | 0005 |
| Notificaciones Slack/Teams/Email + modal rápido | 3 | 0005 |
| Threat model ampliado, fail-closed, sandboxing | 0 | 0006, 0007, 0008 |
| Rate limiting + cost tracking por agente | 0 | 0008 |
| Trust ladder / modo simulación | 2 | 0004 |
| Override de emergencia con auditoría fuerte | 0, 2 | 0006, 0004 |
| Stack v1 (FastAPI/NestJS, React+Tailwind+dnd) | 3 | 0012 |
| Docker Compose self-host + Helm K8s | 1, 5 | 0012 |
| OpenTelemetry + Prometheus + Grafana | 5 | 0011 |

---

## 6. Lo que NO haría todavía (y por qué)

- **NestJS/reescritura del backend a un framework pesado**: el broker stdlib es un
  activo. Migrar a FastAPI *solo* cuando se necesite async real y validación de
  esquemas (probablemente en Fase 1-2), no antes, y manteniendo el contrato HTTP.
- **Postgres/Redis como requisito**: se quedan en Fase 5 y siempre opcionales.
- **K8s/Helm de día 1**: Compose cubre el 95% del self-host. Helm cuando haya
  usuarios que lo pidan.
- **Vista de topología en grafo**: bonita, baja prioridad; va al final de Fase 3.
- **SIEM**: solo importa para el nivel Scale; el hash-chain exportable (Fase 0) ya da
  el 80% del valor.

El criterio constante: **cerrar las grietas que el propio threat model ya enumera
antes que añadir superficie**. Un tablero bonito sobre una puerta con replay no es
producción; una puerta sin replay y con auditoría verificable, aunque el tablero siga
siendo simple, sí lo es.

---

## 7. Cómo usar este plan

1. Lee los [ADRs](adr/README.md) para el *porqué* de cada decisión de stack.
2. Fase 0 es ejecutable ya sobre el repo actual sin dependencias nuevas.
3. Cada ADR lista alternativas y consecuencias; si tu contexto difiere, cambia el ADR
   (es un registro vivo), no el código a ciegas.
