# Plan de QA - Inventario Físico (inv.oscomunidad.com)

**Fecha:** 2026-03-31
**Objetivo:** Revisar cuidadosamente la aplicación web y móvil de inventario para detectar posibles errores, bugs de UI, y validar navegación/funciones, sin alterar datos de producción (modificaciones no destructivas).

## Checklist de Tareas

- [ ] Tarea 1: Obtener acceso (login) al sistema.
- [ ] Tarea 2: QA Desktop (Web)
  - [ ] Verificar login y redirección.
  - [ ] Revisar menú y estructura principal.
  - [ ] Validar flujos de lectura y navegación drill-down.
  - [ ] Revisar consistencia con MANUAL_ESTILOS.md (botones, colores, typography).
- [ ] Tarea 3: QA Móvil
  - [ ] Validar responsividad de tablas y menús.
  - [ ] Revisar experiencia táctil y visibilidad de los modales.
- [ ] Tarea 4: Documentar hallazgos en `.agent/QA_REGISTRO.md`.

## Tareas para Antigravity
- Ejecutar QA web y móvil usando `browser_subagent`.
- Tomar capturas de errores y registrarlas en `screenshots_temporales/`.
- Documentar bugs encontrados.
