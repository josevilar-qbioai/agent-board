# Agent-Board — Plataforma de Supervisión Multi-Agente

## Propietario
Jose Antonio Vilar Sanchez
- Afiliación: Independent Researcher
- Trabajo: IT en Universidad Politécnica de Madrid (UPM)
- Email académico: qmetrika@upm.es
- Email personal: javsprivate@gmail.com
- GitHub: https://github.com/josevilar-qbioai
- Repo público: https://github.com/josevilar-qbioai/agent-board

---

## Qué es este proyecto

Agent-Board es una **plataforma genérica** de supervisión y gobernanza para agentes
autónomos. Es una línea de desarrollo propia de QMetrika, pero diseñada para ser
**independiente de dominio**: cualquier empresa, departamento o proyecto puede usarla
sin modificar el código — solo editando `config.json` y `mcp/policy.json`.

### Relación con QMetrika

Agent-Board y QMetrika-Plataforma-Bio-IA son **dos líneas de desarrollo del mismo
autor**, no una dependencia externa:

```
QMetrika (organización)
├── Agent-Board          ← ESTE REPO: plataforma genérica de gobernanza
│   └── github.com/josevilar-qbioai/agent-board
│
└── QMetrika-Bio-IA      ← Caso de uso: genómica clínica + mRNA terapéutico
    ├── platform/agent-board/   ← git submodule apuntando a ESTE repo
    ├── product/                ← personalización QMetrika (config, policy, threat model)
    └── pipelines/shared/       ← orchestrator que conecta ambas capas
```

**QMetrika consume Agent-Board como submodule** en `platform/agent-board/`. Las mejoras
que se hagan aquí llegan a QMetrika con:
```bash
cd QMetrika-Plataforma-Bio-IA/platform/agent-board
git pull origin main
cd ../..
git add platform/agent-board
git commit -m "Update agent-board submodule"
```

### Lo que es genérico (vive AQUÍ) vs lo que es específico (vive en QMetrika)

| Aquí (agent-board) | En QMetrika (product/) |
|---------------------|------------------------|
| Tablero Kanban (HTML) | Columnas y agentes del pipeline genómico |
| Broker de aprobación | Políticas RBAC para herramientas clínicas |
| MCP Gate + @gated decorator | Modelo de amenazas de genómica clínica |
| Auditoría hash-chain | board_bridge.py (mapeo pipeline → tablero) |
| Cliente universal (agentboard_client.py) | Wrapper con unit/profile (agentboard_client.py) |
| Sistema de cuotas y coste | — |
| Perfiles y swimlanes por departamento | — |
| Plantillas de dominio (dev, legal, finanzas) | — |

**Regla:** si una funcionalidad sirve para cualquier proyecto, va aquí. Si es
específica de genómica/mRNA/variantes, va en QMetrika.

---

## Repo de GitHub

- **URL:** https://github.com/josevilar-qbioai/agent-board
- **Visibilidad:** Público
- **Licencia:** MIT
- **GitHub Pages:** https://josevilar-qbioai.github.io/agent-board/

### Publicar cambios

Después de hacer cambios localmente:
```bash
cd agent-board/        # dentro de la carpeta del proyecto
git add -A
git commit -m "descripción del cambio"
git push origin main
```

### Propagar cambios a QMetrika

Después del push, actualizar el submodule en QMetrika:
```bash
cd QMetrika-Plataforma-Bio-IA/platform/agent-board
git pull origin main
cd ../..
git add platform/agent-board
git commit -m "Update agent-board submodule: descripción breve"
```

---

## Estructura del proyecto

