# 0005 — Tiempo real en el tablero: SSE sobre WebSocket

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0001](0001-niveles-de-despliegue.md), [0003](0003-persistencia-y-estado.md)

## Contexto

El tablero se actualiza por **polling**: pinta con `GET /api/state` y el hook espera la
decisión con `GET /api/decision?req_id=...` cada ~1.5s. Funciona, pero:

- Latencia perceptible y carga constante aunque no pase nada.
- No escala a muchos operadores/tarjetas.

La lista pide "WebSocket/SSE para actualizaciones en vivo". Hay que elegir uno.

## Decisión

Usar **Server-Sent Events (SSE)** como mecanismo de push del tablero, no WebSocket.

- El broker expone `GET /api/stream` (SSE) que emite eventos de cambio de estado
  (`card.updated`, `request.created`, `decision.made`, …). El tablero se suscribe y
  aplica deltas; `GET /api/state` queda como *snapshot* inicial y fallback.
- El canal **agente→broker** sigue siendo HTTP POST normal (no necesita full-duplex).
- La aprobación humana se sigue haciendo por `POST /api/decide` (con token, ADR-0010);
  el resultado se propaga a todos los suscriptores por SSE.

Razones para SSE frente a WebSocket:
- El flujo es **unidireccional** (servidor→tablero); SSE encaja exactamente.
- Es HTTP plano: reconexión automática del navegador (`Last-Event-ID`), atraviesa
  proxies sin upgrade, y se implementa sobre el `ThreadingHTTPServer` actual sin
  librerías nuevas → respeta el nivel Solo (ADR-0001).
- WebSocket añade framing, handshake de upgrade y normalmente una dependencia; su
  ventaja (full-duplex) aquí no se usa.

**Fan-out multi-réplica (nivel Scale)**: con varias instancias del broker, los eventos
se distribuyen por un **bus** (Redis pub/sub, opcional). En Solo/Team el bus es
in-process. La interfaz del bus es estable; SSE es solo el último tramo al navegador.

## Consecuencias

**Positivas**
- Actualización instantánea sin polling; menos carga.
- Cero dependencias nuevas en el nivel Solo; reconexión gratis.
- El mismo stream alimenta métricas en vivo en las tarjetas (tokens/latencia/riesgo).

**Negativas / coste**
- SSE es unidireccional: cualquier acción del operador sigue yendo por POST (ya es así).
- Límite de conexiones por navegador a un host (6 en HTTP/1.1); irrelevante para un
  tablero, mitigable con HTTP/2 en Scale.
- Hay que gestionar el ciclo de vida de los clientes SSE en el servidor (heartbeats,
  limpieza de conexiones muertas).

## Alternativas descartadas

- **Seguir con polling**: simple pero con latencia y carga; no es "producción".
- **WebSocket**: full-duplex innecesario, más peso y dependencia; complica el nivel Solo.
- **Long-polling**: peor que SSE en navegadores modernos sin ventajas aquí.
