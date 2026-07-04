---
name: "🐞 Reporte de fallo"
about: Algo no funciona como debería
title: "[bug] "
labels: bug
---

## Qué pasa
Describe el fallo con claridad.

## Cómo reproducirlo
1. …
2. …
3. Error observado:

## Qué esperabas
Comportamiento esperado.

## Entorno
- SO:
- Python (`python3 --version`):
- Versión de agent-board (`.claude-plugin/plugin.json` → `version`):
- Runtime: Claude Code / cliente genérico / otro
- Modo del tablero: simulado / en vivo (`?feed=/api/state`) / offline

## Configuración (si aplica)
Salida de `python3 scripts/validate_config.py` y, si puedes, el `profile`/`unit` usados.
No pegues secretos ni tokens.

## Logs
Adjunta la salida relevante del broker o del hook (redacta datos sensibles).
