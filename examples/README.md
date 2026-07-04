# Ejemplos por proyecto

Cada subcarpeta es una adaptacion del harness a un dominio concreto. Un ejemplo
contiene tipicamente:

```
examples/<proyecto>/
├── config.json        # wip, gated_tools, routing del proyecto
├── jobs.sample.json   # pool de tareas representativas del dominio
└── README.md          # que hace este proyecto y que operaciones se gatean
```

Para crear el tuyo: copia este esqueleto, rellena `gated_tools` con lo que en
tu dominio tiene efectos irreversibles, y ajusta `settings.json` (lista `ask`)
para que esas operaciones pasen por la puerta humana.

Plantilla minima de `config.json`:

```json
{
  "project": "mi-proyecto",
  "wip_limit": 5,
  "gated_tools": ["Write", "Edit", "Bash", "mcp__mi-servicio__delete"],
  "approval_routing": "claude-code"
}
```
