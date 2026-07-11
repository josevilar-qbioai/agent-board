# Integración Agent-Board ↔ QMetrika Pipeline

**Fecha:** 2026-07-10  
**Estado:** Implementado  
**Repos:** `agent-board` (este) + `QMetrika-Plataforma-Bio-IA`

---

## Qué es

La primera integración real de Agent-Board con un pipeline multi-agente de producción. El orchestrator de QMetrika (clasificación de variantes genéticas) se conecta al broker HTTP para ejecutar un pipeline de 9 pasos con gates humanos, tarjetas Kanban en tiempo real, y auditoría hash-chain de las decisiones del PI.

Esta integración demuestra que Agent-Board no es un demo sino un sistema de gobernanza funcional para aplicaciones de genómica clínica.

---

## Componentes involucrados

### En el repo QMetrika

| Fichero | Función |
|---------|---------|
| `pipelines/shared/orchestrator.py` | Runner del pipeline (flag `--live` para broker) |
| `pipelines/shared/board_bridge.py` | Puente orchestrator → AgentBoard client |
| `pipelines/shared/agentboard_client.py` | Copia local del adaptador universal |
| `pipelines/L1-classification/config.json` | 9 pasos, 6 agentes, gate humano |

### En este repo (Agent-Board)

| Fichero | Función |
|---------|---------|
| `hooks/broker.py` | Servidor HTTP (:8787) |
| `board/agent-board.html` | Tablero Kanban visual |
| `mcp/audit.py` | Cadena hash-chain |
| `mcp/policy.json` | RBAC + cuotas |
| `mcp/models.json` | Precios por modelo (€/Mtok) |
| `client/agentboard_client.py` | Cliente genérico (fuente canónica) |

---

## Cómo funciona

```bash
# Terminal 1: broker
python hooks/broker.py
# → TOKEN de operador: xyz123

# Terminal 2: pipeline
cd QMetrika/pipelines/shared
python orchestrator.py --pipeline L1-classification --gene BRCA1 --live
```

El orchestrator crea una tarjeta por cada paso del pipeline. Cuando llega al gate de validación (paso 6 de 9), la tarjeta cae a "Needs Input" y el pipeline se bloquea. El PI pulsa Aprobar/Denegar en el tablero. La decisión se registra en `gate-audit.log` con el payload completo vinculado por hash.

---

## Mapeo de agentes

Los agentes del pipeline L1 de QMetrika se mapean a los roles de Agent-Board:

| Agente QMetrika | Rol Agent-Board | Modelo | Permisos |
|----------------|-----------------|--------|----------|
| data-curator | `auditor` | haiku | Read-only |
| computational-analyst | `implementer` | local | Read+Write |
| ml-engineer | `implementer` | local | Read+Write |
| statistical-reviewer | `verifier` | opus | Read-only (adversarial) |
| scientific-writer | `documenter` | sonnet | Solo docs |
| literature-scout | `auditor` | sonnet | Read-only |

El mapeo está definido en `board_bridge.py:AGENT_KIND_MAP`.

---

## Lo que valida

Esta integración valida las siguientes capacidades de Agent-Board:

1. **Observabilidad en tiempo real** — tarjetas avanzando por columnas durante la ejecución del pipeline
2. **Gates via broker HTTP** — bloqueo hasta decisión del operador, no ficheros JSON manuales
3. **Payload binding (ADR-0007)** — la aprobación está vinculada al hash del resultado exacto
4. **Auditoría hash-chain (ADR-0006)** — cadena tamper-evident verificable por terceros
5. **Multi-modelo** — haiku ($0.25/M) para curación, local ($0) para cómputo, opus ($15/M) solo para verificación
6. **Control de coste** — cuotas en € por hora aplicadas a modelos fundacionales
7. **RBAC por agente** — cada rol tiene permisos diferentes definidos en policy.json
8. **Unidades/departamentos** — los pasos se clasifican por unidad (Genómica, Terapéutica, Oncología)

---

## Implicación para el producto

Esta integración es el prototipo del producto final (Agent-Board Clínico). La transición investigación → producto implica cambiar:
- Datos de investigación → VCF de pacientes reales
- PI como operador → genetista clínico
- `gate-audit.log` local → almacenamiento 21 CFR Part 11
- `agent-board.html` local → instancia desplegada SaMD

El código base es el mismo. La documentación completa del modelo de producto está en `QMetrika/docs/negocio/PRODUCTO_TABLERO_CLINICO.md`.

---

## Referencia

- Documentación técnica completa: `QMetrika/docs/tecnico/INTEGRACION_TABLERO_REAL.md`
- Agent Canvas de los agentes: `docs/AGENT_CANVAS_ROBIN.md`
- Pipeline config: `QMetrika/pipelines/L1-classification/config.json`
