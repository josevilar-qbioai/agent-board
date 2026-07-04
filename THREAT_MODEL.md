# Modelo de amenazas — agent-board

Guía de gobernanza. Genérica e independiente del LLM. Describe el invariante que
protege la puerta, por dónde podría **colarse una acción sin pasar por ella**, y
cómo cerrar cada vía.

## El invariante

> **Ninguna operación con efectos se ejecuta sin pasar por la política de la puerta.**

Toda la potencia del enfoque (Opción B: la puerta vive *dentro* de la tool MCP)
descansa en este invariante. El modelo de amenazas es, simplemente, el catálogo de
formas de romperlo.

## Modelo de confianza

**No confiamos en** el LLM ni en el cliente (Claude, ChatGPT, Grok, Antigravity,
local…). Se asume que puede equivocarse, ser manipulado por inyección de prompt, o
ser directamente adversario.

**Confiamos en** (y por tanto hay que proteger):
- el servidor MCP y su proceso,
- la integridad de `policy.json`,
- el canal por el que el **operador humano** aprueba/deniega,
- que la operación real (script/API/DB) solo sea invocable a través de la tool gateada.

Si alguno de estos se rompe, el invariante cae. El catálogo siguiente se ordena por
ahí.

## Catálogo de vías de bypass

Estado: **incluido** = el repo lo mitiga · **tuyo** = responsabilidad del integrador ·
**endurecer** = mejora recomendada, aún no implementada.

| # | Vía (cómo se cuela) | Mitigación | Estado |
|---|---|---|---|
| 1 | **Acción fuera de MCP**: el agente ejecuta el efecto por shell (`curl`, CLI) en vez de llamar a tu tool. | Toda capacidad con efectos del agente debe ir por tools gateadas. Gatea/deniega `Bash` y exec genéricos; en clientes sin hooks, desactiva o restringe su shell. | tuyo |
| 2 | **Otra tool con el mismo efecto**: un MCP genérico (filesystem, HTTP) o un servidor no gateado hace el daño. | Inventario de capacidades: que no exista ninguna tool con efectos *sin* gatear. `default: ask` en la política para lo no contemplado. Deniega conectores de egress no auditados. | incluido (default ask) + tuyo |
| 3 | **Efecto diferido**: el agente escribe un fichero (CI, cron, IaC) que ejecuta el efecto más tarde. | Trata las escrituras de configuración/infra como operaciones con efectos: gatea por ruta (`glob`/`startswith` en la política). | tuyo |
| 4 | **Atajo por debajo de la tool**: el script/API real es invocable sin pasar por el wrapper `@gated`. | La función gateada debe ser el **único** punto de entrada. La implementación interna, privada; credenciales accesibles solo desde el camino gateado; el script no ejecutable por el agente por otra vía. | tuyo |
| 5 | **Tool nueva sin decorar**: alguien añade una tool con efectos y olvida `@gated`. | `default: ask` la captura (no se ejecuta sin aprobación). **Implementado** (v0.10.0): lint en CI (`tests/test_decorated.py`) que falla si una tool pública no está `@gated`. Revisión de código. | incluido |
| 6 | **Llamada interna sin decorador**: el código importa la función interna sin el decorador. | Decora en el límite exportado; mantén privada la implementación; registra en MCP solo la versión gateada. | tuyo |
| 7 | **Auto-aprobación**: un agente con shell hace `POST /api/decide` y aprueba su propia petición. | **Implementado**: `/api/decide` (y `/api/reset`) exigen la cabecera `X-Operator-Token`; el agente solo puede `request`/`decision`. El token viaja terminal→navegador (fragmento `#token=`, que no llega al servidor ni a logs). **Residual**: si el agente corre como el **mismo usuario del SO**, podría leer el stdout/entorno del broker y robar el token; el cierre completo exige ejecutar el agente en sandbox o con otro usuario. | incluido (parcial) |
| 8 | **Replay/race de aprobación**: reutilizar una decisión antigua o aprobar antes de ver el impacto real. | **Implementado** (v0.8.0, ADR-0007): `req_id` aleatorio de un solo uso; la decisión se liga al hash canónico de tool+payload (`mcp/canonical.py`); TTL corto; `/api/decide` rechaza hash distinto, replay o caducada (409); hook/gate/cliente re-verifican el hash en el punto de efecto (anti-TOCTOU). | incluido |
| 9 | **Manipular la política**: el agente edita `policy.json` para poner todo en `allow`. | `policy.json` fuera del árbol escribible por el agente y/o de solo lectura; gatea (deny) la escritura sobre la propia política; verificación de integridad al cargar. | tuyo + endurecer |
| 10 | **Manipular la config por entorno**: fijar `AGENT_BOARD_FAIL_OPEN=1` o apuntar `AGENT_BOARD_BROKER` a un broker falso que auto-aprueba. | No tomar config crítica de seguridad de variables influenciables por el agente; fail-closed fijo; validar el origen del broker. | endurecer |
| 11 | **Trocear para esquivar umbrales**: 60 borrados de 1 en vez de 1 de 60, para evadir `deny_if count>50`. | **Implementado** (v0.8.0, ADR-0008): contabilidad agregada en ventana deslizante (`mcp/quota.py`) en el broker. La política puede declarar `quotas` por (agente/workflow/tool) con `limit` y `window`; el límite real es el acumulado, no el valor por llamada. `on_exceed: deny\|ask`. El gate y el hook consultan al broker antes del efecto; fail-closed si hay cuota y el broker no responde. | incluido |
| 12 | **Resumen engañoso al humano**: el payload controla el texto que ve el operador y le induce a aprobar deprisa. | **Implementado** (v0.10.0): el broker compone el resumen (`canonical_summary`) desde campos validados del payload, truncados y etiquetados; el texto libre del agente se muestra aparte como "nota" secundaria, no como titular. | incluido |
| 13 | **Ensamblaje multi-paso (deputado confundido)**: lee datos sensibles con tools `allow` y los exfiltra con una tool de egress `allow`. | Patrón *quarantine*: un agente que lee contenido no confiable no puede usar tools de alto privilegio/egress. Conciencia de flujo de datos. Credenciales de mínimo privilegio por dominio. | tuyo |
| 14 | **Radio de daño**: si la puerta se salta, un servidor con credenciales potentes causa un desastre. | Un servidor = un dominio, con credenciales de mínimo privilegio; separar lectura y escritura. Limita el daño *aunque* falle la puerta. | tuyo (higiene) + incluido (patrón) |
| 15 | **Caída del broker en un `ask`**: sin quién apruebe, ¿se relaja el control? | Fail-closed: sin decisión → deny. Timeout acotado. Alerta si el broker no responde. | incluido |

