# 0003 — Persistencia y estado

- Estado: **aceptado**
- Fecha: 2026-06-19
- Decisores: mantenedores
- Relacionado: [0001](0001-niveles-de-despliegue.md), [0005](0005-tiempo-real-sse.md), [0008](0008-rate-limiting-y-cuotas.md)

## Contexto

`broker.py` mantiene todo el estado en memoria y lo vuelca a un único fichero JSON de
forma atómica (`os.replace`), con un *flusher* en background cada ~1s y flush inmediato
en decisiones. Esto es elegante para el nivel Solo, pero:

- Asume un **único escritor**; no soporta varios procesos/operadores.
- No hay consultas (auditoría, métricas, cuotas por ventana) más allá de cargar todo.
- El crecimiento del JSON degrada el flush completo.

La lista pide "Postgres + Redis". Aplicando el [ADR-0001](0001-niveles-de-despliegue.md),
no lo hacemos requisito.

## Decisión

Introducir una interfaz **`Store`** que abstrae tarjetas, decisiones y contadores
agregados, con tres implementaciones:

- **SQLite** (nuevo **default**): sustituye al JSON. Un fichero, cero servicios,
  transacciones reales, índices, consultas para auditoría/métricas/cuotas, soporta
  varios lectores y escritura serializada con WAL. Cubre Solo y Team pequeño.
- **Memoria**: para tests y efímero.
- **Postgres** (opcional, nivel Scale): mismo contrato; habilita multi-operador real,
  concurrencia alta y retención larga.

**Redis** se trata como **bus/colas opcional** (ver [ADR-0005](0005-tiempo-real-sse.md)),
no como almacén primario. En Solo/Team el bus es in-process; en Scale, Redis pub/sub
para fan-out de eventos entre réplicas.

Migración del estado JSON actual a SQLite con un script idempotente; el formato de las
tarjetas (`sid`, `id`, `col`, `kind`, `tokens`…) se conserva.

## Consecuencias

**Positivas**
- SQLite da el 90% de lo que aportaría Postgres sin operar un servicio.
- Las consultas habilitan métricas en tarjeta (ADR-0005) y cuotas (ADR-0008) sin
  recorrer todo el estado.
- El contrato HTTP (`/api/state`, `/api/decision`, `/api/decide`) no cambia.

**Negativas / coste**
- SQLite con muchos escritores concurrentes requiere cuidado (WAL, timeouts).
- Mantener dos+ implementaciones del `Store` y probarlas con un test de contrato.

## Alternativas descartadas

- **Seguir solo con JSON**: no soporta consultas ni multi-operador.
- **Postgres como default**: rompe el nivel Solo (ADR-0001).
- **Redis como almacén primario**: volátil por defecto; mal encaje como fuente de
  verdad de auditoría.
