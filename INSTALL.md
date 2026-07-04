# Instalar agent-board

Plugin de [Claude Code](https://www.claude.com/product/claude-code) para supervisar y
gobernar agentes. **Cero dependencias**: solo Python 3.8+ (todo stdlib). No hay que
instalar nada más.

> Si tu handle de GitHub no es `QMetrika-Labs`, cambia esa cadena en
> `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` y `README.md`
> (búscala y reemplázala). Es lo único específico del repo.

---

## Requisitos

- **Python 3.8+** en el PATH (`python3 --version`).
- Claude Code (para el modo plugin). Para otros runtimes, ver "Sin Claude Code".
- POSIX (macOS/Linux) recomendado. En Windows funciona, pero la auditoría hash-chain
  usa `fcntl` para el lock entre procesos y cae a un modo sin lock (documentado).

---

## Opción A — Local (probarlo ya, sin publicar)

La forma más rápida. Desde el directorio que contiene el plugin:

```bash
claude --plugin-dir /ruta/a/agent-board
```

O añade el marketplace local (el `source: "./"` de `marketplace.json` ya apunta al
propio repo):

```text
/plugin marketplace add /ruta/a/agent-board
/plugin install agent-board@agent-board
/reload-plugins
```

## Opción B — Desde GitHub (para compartir/equipo)

1. Sube este repo a `https://github.com/QMetrika-Labs/agent-board` (o tu handle).
2. En Claude Code:

```text
/plugin marketplace add https://github.com/QMetrika-Labs/agent-board
/plugin install agent-board@agent-board
/reload-plugins
```

3. Para que un repo de trabajo lo auto-cargue, versiona su `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "agent-board": { "source": { "type": "git", "url": "https://github.com/QMetrika-Labs/agent-board" } }
  },
  "enabledPlugins": ["agent-board@agent-board"]
}
```

## Opción C — Paquete `.plugin`

Se distribuye también como `agent-board.plugin` (un zip del plugin). Instálalo/compártelo
con el botón de instalación, o descomprímelo y usa la Opción A sobre la carpeta.

---

## Arrancar la supervisión

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/broker.py"
# imprime un TOKEN de operador y la URL del tablero con el token en el fragmento:
#   http://127.0.0.1:8787/agent-board.html?feed=/api/state#token=<token>
```

Abre esa URL. Los hooks (`SessionStart` / `PreToolUse` / `Stop`) se enganchan solos:
cuando un agente intenta una operación con efectos (`Write`/`Edit`/`Bash` o una tool
gateada), aparece una tarjeta en **Needs Input** y el hook **bloquea** hasta que pulses
Aprobar/Denegar. Lo de solo lectura corre sin molestar.

Comando del plugin: `/board`.

Modos del tablero:
- `agent-board.html` → demo simulado (sin backend).
- `agent-board.html?feed=/api/state` → en vivo (aprobaciones reales).
- `agent-board.html?feed=board-state.json` → observabilidad offline (solo lectura).

Ver también `board/capital-board.html` (Tablero de Capital, vista de acumulación) y
`demos/index.html` (landing + lanzador).

---

## Configurar (todo en ficheros, no en código)

- **`config.json`** — `wip_limit` (`{ agents, cost_eur, foundational_cost_eur }`),
  `gated_tools`, `approval_routing`, `broker_url`, timeouts.
- **`mcp/policy.json`** — reglas `allow`/`ask`/`deny` por tool y dominio, y `quotas`
  (incluidas las de coste).
- **`mcp/models.json`** — precio €/1M tokens y clase (local/foundational) por modelo.
- **`settings.json`** — lectura preaprobada en `allow`; tus tools con efectos en `ask`.

Tus subagentes especialistas viven en `agents/*.md` (limita sus `tools` por rol). La
gobernanza es uniforme: se controla la operación con efectos, no el agente.

---

## Sin Claude Code (otros runtimes)

Usa el cliente genérico `client/agentboard_client.py`:

```python
from agentboard_client import AgentBoard
board = AgentBoard()                                  # broker en :8787
sid = board.start("Investigación X", model="gpt-4o", kind="researcher")
if board.gate(sid, "Write", {"path": "out.md"}):      # bloquea hasta Aprobar/Denegar
    do_write()
if not board.account_llm("opus", 18000, sid):         # presupuesto de coste (€)
    return
board.stop(sid)
```

---

## Verificar la instalación

```bash
python3 mcp/canonical.py && python3 mcp/quota.py && python3 mcp/audit.py && python3 mcp/cost.py
python3 tests/test_binding.py && python3 tests/test_quota.py && python3 tests/test_audit.py \
  && python3 tests/test_decorated.py && python3 tests/test_cost.py
```

Todo debe imprimir "OK" / "TODAS LAS COMPROBACIONES PASARON".
