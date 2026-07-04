# 0004 — Motor de políticas: nativo + Rego opcional + simulación

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0001](0001-niveles-de-despliegue.md), [0002](0002-capa-de-interceptacion.md), [THREAT_MODEL](../../THREAT_MODEL.md) #9, #10, #11, #12

## Contexto

El motor actual (`mcp/agentboard_gate.py::decide_rule`) es propio y eficaz: casa por
glob de tool, evalúa predicados (`==`, `!=`, `<`, `>`, `in`, `startswith`, `glob`…),
soporta `ask_if`/`deny_if` y restricción por rol, devuelve `allow|deny|ask` o `None`
(nada casa) y aplica `default: ask`. Es cero-dependencias y rápido.

Limitaciones para producción:
- Solo condiciones **AND** dentro de una regla; no hay OR ni anidamiento.
- No hay **overrides temporales** ("aprobar por 1h", "siempre en este contexto").
- No hay forma de **probar una política antes de activarla** (trust ladder).
- La lista pide compatibilidad con **OPA/Rego**, que muchos equipos ya usan.

## Decisión

Formalizar una interfaz **`Decider`** (`decide(tool, payload, ctx) -> Decision`) con
tres implementaciones, manteniendo el motor nativo como **default**:

1. **Motor nativo extendido** (default, cero-dep):
   - Condiciones **compuestas**: `all_of` / `any_of` / `not` anidables, además del AND
     plano actual (retrocompatible).
   - **Globs por dominio** ya soportados; se documentan como ciudadanos de primera.
   - **Overrides temporales**: una decisión `ask` aprobada puede crear una regla
     efímera con TTL y *scope* (por agente/workflow/tool/payload-hash) que auto-aprueba
     repeticiones equivalentes hasta caducar. Se audita su creación y uso.
2. **Adaptador Rego/OPA** (opcional, nivel Team/Scale): delega la decisión en una
   policy Rego (OPA embebido o sidecar). Para quien ya tiene Rego; el input es el mismo
   `{tool, payload, ctx}`. No se hace requisito.
3. **Importador**: utilidad para traducir reglas nativas ↔ esqueleto Rego, para migrar
   en cualquier dirección.

**Modo simulación / dry-run (trust ladder)**: cualquier `Decider` puede ejecutarse en
modo *shadow*: evalúa contra tráfico en vivo o histórico y **registra qué habría
hecho** sin aplicarlo. El operador compara, ajusta y *promueve* la política a
*enforce*. Esto permite endurecer sin romper flujos.

**Endurecimiento ligado al threat model**:
- El **resumen** que ve el operador lo compone el servidor desde campos validados, no
  texto libre del payload (#12).
- Config crítica de seguridad (`FAIL_OPEN`, origen del broker) no se toma de variables
  influenciables por el agente; fail-closed fijo (#10).
- `policy.json` se carga con verificación de integridad y, en despliegue, fuera del
  árbol escribible por el agente (#9).

## Consecuencias

**Positivas**
- Expresividad real sin imponer OPA a todo el mundo.
- El dry-run reduce el miedo a cambiar políticas: es el camino seguro a producción.
- Overrides temporales resuelven la fricción de aprobar lo mismo una y otra vez.

**Negativas / coste**
- Más superficie en el motor nativo (parser de condiciones compuestas) → más tests.
- El adaptador Rego añade una dependencia opcional y dos caminos de evaluación a probar.
- Los overrides temporales son una vía de relajación: requieren auditoría fuerte y TTL
  corto por defecto para no convertirse en un agujero.

## Alternativas descartadas

- **Migrar todo a OPA/Rego**: potente pero pesado y con curva; rompería cero-dep (ADR-0001).
- **Quedarse con AND plano**: insuficiente para reglas reales por dominio.
- **Activar políticas directamente sin dry-run**: arriesgado en sistemas con efectos.
