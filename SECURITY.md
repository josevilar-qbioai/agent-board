# Política de seguridad

agent-board es una herramienta de **gobernanza**: su valor depende de que la puerta no
se pueda esquivar. Nos tomamos los reportes en serio.

## Reportar una vulnerabilidad

**No abras un issue público.** Usa uno de estos canales privados:

- GitHub → pestaña **Security** → *Report a vulnerability* (advisory privado).
- O correo a **qmetrika@proton.me** con el asunto `[security] agent-board`.

Incluye: descripción, impacto, pasos para reproducir y versión afectada
(`.claude-plugin/plugin.json` → `version`). Intentaremos responder en un plazo
razonable y te daremos crédito si lo deseas.

## Alcance

Antes de reportar, mira el [THREAT_MODEL.md](THREAT_MODEL.md): enumera las vías por las
que una acción podría colarse sin pasar por la puerta y su estado (incluido /
responsabilidad del integrador / por endurecer). Ten en cuenta los **no-objetivos**
documentados allí:

- La puerta gobierna las **acciones que pasan por la tool**, no lo que el modelo dice o
  razona, ni efectos por canales ajenos a tu servidor MCP.
- No sustituye al RBAC ni protege frente a un host ya comprometido (se asume integridad
  del proceso y del transporte).

Reportes especialmente valiosos: formas de **ejecutar una operación con efectos sin pasar
por la política** (bypass del invariante), romper el binding de aprobación, falsear la
cadena de auditoría, o evadir las cuotas/presupuestos.

## Versiones

Se da soporte a la última versión publicada. Ver [CHANGELOG.md](CHANGELOG.md).
