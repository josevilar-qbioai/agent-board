# 0006 — Auditoría append-only con hash-chain

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0003](0003-persistencia-y-estado.md), [0007](0007-binding-de-aprobacion.md), [THREAT_MODEL](../../THREAT_MODEL.md)

## Contexto

El gate ya escribe un log de decisiones (`AGENT_BOARD_AUDIT`, def `mcp/gate-audit.log`).
Es un log plano: útil, pero **no es tamper-evident**. Quien tenga acceso de escritura
puede editar o borrar líneas sin dejar rastro, y no hay forma de demostrar que el
registro está completo. Para gobernanza seria — el valor que vende el proyecto — la
auditoría debe ser **verificable** y exportable.

## Decisión

Convertir el log de auditoría en una **cadena append-only con hash encadenado**
(estilo blockchain ligero, sin consenso ni red):

- Cada entrada registra: timestamp, `tool`, `payload_hash` (canónico, ADR-0007),
  decisión (`allow|deny|ask`→resultado), motivo, identidad del agente y del operador
  (ADR-0010), `req_id`, y **`prev_hash`** (hash de la entrada anterior).
- `entry_hash = sha256(prev_hash || entrada_canónica)`. Alterar o borrar cualquier
  entrada rompe la cadena a partir de ahí.
- **Verificador** (`agent-board audit verify`): recorre la cadena y confirma
  integridad; señala el punto exacto de ruptura si la hay.
- **Sellado periódico opcional**: publicar el último `entry_hash` (a un fichero
  externo, a un repo, o firmado con la clave del broker, ADR-0010) para anclar la
  cadena en el tiempo y detectar truncado del final.

**Niveles** (ADR-0001):
- Solo/Team: cadena en fichero (append-only) + verificador. Cero dependencias.
- Scale: **exportador a SIEM** (formato JSON Lines / CEF) como *sink* adicional; el
  hash-chain local sigue siendo la fuente de verdad.

La interfaz **`AuditSink`** abstrae el destino (fichero encadenado, SIEM, ambos).

**Override de emergencia**: cuando un operador fuerza una aprobación fuera de política
(romper-cristal), se registra como una entrada de auditoría de tipo `emergency_override`
con justificación obligatoria, identidad y el mismo encadenado — de modo que el camino
excepcional es el **más** auditado, no el menos.

## Consecuencias

**Positivas**
- Auditoría *tamper-evident*: se puede demostrar integridad y detectar manipulación.
- Base creíble para cumplimiento y para confiar el override de emergencia.
- El export a SIEM no compromete la fuente de verdad local.

**Negativas / coste**
- Append estrictamente serializado (un escritor de la cola de auditoría); encaja con
  el `Store` SQLite/Postgres (ADR-0003).
- El sellado externo añade un paso operativo opcional.
- Hash-chain detecta manipulación pero no la *impide* si el host está comprometido (el
  threat model ya asume integridad del proceso); el sellado externo mitiga el truncado.

## Alternativas descartadas

- **Log plano actual**: no verificable; insuficiente para gobernanza.
- **Solo enviar a SIEM**: dependencia externa obligatoria; rompe nivel Solo y deja sin
  garantía a quien no tiene SIEM.
- **Firmar cada línea sin encadenar**: detecta edición de una línea pero no borrado de
  líneas intermedias ni reordenado.
