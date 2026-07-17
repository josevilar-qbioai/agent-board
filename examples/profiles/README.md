# Plantillas de perfiles

Perfiles de proyecto listos para copiar. Cada `.json` es el valor que va bajo
`profiles.<clave>` en `config.json`. Cambia nombres/modelos a tu gusto.

| Fichero | Dominio | Especialistas |
|---|---|---|
| `dev.json` | Desarrollo de software | auditor, explorer, implementer, documenter, verifier |
| `legal.json` | Legal | analista de contratos, jurisprudencia, redactor, revisor |
| `finanzas.json` | Finanzas | analista, riesgo, conciliaciones, informes, auditor |
| `soporte-it.json` | Soporte IT | clasificador, diagnóstico, runbooks, KB, revisor de cierre |

Además, `config.json` ya trae `default` y `biocomputacion` (genómica) de ejemplo.

## Cómo usarlo

1. Abre el fichero de la plantilla más cercana a tu caso.
2. Cópialo dentro de `profiles` en `config.json` con la clave que quieras, p. ej.:

   ```json
   "profiles": {
     "soporte": { ...contenido de soporte-it.json... }
   }
   ```

3. Ponlo como `active_profile` o ábrelo con `?profile=soporte` en el tablero.

O deja que el asistente lo haga por ti: en Claude Code ejecuta **`/setup`**.

## Anatomía de un especialista

```json
{ "id": "resolutor", "label": "Ejecutor de Runbooks", "color": "#33d1c9",
  "role": "effect", "unit": "Resolución", "model": "gpt-4o",
  "jobs": ["Reiniciar servicio", "Aplicar parche"] }
```

- **role** (flujo, independiente del dominio): `read` (analiza, sin efectos) ·
  `effect` (opera con efectos → puerta humana → review) · `verify` (verificador
  adversarial) · `write` (escribe entregables, allow por política).
- **unit**: departamento/equipo (para filtrar y para los carriles/swimlanes).
- **model**: modelo por defecto; el coste y la clase (local/fundacional) salen de
  `mcp/models.json`.
- **jobs**: tareas de ejemplo para el demo simulado (en modo en vivo las tareas
  reales las pone tu orquestador).

> Consejo: pon los agentes de análisis (`read`) en modelos **locales** (~gratis) y
> reserva los **fundacionales** (caros) para el trabajo con efectos. Así el WIP de
> coste y el KPI de coste por tarea trabajan a tu favor.
