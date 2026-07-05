# Q · Agent Board

<sub>QMetrika Labs · paquete/plugin: `agent-board`</sub>

**Un plano de supervisión en tiempo real para agentes autónomos.** Un **tablero
Kanban en vivo** donde cada agente es una tarjeta que avanza por columnas, con una
**puerta de aprobación humana** sobre cualquier operación con efectos secundarios.
Agentes de solo-lectura por defecto y **auditoría verificable** de cada llamada a tool.

No es un agente: es la **capa que observa y gobierna a los agentes** mientras
trabajan. Empezó como plugin de [Claude Code](https://www.claude.com/product/claude-code)
pero el núcleo (tablero + broker + puerta) es **agnóstico de runtime** y de dominio:
lo pilotas desde LangGraph, CrewAI, AutoGen, OpenAI Agents SDK o tu propio bucle, y lo
adaptas a tu proyecto editando `config.json`.

[![CI](https://github.com/josevilar-qbioai/agent-board/actions/workflows/validate.yml/badge.svg)](https://github.com/josevilar-qbioai/agent-board/actions/workflows/validate.yml)
![Claude Code plugin](https://img.shields.io/badge/claude--code-plugin-blue)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![sin dependencias](https://img.shields.io/badge/deps-0%20(stdlib)-brightgreen)
![license: MIT](https://img.shields.io/badge/license-MIT-green)

**▶ Demos en vivo (GitHub Pages):** https://josevilar-qbioai.github.io/agent-board/ ·
tablero, "cómo funciona" y el Tablero de Capital, sin instalar nada.

## 🚀 Quickstart (2 minutos)

Sin dependencias — solo Python 3.8+.

```bash
# 1) INSTALA (local, sin publicar)
claude --plugin-dir /ruta/a/agent-board      # o ver INSTALL.md para GitHub/marketplace

# 2) CONFIGURA — elige una:
#    a) guiado:      en Claude Code ejecuta  /setup   (genera config.json por ti)
#    b) plantilla:   copia examples/profiles/{dev,legal,finanzas,soporte-it}.json
#                    dentro de "profiles" en config.json
python3 scripts/validate_config.py           # comprueba que todo está bien

# 3) ARRANCA
python3 hooks/broker.py                       # imprime un token y la URL del tablero
```

Abre la URL que imprime el broker (o `board/agent-board.html` para el demo simulado).
Cambia de proyecto/departamento con `?profile=<nombre>` y `?unit=<unidad>`; el botón
**▤ Carriles** agrupa por departamento. Guía completa en [INSTALL.md](INSTALL.md).

## Qué resuelve

Los workflows dinámicos lanzan decenas o cientos de subagentes en paralelo. Es
potente, pero **opaco y arriesgado** si tocan cosas con efectos: no ves qué hace cada
uno, ni quién está a punto de borrar, desplegar o escribir. Mucha gente monta
servidores MCP; muy pocos tienen detrás **observabilidad en vivo, una puerta de
aprobación seria y auditoría a prueba de manipulación**. Ese es el hueco que cubre
agent-board, con dos capas sobre tus agentes:

- **Supervisión / observabilidad** — cada agente es una tarjeta que avanza por
  columnas (Queued → Working → Needs Input → Review → Done; más una vía **⚡ Sin
  presupuesto** para agentes fundacionales frenados por el límite de coste). Ves en tiempo real qué
  agente hace qué, su modelo, tokens y estado.
- **Gobernanza** — las operaciones con efectos no se ejecutan solas: caen en
  *Needs Input* esperando tu aprobación. El descubrimiento/lectura corre con un agente
  que físicamente no puede escribir. La decisión es **código** (política determinista),
  no criterio del modelo.

## Qué es / qué no es

|  | |
|---|---|
| ✅ **Es** | un tablero de supervisión en vivo de agentes; una puerta humana sobre acciones con efectos; una política determinista allow/ask/deny; una auditoría encadenada verificable; agnóstico de LLM y de dominio |
| ❌ **No es** | un agente ni un framework de agentes; un orquestador (no decide *qué* hacen los agentes, sino qué se les permite ejecutar); un reemplazo de tu RBAC (lo complementa: la puerta decide, tu auth dice *quién* es el principal) |

## Estado del endurecimiento (Fase 0 completada)

El núcleo está endurecido para producción sin añadir dependencias externas. Cerrado
en el [THREAT_MODEL](THREAT_MODEL.md): auto-aprobación (#7), replay/race de aprobación
(#8, *binding* al hash del payload), troceo de umbrales (#11, cuotas agregadas),
resumen engañoso al operador (#12) y tool sin decorar (#5, lint en CI). La auditoría
es una **cadena hash-encadenada** verificable (`python3 mcp/audit.py verify`). El plan
completo hacia producción y las decisiones de diseño están en
[docs/PRODUCTION_PLAN.md](docs/PRODUCTION_PLAN.md) y [docs/adr/](docs/adr/).

## Estructura

```
agent-board/
├── .claude-plugin/{plugin.json, marketplace.json}
├── skills/board-workflow/SKILL.md   # el patrón: cuándo y cómo + gobernanza
├── agents/{auditor,implementer,verifier,documenter}.md
├── hooks/{hooks.json, hook.py, broker.py}  # ciclo de vida + puerta + cuotas
├── commands/{board,setup}.md         # /board · /setup (asistente de config)
├── scripts/validate_config.py        # valida config/policy/models (config fácil)
├── examples/profiles/                # plantillas: dev, legal, finanzas, soporte-it
├── board/agent-board.html            # tablero de supervisión (en vivo o demo)
├── client/agentboard_client.py       # cliente genérico (cualquier LLM)
├── mcp/agentboard_gate.py            # puerta DETERMINISTA dentro de tools MCP
├── mcp/policy.json                   # reglas allow/deny/ask + cuotas por dominio
├── mcp/canonical.py                  # hash canónico de operación (binding, ADR-0007)
├── mcp/quota.py                      # contabilidad agregada / rate limit (ADR-0008)
├── mcp/cost.py + mcp/models.json     # coste € por modelo (local vs fundacional)
├── mcp/audit.py                      # auditoría hash-chain verificable (ADR-0006)
├── mcp/example_tools.py              # ejemplo de tools con @gated
├── mcp.example.json                  # plantilla .mcp.json (un servidor = un dominio)
├── tests/                            # binding, cuotas, auditoría, lint de decoración
├── docs/PRODUCTION_PLAN.md + docs/adr/  # plan a producción y decisiones (ADR)
├── THREAT_MODEL.md                   # gobernanza: vías de bypass y mitigaciones
├── examples/multi_model_orchestrator.py
├── settings.json                     # lectura preaprobada, escrituras "ask"
├── config.json                       # adaptación por proyecto
└── examples/                         # adaptaciones por dominio
```

## Instalación

```bash
/plugin marketplace add https://github.com/josevilar-qbioai/agent-board
/plugin install agent-board@agent-board
/reload-plugins
```

Desarrollo local sin instalar: `claude --plugin-dir /ruta/a/agent-board`.

## Uso

```text
ultracode audita las dependencias con CVEs y propón cuáles actualizar
/board-workflow migra el módulo de reporting a async, un agente por fichero
/board          # abre el tablero
```

Lo de lectura corre solo (auto mode); cualquier operación con efectos cae en
*Needs Input* esperando tu aprobación.

## Reproducible en todos tus proyectos

1. **Por usuario** — instálalo una vez; vive en `~/.claude/plugins/` y te sigue a
   cualquier proyecto.
2. **Por proyecto** — versiona `.claude/settings.json` en cada repo para auto-añadir
   el marketplace:
   ```json
   {
     "extraKnownMarketplaces": { "agent-board": { "source": { "type": "git", "url": "https://github.com/josevilar-qbioai/agent-board" } } },
     "enabledPlugins": ["agent-board@agent-board"]
   }
   ```
3. **Por equipo/comunidad** — publica el repo en GitHub y distribuye ese settings.json.

## Adaptar a tu proyecto

Todo lo específico vive en dos sitios, no en el código:

- **`config.json`** — `wip_limit` (WIP **multidimensional medido en coste**:
  `{ agents, cost_eur, foundational_cost_eur }` — un agente entra en *Working* solo si
  hay hueco de agentes **y** de presupuesto € total **y** de € en modelos fundacionales;
  el más restrictivo manda), qué cuenta como operación con efectos (`gated_tools`), y el
  `approval_routing`. El coste por modelo vive en **`mcp/models.json`** (€/1M tokens y
  clase local/fundacional): un token local es ~gratis, uno fundacional es caro.
- **`settings.json`** — la lista `ask` debe incluir tus tools con efectos para que
  pasen por la puerta humana; la lista `allow` solo lectura segura.

Para tu MCP propio, crea **`.mcp.json`** en la raíz del plugin y añade sus tools de
escritura a `gated_tools`/`ask`. La autorización de fondo (RBAC) vive en tu servidor
MCP, no en el prompt.

**Perfiles de proyecto y unidades/departamentos.** El tablero se adapta a los agentes
concretos de tu proyecto mediante *perfiles*, declarados en **`config.json`**
(`profiles`). Cada especialista define su `id`, `label`, `color`, **rol de flujo**
(`read` análisis · `effect` con efectos → puerta + review · `verify` verificador ·
`write` escribe), su `unit` (departamento) y un `model` por defecto. El proyecto de
ejemplo es **Claude Science** (Analista de Genómica del Cáncer, Analista de Variantes,
Diseñador de mRNA, Motor Biofísico, Escritor Científico, Reviewer), repartido en
unidades Genómica / Terapéutica / Publicación / QA.

Distribución por departamentos: **un proyecto = un `profile`; un departamento = una
`unit`**. En el tablero HTML seleccionas con `?profile=<nombre>` y, para la vista de un
departamento, `?profile=claude-science&unit=Terapéutica` (solo ve sus agentes). El
botón **"▤ Carriles"** agrupa el Kanban en *swimlanes* por unidad (todos los
departamentos a la vez, cada uno su fila), para ver y gobernar el enjambre desde la
estructura de la organización. En
**modo en vivo**, tu orquestador pasa el `kind` (id del especialista) en
`board.start(kind="motor-biofisico", model=...)` y el perfil aporta color/etiqueta/unit.
Para otro caso de uso hay **plantillas listas** en `examples/profiles/` (`dev`, `legal`,
`finanzas`, `soporte-it`): copia la más cercana dentro de `profiles`. O deja que el
asistente lo genere por ti con **`/setup`** en Claude Code. Valida en cualquier momento
con `python3 scripts/validate_config.py` (mensajes claros si algo falta).

**Fuente única (sin duplicar).** Cuando el tablero se sirve desde el broker, carga los
perfiles de `GET /api/config` (que el broker lee de `config.json`), así que `config.json`
es la única fuente de verdad. Los perfiles embebidos en el HTML son solo *fallback*
offline (al abrir por `file://`).

Mira `examples/` para ver cómo estructurar una adaptación por dominio.

## Usar con otros LLM (agnóstico de runtime)

El tablero y el broker no saben nada de Claude. Hablan por una API HTTP
(`/api/event`, `/api/request`, `/api/decision`, `/api/decide`). Los hooks de
Claude Code son **solo un adaptador**. Para pilotar el tablero desde cualquier
otro runtime (OpenAI Agents SDK, LangGraph, CrewAI, AutoGen, tu propio bucle)
tienes dos caminos:

**a) El cliente genérico** (`client/agentboard_client.py`). Mapea tres cosas de tu
framework: el ciclo de vida (`start`/`step`/`stop`), la operación con efectos
(`gate`, que BLOQUEA hasta que apruebas en el tablero) y el control de coste
(`account_llm`, presupuesto en € por modelo/clase):

```python
from agentboard_client import AgentBoard
board = AgentBoard()                                   # broker en :8787
sid = board.start("Refactor del cliente", model="gpt-4o", kind="implementer")
board.step(sid, "analizando código")
if board.gate(sid, "Write", {"path": "client.py"}):    # espera Aprobar/Denegar
    do_write()
# antes de una llamada LLM cara, comprueba el presupuesto de coste (una línea):
if not board.account_llm("opus", 18000, sid):          # False -> presupuesto agotado
    return
board.stop(sid)
```

`account_llm(model, tokens)` traduce (modelo, tokens) → € con `mcp/models.json`,
aplica las cuotas de coste y devuelve `True` si puedes gastar (queda contabilizado).
Si la cuota es `ask`, abre tarjeta en el tablero y espera tu aprobación. Un token
local es ~gratis; uno fundacional pesa contra el presupuesto.

Adaptadores típicos (≈20 líneas cada uno):
- **OpenAI Agents SDK / Assistants** — envuelve la ejecución de cada tool; antes
  de una con efectos, `board.gate(...)`.
- **LangGraph** — `start/step/stop` en los callbacks; para gatear, un nodo
  human-in-the-loop (`interrupt`) que llama a `board.gate`.
- **CrewAI / AutoGen** — igual: envuelve tools, emite inicio/fin por agente.

**b) La puerta en la capa de tools/MCP** (lo más universal). Si todas las
operaciones con efectos pasan por tu servidor MCP con RBAC, mete ahí la llamada a
`board.gate(...)`. Entonces da igual qué LLM las invoque: el control vive en la
tool, no en el runtime. Es exactamente tu arquitectura MCP original.

## Opción B: puerta determinista dentro del servidor MCP (Python)

La forma más universal y con control más estricto: la puerta vive **dentro** de
la tool, no en el runtime del LLM. El efecto no puede ocurrir sin pasar la puerta,
y la decisión es **código** (política), no criterio del modelo.

Flujo por cada tool con efectos:

```
RBAC (tu capa)  ->  política determinista  ->  [solo 'ask'] tablero  ->  auditoría
```

Aplicarlo a tu servidor MCP es un decorador (`mcp/agentboard_gate.py`):

```python
from agentboard_gate import gated, GateDenied

@gated("disable_account")
def disable_account(upn: str):
    ...  # SOLO se ejecuta si la política permite o el operador aprueba
```

La política (`mcp/policy.json`) decide de forma determinista por tool, con
condiciones sobre el payload y restricción por rol:

```json
{
  "default": "ask",
  "rules": [
    { "tool": "get_*",           "decision": "allow" },
    { "tool": "disable_account", "decision": "ask",  "roles": ["admin"] },
    { "tool": "assign_license",  "decision": "allow", "ask_if": [{ "field": "count", "op": ">", "value": 10 }] },
    { "tool": "delete_*",        "decision": "ask",  "deny_if": [{ "field": "count", "op": ">", "value": 50 }] },
    { "tool": "purge_*",         "decision": "deny" }
  ]
}
```

- `allow` → ejecuta sin preguntar.
- `deny` → lanza `GateDenied`, nunca ejecuta.
- `ask` → tarjeta en el tablero, BLOQUEA hasta Aprobar/Denegar.
- `ask_if` / `deny_if` → escalan o bloquean según el payload (p. ej. tamaño del lote).
- `roles` → restringe la tool a ciertos roles (reutiliza tu `MCP_USER_ROLE`).

**Fail-closed**: si una decisión es `ask` y el broker no responde (o expira el
timeout), se **deniega** por defecto. En un servidor es lo seguro; cámbialo con
`AGENT_BOARD_FAIL_OPEN=1` solo si sabes lo que haces.

**Auditoría (tamper-evident)**: cada decisión (por regla o humana) se registra en
`mcp/gate-audit.log` como una **cadena con hash encadenado** (ADR-0006): cada entrada
liga con la anterior, así que alterar o borrar cualquier línea rompe la cadena. Incluye
tool, rol, decisión, origen (`policy` / `human` / `quota` / `fail-closed`) y el
`payload_hash` de la operación. Verifica la integridad con `python3 mcp/audit.py verify`.

**Cuotas agregadas (ADR-0008)**: además de la decisión por llamada, la política puede
declarar `quotas` por (agente/workflow/tool) con `limit` y `window`. El límite real es
el **acumulado** en la ventana, no el valor de una llamada — cierra el troceo (60
borrados de 1 en 1 para esquivar `count>50`). `on_exceed: deny | ask`.

**Cuotas de coste (€)**: una quota puede medirse en **euros** en vez de en conteo, con
`amount_field: "cost_eur"` y `match_class: "foundational"` — p. ej. "máx. 5 €/hora en
modelos fundacionales". El coste sale de `mcp/models.json` (precio €/1M tokens y clase
por modelo); el caller pasa `ctx.model` y `ctx.tokens` a `/api/account` y el broker
calcula el coste. Así un token local (~gratis) no cuenta como uno de Opus/GPT-4o.

Ventaja frente al adaptador de runtime (Opción A): da igual qué LLM llame la tool
—Claude, GPT, Gemini, tu bucle— el control es el mismo porque vive en la tool.

> Antes de producción, lee [THREAT_MODEL.md](THREAT_MODEL.md): enumera por dónde
> podría colarse una acción sin pasar por la puerta y cómo cerrarlo. La auto-aprobación
> (#7), el replay de aprobación (#8) y el troceo de umbrales (#11) ya están cerrados en
> el núcleo; el documento marca lo que sigue siendo responsabilidad del integrador.

## Varios MCP por dominio (genérico)

Puedes ampliar funcionalidad añadiendo servidores MCP, y conviene mantener
**un servidor = un dominio** (notify, data, deploy, lo que necesites). La
convención de nombres de tool es `mcp__<servidor>__<tool>`, así que la **misma**
`policy.json` razona por dominio con globs, y gobierna tanto tu servidor propio
como los MCP de terceros que no puedes modificar:

```json
{ "tool": "mcp__*__purge_*",  "decision": "deny" },
{ "tool": "mcp__*__delete_*", "decision": "ask", "deny_if": [{ "field": "count", "op": ">", "value": 50 }] },
{ "tool": "mcp__notify__*",   "decision": "allow" },
{ "tool": "mcp__data__*",     "decision": "ask" },
{ "tool": "mcp__deploy__*",   "decision": "ask" }
```

Dos puntos de aplicación, una sola política:

- **Tu servidor propio (Python)** → la puerta va *dentro* con `@gated` (Opción B,
  determinista). Ver `mcp/example_tools.py`.
- **MCP de terceros (no lo controlas)** → la puerta va en el hook `PreToolUse`,
  que ve el nombre `mcp__servidor__tool` y aplica la misma `policy.json`. Si
  ninguna regla casa, no interfiere (deja el flujo normal de Claude Code).

Añadir un MCP:

1. Copia `mcp.example.json` a `.mcp.json` (raíz del plugin) y deja solo tus
   servidores. Tres modos: comando local (`${CLAUDE_PLUGIN_ROOT}/...`), HTTP, o un
   conector que el usuario ya tenga. No metas secretos en el fichero; usa env.
2. Por cada dominio/tool con efectos, una regla en `policy.json`
   (`allow`/`ask`/`deny`, con `roles`, `ask_if`, `deny_if`, `startswith`, `glob`).
3. Higiene: un servidor por dominio (credenciales de mínimo privilegio, política
   legible, fallo y despliegue independientes). Lo transversal (auth, logging, el
   propio gate) es una librería compartida, no un servidor.

## Multi-proveedor: Claude, Gemini, OpenAI y modelos locales

Pilota el tablero con **cualquier LLM**. La capa `client/providers.py` expone una sola
función `generate(model, prompt)` que despacha al proveedor según el nombre del modelo
y devuelve texto + **uso real de tokens**:

- **Claude** → Anthropic (`ANTHROPIC_API_KEY`)
- **GPT / o\*** → OpenAI (`OPENAI_API_KEY`)
- **Gemini** → Google (`GOOGLE_API_KEY`)
- **Locales** (Llama/Mistral/Qwen…) → OpenAI-compatible o Ollama (`AGENT_BOARD_LOCAL_URL`)

Sin API keys funciona en **modo simulado** (con tokens estimados), así que ves agentes
de todos los proveedores en el tablero desde el primer minuto; en cuanto pones una key
o levantas un modelo local, ese proveedor pasa a llamadas reales. Cada proveedor es
independiente (puedes tener Claude real y el resto simulado).

`examples/multi_model_orchestrator.py` lo junta todo:

- **Un proveedor por rol** — `ROLE_MODELS`: explorer→gemini-2.0-flash (Google),
  auditor→mistral-local (LOCAL), implementer→gpt-4o (OpenAI), verifier→opus (Anthropic),
  documenter→sonnet. El tablero colorea cada proveedor y muestra sus tokens y coste €.
- **Tokens y coste reales por agente** — `board.report_usage(sid, model, tin, tout)`
  refleja el uso en la tarjeta; `board.account_llm(model, tokens)` aplica el presupuesto
  (local ~gratis, fundacional pesa).
- **Verificación cruzada** — el verifier usa un proveedor **distinto** al autor; un juez
  sin interés en el texto que juzga mata el sesgo auto-preferencial.
- Todo pilotado por el cliente genérico; las escrituras pasan por la puerta humana.

El orquestador vive fuera de Claude Code, en Python plano — ese es el cambio que lo hace
multi-LLM. El tablero y el broker no saben de qué proveedor viene cada agente.

## Aprobación de doble vía (el botón decide de verdad)

Por defecto (`approval_routing: "board"`) el tablero **es** la superficie de
aprobación: pulsar Aprobar/Denegar desbloquea o bloquea la operación real.

El bucle, coordinado por un broker local:

```
agente quiere Write/Edit/Bash
        │  (hook PreToolUse)
        ▼
   hook.py ──POST /api/request──▶ broker ──▶ tarjeta en "Needs Input"
        │                                         │
        │ (poll cada 1.5s, hasta gate_timeout)    │  operador pulsa Aprobar/Denegar
        ◀──GET /api/decision───── broker ◀──POST /api/decide── tablero
        │
        ▼
 devuelve a Claude Code:
   { "hookSpecificOutput": { "hookEventName": "PreToolUse",
       "permissionDecision": "allow" | "deny", "permissionDecisionReason": "..." } }
```

Arranque:

```bash
python3 hooks/broker.py     # sirve tablero + API; imprime un TOKEN de operador y la URL
# abre la URL que imprime, que incluye el token en el fragmento:
#   http://127.0.0.1:8787/agent-board.html?feed=/api/state#token=<token>
```

Aprobar/Denegar exige ese **token de operador** (cabecera `X-Operator-Token`). El
canal del agente (`/api/request`, `/api/decision`) NO lo requiere: así un agente con
shell no puede auto-aprobarse (amenaza #7). Fíjalo con `AGENT_BOARD_OP_TOKEN` o deja
que el broker lo genere.

Las tools de lectura nunca tocan la puerta. Solo las de `gated_tools`
(= `AGENT_BOARD_GATED`, por defecto `Write,Edit,Bash`) abren tarjeta y esperan.

Otros modos del tablero:
- `agent-board.html` (sin `?feed`) → demo simulada.
- `agent-board.html?feed=board-state.json` → observabilidad offline (solo lectura;
  los hooks escriben ese fichero si el broker no está levantado).

## Fallback seguro y límites

- **Si el broker está caído o se agota `gate_timeout_seconds`, el hook NO decide**
  y aparece el prompt nativo de Claude Code. Nunca se aprueba algo solo porque el
  tablero no respondió.
- **Compatibilidad de versiones:** el honrado `permissionDecision` allow/deny del
  hook ha tenido regresiones puntuales en algunas versiones de Claude Code (que el
  prompt nativo siguiera apareciendo). Pruébalo en tu versión; como defensa en
  profundidad, las operaciones con efectos siguen en la lista `ask` de
  `settings.json`, así que el peor caso es un prompt extra, nunca una ejecución sin
  control.
- Los nombres de campo del payload de los hooks (`session_id`, `tool_name`,
  `tool_input`) pueden variar entre versiones; si algo no encaja, imprime el stdin
  en `hooks/hook.py` y ajusta los `.get()`.
- El broker **persiste** su estado en `board/broker-state.json` (volcado atómico, flush inmediato en cada decisión): sobrevive a reinicios. `POST /api/reset` lo vacía.

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md). La regla: mantenerlo genérico y
configurable. Lo específico de un proyecto va en `examples/`.

## Licencia

MIT — ver [LICENSE](LICENSE).
