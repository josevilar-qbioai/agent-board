# 0007 — Binding de aprobación al payload

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0006](0006-auditoria-hash-chain.md), [THREAT_MODEL](../../THREAT_MODEL.md) #8

## Contexto

Hoy el flujo de `ask` es: el cliente hace `POST /api/request` con `{session_id,
tool_name, summary, tool_input}` y recibe un `req_id` entero secuencial; luego sondea
`GET /api/decision?req_id=...` hasta `allow`/`deny`. El operador aprueba con
`POST /api/decide {req_id, decision}`.

El **threat model #8** (replay/race de aprobación) está marcado como *endurecer*: nada
ata la decisión al contenido exacto que se va a ejecutar. Riesgos concretos:

- **Replay**: reutilizar una decisión `allow` para una operación distinta.
- **Race / TOCTOU**: cambiar el `tool_input` entre la aprobación y la ejecución.
- `req_id` secuencial es **adivinable**; facilita interferencias.

## Decisión

Ligar criptográficamente la decisión al payload exacto y hacerla de un solo uso:

1. **Payload canónico + hash**: al crear la petición, el broker computa
   `payload_hash = sha256(canonical_json({tool, payload}))` (claves ordenadas,
   normalización estable). La tarjeta y la auditoría guardan ese hash.
2. **`req_id` no adivinable**: identificador aleatorio (p. ej. `secrets.token_urlsafe`)
   en lugar del entero secuencial.
3. **Decisión atada al hash**: `POST /api/decide` referencia `{req_id, payload_hash,
   decision}`; el broker rechaza si el hash no coincide con el de la petición.
4. **Un solo uso + TTL**: la decisión se consume al ejecutarse y caduca con un TTL
   corto (config, p. ej. 120s). Antes de ejecutar, el lado que aplica (gate/proxy)
   **revalida** que el `payload_hash` del intento real coincide con el aprobado.
5. **Re-verificación en el punto de efecto**: el `@gated`/proxy recalcula el hash del
   payload que va a ejecutar y lo compara con el aprobado; si difiere → deny.

El operador, además, ve un **resumen canónico** derivado de campos validados (no del
texto libre del payload), cerrando también #12.

## Consecuencias

**Positivas**
- Cierra replay y TOCTOU: una aprobación vale para *exactamente* ese contenido, una vez.
- `req_id` aleatorio elimina la adivinación/interferencia.
- El `payload_hash` es justo lo que la auditoría hash-chain (ADR-0006) necesita anclar.

**Negativas / coste**
- Requiere una **canonicalización** estable y bien testeada (orden de claves, tipos,
  unicode); un canonicalizador inconsistente causaría denegaciones espurias.
- TTL corto puede caducar aprobaciones legítimas si el operador tarda; configurable y
  con opción de re-solicitar.
- Pequeño coste de hashing por operación (despreciable).

## Alternativas descartadas

- **Seguir con `req_id` secuencial sin hash**: deja abiertos replay y race (#8).
- **Firmar la decisión con la clave del operador pero sin atarla al payload**: prueba
  *quién* aprobó, no *qué*; no cierra TOCTOU.
