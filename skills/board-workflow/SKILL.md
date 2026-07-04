---
name: board-workflow
description: Patron reproducible para abordar un proyecto con un dynamic workflow visible en un tablero Kanban de agentes, con puerta de aprobacion humana sobre cualquier operacion de escritura o con efectos secundarios. Usalo cuando una tarea sea grande, paralelizable, adversarial o de auditoria a escala (migraciones, refactors, barridos de catalogar-y-clasificar, auditorias). Disparalo con "workflow", "ultracode" o /board-workflow.
---

# board-workflow

Plantilla, no guion. Adapta el harness al caso concreto; no lo ejecutes literal.

## Cuando aplicarlo
Tareas demasiado grandes para una sola pasada, donde quieres ver el progreso de
los agentes y controlar las operaciones con efectos. Si es un cambio de 20 lineas,
NO uses esto: el modo normal sobra.

## Forma del workflow (orquestador)
Un `claude` de nivel superior lanza N tareas. Cada tarea sigue:
**implementer -> 2 verifiers adversariales -> fixer**, y solo se cierra cuando
los verifiers pasan. Reparte el trabajo por unidades independientes (ficheros,
modulos, registros, items del catalogo) y maximiza el paralelismo.

Agentes incluidos en el plugin:
- `auditor`  (solo lectura) para inventario/descubrimiento/deteccion.
- `implementer` (worktree) para cambios aislados.
- `verifier` (distinto del autor) para la verificacion adversarial.

## Regla de oro de gobernanza (configurable por proyecto)
1. **Lectura por defecto.** El descubrimiento, inventario y deteccion van con el
   agente `auditor`, que no puede escribir.
2. **Toda operacion con efectos pasa por la puerta humana.** Borrar, modificar,
   desplegar, enviar, rotar o cualquier accion irreversible NO se ejecuta de forma
   autonoma: se propone y queda pendiente de aprobacion (columna Needs Input del
   tablero), enrutada por el hook PermissionRequest.
3. **Auto mode SI, pero solo sobre tools de lectura preaprobadas.** Las tools con
   efectos siguen pidiendo permiso aunque el workflow corra desatendido.

Que cuenta como "operacion con efectos" depende de tu proyecto: defínelo en
`config.json` (campo `gated_tools`) y en `settings.json` (lista `ask`).

## Tablero (observabilidad)
Los hooks del plugin proyectan el ciclo de vida de cada agente sobre
`board/board-state.json`. Abre el tablero con `/board`. No narres esto al
usuario; simplemente trabaja y deja que el tablero refleje el estado.

## Presupuesto
Los workflows consumen muchos tokens. Pon un techo explicito cuando proceda
("usa 50k tokens") y reserva esto para los trabajos que de verdad lo justifican.

## Gotchas
- Si un verifier es el mismo contexto que el autor, el sesgo auto-preferencial
  arruina la verificacion: usa SIEMPRE el agente `verifier` aparte.
- Tras compactar contexto, la deriva de objetivo borra restricciones del tipo
  "no toques X": mantenlas en el brief de cada subagente, no solo en el global.
- Los nombres de campo del payload de los hooks pueden variar entre versiones;
  si el tablero no se actualiza, revisa `hooks/emit_card.py` (ver README).
