# Mapa del repositorio

Guía de qué hay en `agent-board` y para qué sirve. Etiquetas:
**[núcleo]** imprescindible en tiempo de ejecución · **[config]** ajustes ·
**[demos]** visualización/landing · **[docs]** documentación/diseño ·
**[dev]** desarrollo/CI · **[plugin]** metadatos del plugin de Claude Code.

## Núcleo (el producto)

| Ruta | Tipo | Qué hace |
|------|------|----------|
| `hooks/broker.py` | [núcleo] | Servidor (stdlib) del tablero: estado, `/api/*`, aprobaciones de doble vía, cuotas, coste, auditoría, `config`. |
| `hooks/hook.py` | [núcleo] | Hooks de Claude Code (`SessionStart`/`PreToolUse`/`Stop`): enganchan la puerta y las cuotas. |
| `hooks/hooks.json` | [plugin] | Registro de los hooks del plugin. |
| `mcp/agentboard_gate.py` | [núcleo] | Puerta determinista dentro de la tool (`@gated`): política → cuota → tablero → auditoría. |
| `mcp/policy.json` | [config] | Reglas `allow`/`ask`/`deny` por tool y dominio + `quotas` (incl. coste). Tu lógica de negocio. |
| `mcp/canonical.py` | [núcleo] | Hash canónico `op_hash(tool,payload)`: fuente única del binding de aprobación. |
| `mcp/audit.py` | [núcleo] | Cadena de auditoría append-only con hash encadenado + verificador (`verify`). |
| `mcp/quota.py` | [núcleo] | Cuotas agregadas en ventana deslizante (lógica pura). |
| `mcp/cost.py` | [núcleo] | Coste € por (modelo, tokens) y clase local\|fundacional. |
| `mcp/models.json` | [config] | Tabla de precios €/1M tokens y clase por modelo. |
| `mcp/example_tools.py` | [docs] | Ejemplo genérico de tool `@gated` (referencia para integradores). |
| `client/agentboard_client.py` | [núcleo] | Cliente genérico (sin Claude Code): `gate()`, `report_usage()`, `account_llm()`. |
| `client/providers.py` | [núcleo] | Capa multi-proveedor: Anthropic/OpenAI/Google/local, con fallback simulado. |

## Configuración

| Ruta | Qué hace |
|------|----------|
| `config.json` | Fuente única de perfiles (agentes/unidades), `wip_limit`, columnas. |
| `settings.json` | Lectura preaprobada (`allow`) y tools con efectos (`ask`). |
| `mcp.example.json` | Plantilla de MCP por dominio (copia a `.mcp.json`, que está ignorado). |
| `agents/*.md` | Subagentes especialistas por rol (auditor, implementer, verifier, documenter). |
| `commands/*.md` | Comandos del plugin: `/board` y `/setup` (asistente de configuración). |
| `skills/board-workflow/SKILL.md` | Skill de flujo del tablero. |

## Scripts

| Ruta | Qué hace |
|------|----------|
| `scripts/validate_config.py` | Valida `config.json`/`policy.json`/`models.json` (usado en CI). |
| `scripts/analyze_decisions.py` | Agrega decisiones humanas por unidad/departamento y exporta dataset `{contexto,decisión}` (JSONL). Modo multi-log (federado). |
| `scripts/forward_audit.py` | Reenvía la cadena de una unidad al central (`--to-dir`/`--to-url`). |

## Demos y tableros [demos]

| Ruta | Qué hace |
|------|----------|
| `index.html` (raíz) | Redirección a `demos/index.html` (para GitHub Pages). |
| `demos/index.html` · `.en.html` | Landing (ES/EN). |
| `demos/board-demo.html` · `.en.html` | Demo simulado del tablero de agentes (ES/EN). |
| `demos/como-funciona.html` · `how-it-works.en.html` | Recorrido de adopción (ES/EN). |
| `board/agent-board.html` | Tablero operativo (simulado / en vivo / offline). |
| `board/capital-board.html` · `.en.html` | Capital Board de una unidad (ES/EN). |
| `board/capital-central.html` · `.en.html` | Capital Central de la flota federada (ES/EN). |

> La presentación (`demos/presentation*.html`) es **solo local**: está en `.gitignore` y no se publica.

## Documentación [docs]

| Ruta | Qué hace |
|------|----------|
| `README.md` | Portada: qué es, quickstart, uso, auditoría, federación. |
| `INSTALL.md` | Instalación (local, GitHub, `.plugin`) y arranque. |
| `THREAT_MODEL.md` | Modelo de amenazas: vías de bypass y mitigaciones. |
| `SECURITY.md` | Reporte privado de vulnerabilidades. |
| `CONTRIBUTING.md` | Cómo contribuir. |
| `CHANGELOG.md` | Historial de versiones. |
| `docs/PRODUCTION_PLAN.md` | Plan a producción. |
| `docs/adr/*.md` | 12 ADRs (decisiones de arquitectura) + índice. Registro de diseño. |
| `examples/` | Orquestador multi-modelo + plantillas de perfiles (dev, legal, finanzas, soporte-it). |

## Desarrollo / CI [dev]

| Ruta | Qué hace |
|------|----------|
| `tests/*.py` | Tests del núcleo (binding, cuotas, auditoría, coste, decorado, proveedores). |
| `.github/workflows/validate.yml` | CI: valida JSON/config, compila, corre tests. |
| `.github/workflows/pages.yml` | Publica las demos en GitHub Pages. |
| `.github/ISSUE_TEMPLATE/`, `pull_request_template.md` | Plantillas de issues/PR. |
| `.claude-plugin/plugin.json` · `marketplace.json` | Metadatos del plugin/marketplace. |

## No se versiona (ver `.gitignore`)

Estado en runtime (`board/*-state.json`), auditoría generada (`mcp/gate-audit.log`),
`__pycache__/`, `.DS_Store`, `*.log`, artefactos (`*.plugin`, `*.zip`), la presentación
(`demos/presentation*.html`), el offset del reenviador (`*.fwd-offset`), la config MCP real
(`.mcp.json`) y los entregables sueltos (`blog-*.md`).
