# Changelog

## 0.17.0 — config fácil (OSS)
- Asistente `/setup` (comando): genera config.json + policy.json de forma guiada
  (proyecto, especialistas/unidades, tools con efectos, presupuestos), sin editar JSON.
- Validador `scripts/validate_config.py` (+ CI): comprueba config/policy/models con
  mensajes claros (role inválido, unidad inexistente, id duplicado, modelo sin precio…).
- Plantillas de perfiles en examples/profiles/: dev, legal, finanzas, soporte-it
  (además de default y claude-science en config.json), listas para copiar.
- README con Quickstart de 2 minutos (instala → configura → arranca).
- Repo listo para OSS: badges (CI, Python, deps=0, MIT), .gitignore ampliado,
  plantillas de issue (bug/idea) y de pull request, y SECURITY.md (reporte privado de
  vulnerabilidades + alcance, ligado al THREAT_MODEL).
- Demos en GitHub Pages: workflow .github/workflows/pages.yml que publica el sitio en
  cada push, index.html raíz que redirige a demos/, y .nojekyll. Las demos quedan
  visibles en https://josevilar-qbioai.github.io/agent-board/ sin instalar nada.

## 0.16.0 — swimlanes por unidad/departamento
- Vista de carriles en el tablero (botón "▤ Carriles"): agrupa el Kanban por unidad
  (Genómica / Terapéutica / Publicación / QA en el perfil claude-science) — cada fila
  es un departamento y las columnas son los estados. Ves y gobiernas todos los carriles
  a la vez, en vez de filtrar a uno con ?unit=. Alterna con la vista de columnas.
  Es observabilidad/gobernanza desde la estructura de la organización (no orquestación).

## 0.15.1
- Q · Capital Board: nuevo KPI "Coste por tarea" (coste agregado 30d ÷ tareas
  completadas) — la métrica que decide si el enfoque multiagente (organización de
  especialistas) compensa frente a un modelo único / router. Rejilla de KPIs a auto-fit.

## 0.15.0 — perfiles de proyecto, unidades y fuente única
- Perfiles de proyecto: config.json declara `profiles` (agentes concretos: id, label,
  color, role de flujo, unit/departamento, model). El tablero se adapta a TUS agentes;
  ejemplo real "claude-science" (Analista de Genómica, Motor Biofísico, Diseñador de
  mRNA, etc.). Selección con ?profile=<nombre>.
- Distribución por unidades/departamentos: filtro ?unit=<Departamento> (cada área ve
  sus agentes); conmutador de perfil y de unidad en la cabecera; tag de unidad por
  tarjeta. Un proyecto = un profile; un departamento = una unit.
