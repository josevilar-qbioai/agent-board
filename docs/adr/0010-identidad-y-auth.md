# 0010 — Identidad y auth (humanos y agentes)

- Estado: **propuesto**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0001](0001-niveles-de-despliegue.md), [0006](0006-auditoria-hash-chain.md), [0007](0007-binding-de-aprobacion.md), [THREAT_MODEL](../../THREAT_MODEL.md) #7, #10

## Contexto

La autenticación hoy es un **secreto compartido**: `AGENT_BOARD_OP_TOKEN` (o uno
aleatorio por arranque) que se exige en `/api/decide` y `/api/reset`. El token viaja
por el fragmento de URL terminal→navegador. Esto cierra la auto-aprobación (#7) en el
caso simple, pero:

- No hay **identidad de operador**: cualquiera con el token es "el operador". En equipo
  no se sabe *quién* aprobó.
- No hay **identidad de agente**: el `session_id` es autodeclarado; un agente puede
  suplantar a otro en el canal `request`/`event`.
- Riesgo residual ya documentado: si el agente corre como el mismo usuario del SO,
  puede leer el token del broker.

La lista pide: humanos → SSO/OAuth + tokens de aprobación de corta duración; agentes →
API keys o, mejor, **identidades criptográficas (Ed25519)**.

## Decisión

Separar y reforzar las dos identidades, manteniendo el token como default del nivel Solo.

**Humanos (operadores)**
- **Solo**: token actual (sin cambios; barrera cero).
- **Team/Scale**: **OIDC/OAuth** (Authelia, Keycloak, Google, Okta…). El operador se
  autentica; `/api/decide` exige sesión válida y registra **quién** aprobó en la
  auditoría (ADR-0006). Las aprobaciones se materializan como **tokens de aprobación de
  corta duración** ligados a la identidad y al `payload_hash` (ADR-0007).

**Agentes**
- **Identidad Ed25519 por agente**: cada agente tiene un par de claves; registra su
  clave pública en el broker (o se aprovisiona). Cada `request`/`event` va **firmado**
  sobre `{session_id, tool, payload_hash, nonce, ts}`. El broker **verifica la firma**
  antes de crear la tarjeta y registra la identidad real en la auditoría.
- **API keys** como escalón intermedio para quien no quiera gestionar claves.
- Esto ata el `session_id` a una identidad verificable: un agente no puede hablar por
  otro, y la auditoría refleja el actor real, no un campo autodeclarado.

**Endurecimiento de config (#10)**: el origen del broker y `FAIL_OPEN` no se toman de
variables influenciables por el agente; en Team/Scale el broker valida su propia
configuración al arrancar y rechaza un `FAIL_OPEN` no firmado por el operador.

## Consecuencias

**Positivas**
- "Quién aprobó" y "qué agente pidió" quedan probados criptográficamente → auditoría
  con valor real (cumplimiento, forense).
- Las firmas Ed25519 cierran la suplantación entre agentes y refuerzan el binding (#7).
- OIDC encaja con los IdP que los equipos ya tienen, sin reinventar gestión de usuarios.

**Negativas / coste**
- Gestión de claves/aprovisionamiento de agentes: complejidad operativa nueva
  (rotación, revocación). Por eso es **opcional** (nivel Team/Scale).
- OIDC añade dependencia de un IdP en Team/Scale; en Solo se mantiene el token.
- El riesgo "agente como mismo usuario del SO" solo se cierra del todo con
  **aislamiento** (sandbox/usuario distinto), que es responsabilidad del despliegue.

## Alternativas descartadas

- **Solo token compartido**: no da identidad ni en humanos ni en agentes; insuficiente
  para equipo.
- **mTLS para agentes**: válido pero más pesado de operar que firmar payloads con
  Ed25519, y no ata la firma al contenido de cada operación.
- **Hacer OIDC obligatorio**: rompería el nivel Solo (ADR-0001).
