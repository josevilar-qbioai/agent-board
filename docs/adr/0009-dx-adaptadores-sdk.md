# 0009 — DX: adaptadores SDK y "2 líneas para gobernar"

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0002](0002-capa-de-interceptacion.md)

## Contexto

Ya existe un **cliente genérico** (`client/agentboard_client.py`) con `start/step/stop`
y `gate(...)` que bloquea hasta la aprobación, y el README describe adaptadores de ~20
líneas por framework. Pero "describir" no es "soportar": la lista pide DX al nivel de
*"2 líneas para gobernar cualquier tool"* (como el toolkit de Microsoft), con ejemplos
**probados** para CrewAI, LangGraph, Claude Code/Cursor y servidores MCP de terceros.
Para OSS, la DX y los ejemplos que funcionan a la primera son adopción.

## Decisión

Empaquetar y **probar** los adaptadores como parte del proyecto, no como prosa:

1. **Contrato del adaptador**: dos puntos de enganche, ya presentes en el cliente — el
   ciclo de vida (`start`/`step`/`stop`) y la operación con efectos (`gate`, que
   bloquea). Cualquier runtime se gobierna mapeando esos dos.
2. **Adaptadores oficiales** en `adapters/`, uno por framework, con la API mínima:
   - **CrewAI**, **LangGraph**, **AutoGen**, **OpenAI Agents SDK**: envuelven la
     ejecución de tools; antes de una con efectos, `board.gate(...)`.
   - **Claude Code / Cursor**: vía hooks (ya existe) y/o el proxy MCP (ADR-0002).
   - **Servidores MCP de terceros**: vía el proxy MCP — el caso "gobierna lo que no
     controlas", sin tocar su código.
3. **Azúcar de "2 líneas"**: un decorador/`context manager` que envuelve una tool
   arbitraria:
   ```python
   from agentboard import govern
   govern(my_tool)            # ahora pasa por política + tablero
   # o:  with govern.gate("deploy", payload): do_deploy()
   ```
4. **Test de contrato común**: una suite que todo adaptador debe pasar (lifecycle
   visible en el tablero, `gate` bloquea hasta decisión, deny impide el efecto,
   fail-closed sin broker). Garantiza que los ejemplos del README **funcionan**.

## Consecuencias

**Positivas**
- "2 líneas" reales y verificadas → adopción.
- El test de contrato evita que los adaptadores se pudran al evolucionar el broker.
- Refuerza el mensaje del proxy MCP (ADR-0002): gobernar terceros sin integrarlos.

**Negativas / coste**
- Mantener N adaptadores frente a cambios de API de frameworks de terceros (CrewAI,
  LangGraph evolucionan rápido). Mitigación: mantener el núcleo (`gate`) estable y los
  adaptadores finos.
- CI necesita instalar esos SDKs (solo en jobs de adaptador, no en el núcleo Solo).

## Alternativas descartadas

- **Dejarlo en documentación**: ejemplos que se rompen en silencio dañan la confianza.
- **Un único adaptador "universal" mágico**: imposible; cada framework engancha tools
  de forma distinta. Mejor finos y probados.
