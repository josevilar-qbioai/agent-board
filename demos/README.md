# Demos

Abre **`index.html`** en el navegador. Es una sola página que hace de landing
(qué es el proyecto, los pilares, cómo fluye una decisión) **y** de lanzador del
demo: desde el botón "Abrir el tablero" llegas al tablero funcional.

La demo **funcional** es el tablero real en `../board/agent-board.html`, con tres modos:

| Cómo se abre | Qué muestra |
|---|---|
| `board/agent-board.html` | Demo simulado: agentes ficticios avanzando por las columnas. Sin backend. |
| `board/agent-board.html?feed=/api/state` | En vivo contra el broker, con aprobaciones reales (doble vía). Requiere `python3 hooks/broker.py`. |
| `board/agent-board.html?feed=board-state.json` | Observabilidad offline (solo lectura). |

Para el modo en vivo: `python3 hooks/broker.py` imprime un token de operador y la URL
del tablero con el token en el fragmento.