## Checklist mínimo de endurecimiento

Para que el invariante se sostenga en producción, por orden de prioridad:

1. ~~**Token en `/api/decide`**~~ (cierra el #7): **hecho** desde v0.7.0. Aprobar exige
   `X-Operator-Token`. Cierra el cierre por completo solo si además el agente corre
   aislado (sandbox/usuario distinto), para que no pueda leer el token del broker.
1b. ~~**Binding de aprobación al payload**~~ (cierra el #8): **hecho** desde v0.8.0
   (ADR-0007). `req_id` aleatorio de un solo uso, decisión ligada al hash canónico de
   tool+payload, TTL, y re-verificación en el punto de efecto.
2. **Canaliza todo efecto por MCP** (#1, #2): ninguna operación con efectos accesible
   por shell u otra tool sin gatear. Desactiva exec genérico donde no haga falta.
3. **`policy.json` y la implementación interna fuera del alcance de escritura del
   agente** (#4, #6, #9).
4. **Test/CI que verifique** que toda tool con efectos está decorada (#5).
5. **Credenciales de mínimo privilegio por dominio**, lectura y escritura separadas (#14).
6. ~~**Contabilidad agregada** para operaciones troceables (#11)~~: **hecho** desde
   v0.8.0 (ADR-0008). Patrón quarantine para flujos lectura→egress (#13): pendiente.
7. ~~**Auditoría tamper-evident**~~: **hecho** desde v0.10.0 (ADR-0006). El log de
   decisiones es una cadena con hash encadenado (`mcp/audit.py`); `python3 mcp/audit.py
   verify` detecta cualquier alteración o borrado. Sellado externo / export a SIEM:
   pendiente (nivel Scale).

## No-objetivos y riesgo residual

- La puerta gobierna **acciones que pasan por la tool**, no lo que el modelo *dice* o
  *razona*, ni efectos por canales ajenos a tu servidor. Lo que no se canalice por
  MCP, queda sin gobernar — por diseño, no por descuido.
- No sustituye al RBAC: la puerta decide allow/ask/deny; *quién* es el principal lo
  aporta tu capa de autenticación.
- No protege frente a un servidor o un host ya comprometidos: asume integridad del
  proceso y del transporte. Endurécelos con los medios habituales (auth del MCP,
  aislamiento, mínimo privilegio).

## La regla de oro

Invierte la confianza: no intentes certificar al actor (el LLM, infinito e
imprevisible), pon el control en la infraestructura (la tool), una vez, con reglas
deterministas y registro de todo el que pasa. Este documento existe para enumerar
las grietas por las que alguien podría rodear ese control, y cerrarlas.
