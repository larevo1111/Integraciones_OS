# Catálogo de Skills — Integraciones_OS

> **Índice de todas las skills disponibles para los agentes (Antigravity, Claude Code, Codex).**
> Antes de intentar realizar una tarea nueva (especialmente de conexiones, despliegue o IA), **SIEMPRE** revisa este catálogo para no reinventar la rueda y evitar errores graves documentados.

---

## 🧠 Skills Generales Estandarizadas (`.agent/skills/`)
Skills de arquitectura abstracta y reglas de negocio obligatorias.

| Nombre de la Skill | Archivo Físico | Descripción | Regla Crítica |
|--------------------|----------------|-------------|---------------|
| **Servicio Central de IA** | `.agent/skills/manejo_ia.md` | Arquitectura completa del ia_service_os: agentes, enrutamiento, resumen vivo, consumo. Sirve a todos los proyectos OS. | **Regla de los 3 Pasos (Anti-Alucinaciones):** 1. Generar SQL 2. Ejecutar SQL 3. Responder con datos reales. NUNCA inventar cifras. |

---

## 🤖 Comandos Interactivos para Claude Code (`.claude/commands/`)
Estos son "skills" en formato de slash-commands (`/nombre-skill`) nativos para Claude Code, enfocados en ejecución directa.

| Comando | Archivo Físico | Enfoque Principal |
|---------|----------------|-------------------|
| `/ia-service` | `.claude/commands/ia-service.md` | Operar el Servicio Central de IA: consultar, configurar agentes, monitorear consumo, agregar keys. |
| `/playwright-effi` | `.claude/commands/playwright-effi.md` | Trucos y selectores para hacer scraping de los exports de Effi usando Playwright. |
| `/effi-database` | `.claude/commands/effi-database.md` | Mapas estructurales para consultar y hacer JOINs en las 41 tablas `zeffi_*` y tablas analíticas. |
| `/effi-negocio` | `.claude/commands/effi-negocio.md` | Reglas duras de ventas: Vigencia, Mapeo de canales, y Atribución de Consignaciones. |
| `/telegram-pipeline`| `.claude/commands/telegram-pipeline.md` | Variables asíncronas para disparar alertas del estado del orquestador Python. |
| `/espocrm-integracion` | `.claude/commands/espocrm-integracion.md` | Flujo de normalización de la sincronía bidireccional Effi <-> EspoCRM. |

---

> **⚠️ REGLA DE ACTUALIZACIÓN:** Si un agente de IA (Claude Code o Antigravity) resuelve un problema complejo nuevo de infraestructura, conexión a una Base de Datos, o establece un patrón de arquitectura novedoso, tiene la **obligación** de documentarlo como un `.md` en `.agent/skills/` y agregar la fila correspondiente en este catálogo ANTES de terminar su tarea.
