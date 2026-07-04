## Qué cambia
Describe el cambio en una o dos frases.

## Motivación
Qué problema resuelve o qué mejora. Enlaza el issue si existe (`Closes #…`).

## Tipo
- [ ] Fix (corrige un fallo)
- [ ] Feature (añade funcionalidad)
- [ ] Docs / config
- [ ] Refactor / interno

## Checklist
- [ ] `python3 scripts/validate_config.py` pasa
- [ ] Los tests pasan: `python3 tests/test_binding.py && … test_quota / test_audit / test_cost / test_providers / test_decorated`
- [ ] Auto-comprobaciones de módulos OK: `python3 mcp/{canonical,quota,audit,cost}.py`
- [ ] Si tocaste el tablero: HTML válido y el JS pasa `node --check`
- [ ] Mantiene la filosofía: **observar y gobernar**, no orquestar; genérico y configurable (lo específico de un proyecto va en `config.json` / `examples/`)
- [ ] Si afecta a la gobernanza, revisado contra `THREAT_MODEL.md`
- [ ] CHANGELOG.md actualizado

## Notas para el revisor
Cualquier contexto útil (capturas del tablero, decisiones de diseño, etc.).
