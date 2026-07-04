# 0002 — Capa de interceptación: proxy MCP + adaptadores

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0001](0001-niveles-de-despliegue.md), [0004](0004-motor-de-politicas.md), [0009](0009-dx-adaptadores-sdk.md), [THREAT_MODEL](../../THREAT_MODEL.md) #1, #2

## Contexto

Hoy existen dos formas de que una operación llegue a la puerta:

1. El **hook `PreToolUse`** de Claude Code (`hooks/hook.py`), que consulta
   `policy.json` y puede gobernar incluso tools `mcp__srv__op` de terceros — pero solo
   en clientes que soportan hooks (Claude Code).
2. El **decorador `@gated`** (`mcp/agentboard_gate.py`), que mete la puerta *dentro*
   de tu propio servidor MCP en Python — pero solo cubre el servidor que tú escribes.

El threat model (vías #1 y #2) deja claro el hueco: un servidor MCP de terceros que tú
**no controlas** y un cliente **sin hooks** dejan operaciones con efectos fuera de la
puerta. El verdadero diferenciador del producto — *"gobierna incluso lo que no
controlas"* — exige interceptar a nivel de **protocolo MCP**, no de cliente ni de
servidor concreto.

## Decisión

Elevar la interceptación a una **interfaz `Interceptor`** con varias implementaciones,
siendo la nueva y principal un **proxy/gateway MCP**:

- **MCP Gateway/Proxy** (núcleo nuevo): un servidor MCP que el cliente configura como
  si fuera el servidor real. Reenvía `initialize`/`tools/list`/`tools/call` a los
  servidores upstream reales, pero antes de reenviar un `tools/call` evalúa el
  `Decider` (ADR-0004) y aplica allow/deny/ask. Gobierna **cualquier** servidor MCP
  upstream sin modificarlo y **cualquier** cliente que hable MCP, sin depender de
  hooks. Multiplexa N servidores upstream con prefijos de nombre estables.
- **`@gated`** (se mantiene): la puerta in-process sigue siendo la opción más fuerte
  cuando controlas el servidor (no hay forma de saltársela por debajo del proxy).
- **Hooks de Claude Code** (se mantienen como adaptador): siguen siendo útiles para
  gobernar las tools nativas del cliente (`Write`, `Edit`, `Bash`) que no pasan por
  ningún servidor MCP.
- **Adaptadores SDK** (ADR-0009): para runtimes que no usan MCP, envuelven la
  ejecución de tools y llaman al broker.

Las cuatro comparten el mismo `Decider` y el mismo broker. La política es única.

## Consecuencias

**Positivas**
- Cierra las vías #1/#2 del threat model para todo el tráfico que pase por MCP, con
  independencia del cliente.
- Un único punto de evaluación de política para servidores de terceros.
- El proxy es además el sitio natural para métricas por tool (tokens/latencia) y para
  el rate limiting agregado (ADR-0008).

**Negativas / coste**
- El proxy añade un salto de red local y debe ser transparente (manejar streaming,
  errores y `tools/list` dinámico correctamente).
- Riesgo de convertirse en cuello de botella; debe ser async y ligero.
- No cubre efectos **fuera** de MCP (shell directo): eso sigue siendo responsabilidad
  del integrador (gatear `Bash`, restringir exec), tal como ya documenta el threat model.

## Alternativas descartadas

- **Solo hooks**: atado a Claude Code; no gobierna otros clientes.
- **Solo `@gated`**: no gobierna servidores de terceros.
- **Parchear cada servidor upstream**: no escala y contradice "lo que no controlas".