- Fuente ÚNICA: el broker expone GET /api/config (perfiles + wip_limit + columns desde
  config.json). El tablero y el demo cargan los perfiles de ahí cuando se sirven por el
  broker; los embebidos quedan solo como fallback offline (file://). Sin duplicar.
- Refactor del flujo del tablero a roles (read/effect/verify/write) independientes del
  dominio; verificado con simulación headless en ambos tableros.

## 0.14.0 — multi-proveedor (Claude · Gemini · OpenAI · locales)
- Nueva capa client/providers.py: generate(model, prompt) despacha por el nombre del
  modelo a Anthropic / OpenAI / Google / local (OpenAI-compat u Ollama) y devuelve el
  uso REAL de tokens. Sin API keys cae a modo simulado (tokens estimados), así el
  tablero muestra agentes de todos los proveedores sin llaves; con keys, llamadas reales.
- Tokens reales en el tablero: nuevo evento 'Usage' en el broker + board.report_usage(
  sid, model, tin, tout) en el cliente. La tarjeta muestra tokens y coste € por proveedor.
- examples/multi_model_orchestrator.py reescrito: un proveedor por rol (gemini/local/
  gpt-4o/opus/sonnet), verificación cruzada entre familias, report_usage + account_llm.
- models.json: ids reales (gemini-2.0-flash, gpt-4o-mini). Test tests/test_providers.py
  (enrutado, generate simulado, report_usage e2e) + CI. Verificado e2e: agentes de los
  4 proveedores en el tablero con sus tokens.

## 0.13.0
- Nueva columna/estado "⚡ Sin presupuesto" (capped): los agentes con modelo
  fundacional frenados por el límite de coste fundacional se ven en su propia vía, en
  vez de confundirse con la cola normal. Badge ⚡ en la tarjeta y contador en el resumen.
  En el tablero (simulado + en vivo) y en el broker: cuando una cuota de COSTE deniega,
  el broker marca la tarjeta del agente como capped; al liberarse la ventana, vuelve a
  Working. Demo y README actualizados. Test en tests/test_cost.py (4a/4b).

## 0.12.0 — control de coste (no todos los tokens cuestan igual)
- Tabla de precios por modelo (mcp/models.json) + mcp/cost.py: € por (modelo, tokens)
  y clase local|foundational. Un token local (~gratis) deja de contar como uno
  fundacional (caro).
- WIP del tablero medido en COSTE: wip_limit pasa a { agents, cost_eur,
  foundational_cost_eur }. La columna Working muestra tres píldoras (agentes, € total,
  ⚡€ fundacional) y la promoción exige pasar todas. Cada tarjeta muestra su € y modelos
  variados (local vs fundacional). Controles €-WIP y ⚡€ en el tablero.
- Cuotas de coste en el broker (ADR-0008 ext): una quota puede medir en € con
  amount_field='cost_eur' y filtrar por match_class (p. ej. techo de €/hora solo en
  modelos fundacionales). quota.py lee el amount de ctx; el broker calcula cost_eur y
  model_class desde ctx.model+ctx.tokens. Ejemplo en policy.json.
- Cliente genérico: nuevo board.account_llm(model, tokens) — enforcement de coste en
  una línea antes de una llamada LLM. Devuelve True si hay presupuesto (lo contabiliza);
  si la cuota es 'ask', abre tarjeta y espera aprobación; sin broker, conservador (False).
- Tests: tests/test_cost.py (unit de cost.py + e2e de cuota de coste por clase + helper
  del cliente). CI.

## 0.11.0
- WIP multidimensional: el límite de la columna Working pasa de "nº de agentes" a
  `{ agents, tokens }` — la promoción a Working exige hueco de agentes Y de presupuesto
  de tokens en vuelo (el más restrictivo manda). El tablero muestra dos píldoras en la
  cabecera de Working (agentes y tok/presupuesto), con control deslizante tok-WIP y
  enforcement en la promoción. `config.json` documenta el formato; un número suelto
  sigue significando solo 'agents' (retrocompatible).

## 0.10.0 — cierre de Fase 0 (endurecimiento del núcleo)
- Auditoría tamper-evident (ADR-0006): nuevo mcp/audit.py, cadena append-only con hash
  encadenado (entry_hash = sha256(prev || entrada)) y lock entre procesos (flock). El
  gate y el broker auditan en la MISMA cadena; las decisiones del operador quedan
  ligadas al payload_hash. Verificador y CLI: `python3 mcp/audit.py verify`. Tests en
  tests/test_audit.py (cadena íntegra, alteración y borrado detectados, e2e del broker).
- Resumen canónico server-side (amenaza #12): el broker compone el texto que ve el
  operador (canonical_summary) desde campos validados del payload; el texto libre del
  agente pasa a "nota" secundaria en la tarjeta.
- Lint de decoración (amenaza #5): tests/test_decorated.py falla en CI si una tool
  pública no está @gated.
- Con esto Fase 0 queda cerrada: amenazas #5, #7, #8, #11, #12 implementadas y la
  auditoría es verificable.

## 0.9.0
- Cierre de la amenaza #11 (trocear para esquivar umbrales): contabilidad agregada en
  ventana deslizante (ADR-0008). Nuevo mcp/quota.py (logica pura, ventanas por
  agente/workflow/tool, precedencia deny>ask>allow). El broker carga la seccion
  "quotas" de policy.json, lleva los contadores (persistidos) y expone /api/account
  (check|commit|force). El gate @gated y el hook consultan la cuota antes del efecto:
  el limite real es el ACUMULADO, no el valor por llamada; on_exceed deny|ask;
  fail-closed si hay cuota y el broker no responde. Ejemplo de quotas en policy.json.
  Tests e2e en tests/test_quota.py + auto-comprobacion en CI.

## 0.8.0
- Cierre de la amenaza #8 (replay/race de aprobacion): la decision se liga al hash
  canonico del payload (ADR-0007). Nuevo mcp/canonical.py como fuente unica del hash.
  El broker genera req_id aleatorio (no adivinable), guarda un registro de peticiones
  con payload_hash, TTL y un solo uso; /api/decide valida el payload_hash y rechaza
  replays/caducadas/contenido distinto (409). hook, gate @gated y cliente generico
  re-verifican el hash en el punto de efecto (anti-TOCTOU). Tablero actualizado para
  aprobar por reqId+payloadHash. Tests e2e en tests/test_binding.py y CI que los corre.
- Inicio del plan a produccion: docs/PRODUCTION_PLAN.md + 12 ADRs en docs/adr/.

## 0.7.0
- Cierre de la amenaza #7: /api/decide y /api/reset exigen X-Operator-Token. El canal
  del agente (request/decision/event/state) sigue abierto; aprobar no. El token viaja
  por el fragmento de URL (terminal->navegador) y se limpia de la barra. Configurable
  con AGENT_BOARD_OP_TOKEN. Riesgo residual (agente como mismo usuario del SO)
  documentado en THREAT_MODEL.md.

## 0.6.1
- Añadido THREAT_MODEL.md: guía de gobernanza con el catálogo de vías de bypass de
  la puerta y sus mitigaciones (incluido / responsabilidad del integrador / endurecer).
  Destaca como prioritario añadir auth al endpoint /api/decide.

## 0.6.0
- MCP por dominio (genérico): policy.json unificada gobierna el servidor propio
  (@gated) y los MCP de terceros (hook PreToolUse, por el nombre mcp__srv__tool).
  Reglas por dominio con globs, plantilla mcp.example.json (un servidor = un
  dominio, 3 modos), ejemplo genérico mcp/example_tools.py. decide_rule devuelve
  None si nada casa (el hook no interfiere). Ops startswith/glob.

## 0.5.0
- Nuevo rol documenter (escribe SOLO documentacion) con su propio modelo. Reglas de
  politica para docs (write_docs/update_readme/write_changelog -> allow): la escritura
  de documentacion no pasa por la puerta humana, el codigo si. Nuevos operadores de
  politica startswith y glob para escopar por ruta.

## 0.4.1
- Ejemplo multi-modelo: binding por ROL (ROLE_MODELS) — un LLM distinto por
  explorer/auditor/implementer/verifier. La puerta determinista es independiente del
  modelo elegido.

## 0.4.0
- Opción B (puerta determinista en el servidor MCP): nuevo mcp/agentboard_gate.py
  con decorador @gated y capa de política en código (mcp/policy.json): allow/deny/ask
  por tool, condiciones ask_if/deny_if sobre el payload, restricción por rol, y
  auditoría por decisión. La puerta vive DENTRO de la tool: universal e independiente
  del LLM que la invoque. Fail-closed por defecto si no hay broker en un caso 'ask'.
- El broker muestra un 'summary' legible en la tarjeta de aprobación.
- Fix: las condiciones vacías ya no disparaban deny/ask por error.

## 0.3.0
- Agnóstico de runtime: cliente genérico (client/agentboard_client.py). Multi-modelo:
  modelo/kind/parent por tarjeta, badges por proveedor, ejemplo de orquestador.

## 0.2.1
- Persistencia del broker (volcado atómico, restauración al arrancar, /api/reset).

## 0.2.0
- Aprobación de doble vía (broker + hook PreToolUse -> permissionDecision).

## 0.1.0
- Versión inicial: skill, agentes, hooks, tablero, escrituras gated.
