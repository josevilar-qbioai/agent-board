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

## Federación y trabajo futuro

**Federación (implementado, v0.20.0).** El tablero se adopta por **unidades pequeñas y
autónomas**: cada una tiene su `policy.json`/`config.json` y su **propia cadena**. Para
consolidar sin acoplar:
- cada instalación se etiqueta con `AGENT_BOARD_DEPLOYMENT=<unidad>` (estampado en cada
  entrada);
- `scripts/forward_audit.py` reenvía la cadena de la unidad a un **central** (carpeta con
  un fichero por unidad, `--to-dir`, o colector HTTP, `--to-url`);
- `scripts/analyze_decisions.py <carpeta>` verifica **cada cadena por separado** y agrega
  el conjunto por despliegue/unidad/agente/modelo/tool + export JSONL.

Principio: **las cadenas NO se fusionan**. Concatenar entradas de unidades distintas
rompería el encadenado `prev_hash`. El central es una *colección* de cadenas
re-verificables, cada una con su prueba de integridad; así se preserva la autonomía de la
unidad y su garantía local.

**Opción futura — sello de integridad GLOBAL (Merkle sobre las unidades).** La federación
actual prueba la integridad *por unidad*, pero no del *conjunto* (no detecta que falte una
unidad entera, ni ancla el estado global en el tiempo). Extensión propuesta, sin romper el
diseño:
- Periódicamente, tomar el `entry_hash` final (la "raíz" actual) de la cadena de **cada**
  unidad y construir un **árbol de Merkle** con esas hojas → una única `root` global.
- Registrar cada `root` en un **libro de sellos** (append-only, él mismo encadenado) con
  timestamp, el conjunto de unidades incluidas y sus alturas de cadena. Opcionalmente
  firmar la `root` (clave del broker central, ADR-0010) o anclarla externamente (repo,
  servicio de timestamping) para atestiguación en el tiempo.
- Verificación en dos niveles: (1) cada unidad sigue verificando su cadena localmente;
  (2) un `verify-federation` comprueba que las hojas del árbol coinciden con los
  `entry_hash` finales presentes y que la secuencia de `root` no se ha truncado/reordenado
  → detecta **omisión de una unidad** o **retroceso** del estado global.
- Propiedades: no requiere fusionar cadenas ni un escritor compartido; cada unidad sigue
  siendo autónoma; el sello es incremental y barato (una hoja por unidad por periodo);
  degrada a "solo por-unidad" si no se despliega. Coste: un componente central de sellado
  (cron/servicio) y la gestión de la clave de firma si se ancla criptográficamente.

Estado: **propuesto** (no implementado). Se activaría cuando una organización necesite
atestiguar la integridad *de toda la flota* (auditoría/compliance a nivel corporativo),
no solo de cada unidad por separado.
