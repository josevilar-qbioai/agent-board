# 0012 — Empaquetado y despliegue

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0001](0001-niveles-de-despliegue.md), [0003](0003-persistencia-y-estado.md), [0005](0005-tiempo-real-sse.md)

## Contexto

Hoy el proyecto se distribuye como **plugin de Claude Code** (marketplace + `plugin.json`)
y se ejecuta con `python3 hooks/broker.py`. La lista recomienda, para v1: backend
FastAPI (o NestJS), frontend React + Tailwind + dnd, Docker + docker-compose para
self-host fácil, y Helm para K8s. Hay que decidir qué adoptar sin romper ni el plugin
ni el nivel Solo.

## Decisión

**Backend**
- Conservar el **broker stdlib** como camino del nivel Solo (sin dependencias).
- Migrar a **FastAPI** *cuando* haga falta async real, validación de esquemas y SSE
  robusto (previsiblemente al construir el proxy MCP, ADR-0002) — **manteniendo el
  contrato HTTP** (`/api/event`, `/api/request`, `/api/decision`, `/api/decide`,
  `/api/state`, nuevo `/api/stream`). No se elige **NestJS**: el núcleo y el ecosistema
  (gate, cliente, MCP) son Python; un segundo lenguaje fragmentaría el proyecto.

**Frontend**
- El tablero actual es **HTML de un fichero** servido por el broker: excelente para
  Solo (cero build). Se mantiene como modo embebido.
- Para la UX rica (swimlanes, filtros, modal de aprobación, métricas — ADR-0005) se
  construye un frontend **React + Tailwind** con una librería de drag-and-drop
  (`@hello-pangea/dnd`), compilado a estáticos que el mismo broker sirve. Sin servidor
  de frontend separado en Solo/Team.

**Despliegue**
- **Dockerfile + docker-compose** como camino self-host de primera clase (nivel Team):
  un servicio por defecto; perfiles de Compose para añadir Postgres/OIDC/OTel
  opcionales. Esto cubre la inmensa mayoría del self-host.
- **Helm chart** solo en nivel **Scale**, cuando haya usuarios que desplieguen en K8s.
  No es día 1.
- Se mantiene la **distribución como plugin** de Claude Code en paralelo: son públicos
  distintos (dev individual vs. equipo self-host).

## Consecuencias

**Positivas**
- Tres formas de consumir el proyecto sin contradecirse: plugin (dev), Compose
  (equipo), Helm (escala) — cada una en su nivel (ADR-0001).
- Un solo lenguaje de núcleo (Python) reduce fricción de contribución OSS.
- El contrato HTTP estable permite cambiar el backend por dentro sin romper clientes.

**Negativas / coste**
- Mantener el tablero embebido **y** el frontend React es doble trabajo de UI; se
  mitiga compartiendo el contrato de eventos SSE y dejando el embebido como "modo
  básico".
- La migración a FastAPI hay que hacerla preservando comportamiento (tests de contrato
  HTTP antes de migrar).

## Alternativas descartadas

- **NestJS / backend en Node**: segundo lenguaje, fragmenta el proyecto Python.
- **Reescribir a FastAPI ya**: prematuro; el stdlib aún sirve y la prioridad es Fase 0
  (seguridad), no el framework.
- **Helm/K8s de día 1**: complejidad sin demanda; Compose cubre el self-host real.
- **SPA servida aparte (Vercel/Netlify)**: rompe el self-host de un proceso.
