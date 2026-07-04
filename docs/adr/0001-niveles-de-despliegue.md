# 0001 — Niveles de despliegue (Solo / Team / Scale)

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: todos los ADRs siguientes; [PRODUCTION_PLAN.md](../PRODUCTION_PLAN.md)

## Contexto

La lista de mejoras hacia producción propone Postgres, Redis, OPA, OIDC, OTel,
Prometheus/Grafana y Helm. Cada pieza es razonable, pero juntas convierten un proyecto
que hoy arranca con `python3 broker.py` y **cero dependencias** en algo que exige una
plataforma. El objetivo declarado es **OSS serio y self-hostable**, donde la barrera
de entrada baja es la principal palanca de adopción. Necesitamos una regla que permita
incorporar todo eso sin perder el arranque trivial.

## Decisión

Definimos **tres niveles de despliegue** y exigimos que el nivel base siga siendo
mínimo:

- **Solo** (por defecto): un único proceso, almacenamiento embebido (SQLite/JSON),
  sin servicios externos, sin red saliente. Es el que se prueba en CI y el que un dev
  ejecuta en local. **Nunca puede requerir Postgres, Redis, OPA ni un IdP.**
- **Team**: Docker Compose. Postgres y OIDC **opcionales**, activados por config.
- **Scale**: Helm/K8s, Postgres + Redis, OTel, SSO/SIEM. Para quien lo necesite.

Toda capacidad pesada entra **detrás de una interfaz** (`Store`, `Decider`,
`AuditSink`, bus de eventos) con una implementación embebida por defecto y un
adaptador externo opcional. Un cambio que rompa el nivel Solo se rechaza o se
rediseña como adaptador.

## Consecuencias

**Positivas**
- Se conserva la ventaja de adopción (instalar y usar en minutos).
- El núcleo y los tests son los mismos en los tres niveles; los adaptadores se prueban
  con un test de contrato común.
- La documentación puede ofrecer un "quickstart" honesto sin asteriscos.

**Negativas / coste**
- Disciplina de diseño: cada feature debe pensar su versión embebida primero.
- Algún adaptador pesado puede ir por detrás en features respecto al embebido.

## Alternativas descartadas

- **Asumir Postgres+Redis desde el principio** (como sugiere la lista): más simple de
  programar, pero mata el self-host trivial y la adopción OSS.
- **Solo embebido, sin caminos de escala**: limita el techo del proyecto y obliga a
  fork para uso serio en equipo.
