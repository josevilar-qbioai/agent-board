---
description: Arranca el broker y abre el tablero Kanban de agentes con aprobacion de doble via.
---

Arranca el broker local y abre el tablero de agentes de este plugin.

Modo recomendado (aprobacion de doble via):
1. Arranca el broker (sirve el tablero y coordina decisiones):
   `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/broker.py"`
2. Abre: http://127.0.0.1:8787/agent-board.html?feed=/api/state
3. Cuando un agente intente una operacion con efectos, aparecera una tarjeta en
   la columna Needs Input. Pulsa Aprobar o Denegar: el hook PreToolUse esta
   esperando esa decision y dejara continuar o bloqueara la tool.

Modo demo (sin broker): abre `agent-board.html` directamente -> simulacion.
Modo observabilidad offline: abre `agent-board.html?feed=board-state.json` (los
hooks escriben ese fichero si el broker no esta levantado; solo lectura).

No realices ninguna operacion con efectos desde aqui; el tablero solo decide
sobre las peticiones que los agentes ya han solicitado.