```
agente-kanban-board/           # directorio local de desarrollo
└── agent-board/               # contenido del plugin
    ├── board/                 # tablero HTML (Kanban + Capital Board + Central)
    ├── hooks/                 # broker.py (coordinación) + hook.py (Claude Code)
    ├── client/                # agentboard_client.py (adaptador universal)
    ├── mcp/                   # gate, policy, audit, quota, cost, canonical
    ├── agents/                # prompts de rol (auditor, implementer, verifier, documenter)
    ├── commands/              # /board, /setup
    ├── skills/                # board-workflow SKILL.md
    ├── scripts/               # validate_config, analyze_decisions, forward_audit
    ├── examples/              # perfiles, multi_model_orchestrator
    ├── demos/                 # landing page para GitHub Pages
    ├── tests/                 # binding, cuotas, auditoría, lint
    ├── docs/                  # PRODUCTION_PLAN, ADRs, REPO_MAP
    ├── config.json            # configuración por defecto / plantilla
    ├── settings.json          # tools ask/allow
    └── .claude-plugin/        # metadata del plugin
```

---

## Componentes clave

### Broker (`hooks/broker.py`)
Servidor HTTP local (`:8787`) que coordina la aprobación de doble vía. Mantiene
estado persistido en disco (atómico). Endpoints:

| Endpoint | Método | Quién lo usa | Requiere token |
|----------|--------|-------------|----------------|
| `/api/state` | GET | Tablero (polling) | No |
| `/api/event` | POST | Agente (ciclo de vida) | No |
| `/api/request` | POST | Agente (solicita gate) | No |
| `/api/decision` | GET | Agente (consulta gate) | No |
| `/api/decide` | POST | Operador (aprueba/deniega) | Sí |
| `/api/account` | POST | Agente (contabilidad coste) | No |
| `/api/reset` | POST | Operador (limpia estado) | Sí |
| `/api/purge-stale` | POST | Operador (limpia tarjetas fantasma) | Sí |
| `/api/config` | GET | Tablero (perfiles) | No |

### Cliente universal (`client/agentboard_client.py`)
~140 LOC, sin dependencias. Tres interfaces: ciclo de vida (start/step/stop),
gate (bloquea hasta aprobación), y account_llm (presupuesto). Compatible con
cualquier runtime de LLM.

### Gate determinista (`mcp/agentboard_gate.py`)
Decorador `@gated` para tools MCP. La decisión es código (policy.json), no
criterio del modelo. Fail-closed por defecto.

### Auditoría (`mcp/audit.py`)
Cadena hash-encadenada append-only. Cada entrada liga con la anterior. Verificable
con `python3 mcp/audit.py verify`. Las decisiones del operador incluyen unit/profile
para análisis por departamento.

---

## Tareas pendientes / Roadmap

### Corto plazo
- Mejorar documentación de perfiles en `examples/profiles/`
- Tests de integración para `/api/purge-stale`
- Documentar flujo de federación con ejemplo real

### Medio plazo
- WebSocket para el tablero (reemplazar polling HTTP)
- Dashboard de análisis de decisiones humanas (visualización)
- SDK para TypeScript/Node (además de Python)

### Largo plazo
- Políticas aprendidas del dataset de decisiones humanas
- Marketplace de plantillas de dominio
- Integración con sistemas de gestión de incidentes

---

## Errores conocidos

### Tarjetas fantasma en modo live
Si un pipeline se interrumpe abruptamente (Ctrl+C, crash), la tarjeta puede
quedarse en "working" permanentemente. Solución: `POST /api/purge-stale`
con `max_age_s` o el botón 🧹 Purge en la UI.

### Reset en modo live
El botón Reset limpia el estado local del navegador pero el broker sigue sirviendo
tarjetas por `/api/state`. Usar `POST /api/reset` con token de operador para
limpiar ambos lados, o el botón Reset del tablero en modo live (que ya envía el POST).

---

## Convenciones de desarrollo

- **Sin dependencias externas** — solo stdlib de Python 3.8+
- **Fail-closed** — si algo falla, se deniega (nunca se aprueba por defecto)
- **Un fichero = una responsabilidad** — broker, gate, audit, quota, cost separados
- **Lo genérico aquí, lo específico fuera** — este repo no debe tener código de QMetrika
- **ADRs para decisiones importantes** — en `docs/adr/`
- **Tests para seguridad** — binding, cuotas, auditoría en `tests/`
