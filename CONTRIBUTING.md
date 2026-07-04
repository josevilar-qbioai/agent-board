# Contribuir

Gracias por tu interes. Este es un harness independiente del dominio: las
mejoras deben mantenerlo generico y configurable, no atado a un proyecto.

## Antes de un PR
- Valida los JSON: `python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('**/*.json', recursive=True)]"`
- Comprueba que el hook compila: `python3 -m py_compile hooks/emit_card.py`
- Prueba el plugin en local: `claude --plugin-dir .`
- Si tocas hooks/, agents/, .mcp.json: `/reload-plugins` o reinicia Claude Code.

## Que encaja bien
- Adaptadores de routing de aprobacion (file, webhook, Slack/Teams).
- Modos de feed del tablero (poll, websocket, fichero).
- Nuevos tipos de agente reutilizables (siempre dominio-neutral).
- Ejemplos por proyecto en `examples/` (sin credenciales ni datos reales).

## Que NO encaja
- Logica especifica de un tenant/empresa fuera de `examples/`.
- Tools de escritura preaprobadas por defecto: las operaciones con efectos
  deben quedar siempre en la lista `ask` de `settings.json`.

## Seguridad
Si encuentras un problema de seguridad, no abras una issue publica: contacta
en privado con el mantenedor.
