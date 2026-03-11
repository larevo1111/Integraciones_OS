# Integraciones_OS — Instrucciones para Claude

## Autonomía operativa

Trabaja de forma autónoma sin pedir confirmación para:
- Editar, crear o leer archivos del proyecto
- Ejecutar scripts de Python, Node.js o Bash (export, import, pipeline)
- Consultas a MariaDB (lectura o escritura en `effi_data`)
- Comandos git: add, commit, push a main
- Comandos docker exec, docker ps, systemctl status
- Instalar dependencias con npm, pip

Solo detente y pregunta si hay riesgo irreversible fuera del proyecto:
- `DROP DATABASE`, `rm -rf` en rutas fuera de este repo
- Force push con historial perdido
- Modificar configuración de otros proyectos del servidor

## ⚠️ REGLA ABSOLUTA — FRONTEND

**Antes de crear CUALQUIER componente, vista o elemento visual del ERP:**
1. Leer `frontend/design-system/MANUAL_ESTILOS.md` — es la fuente de verdad única del diseño
2. Ver capturas en `frontend/design-system/screenshots/` para referencia visual (88 imágenes de Linear.app)
3. Seguir el manual al pie de la letra: colores, tipografía, espaciado, CSS
4. **Si el elemento NO está en el manual → DETENERSE. Preguntar a Santi y definirlo juntos antes de implementar.**
5. Una vez definido el elemento nuevo, actualizar el manual inmediatamente.

## Contexto del proyecto — leer siempre al inicio

Antes de cualquier tarea, revisar estos archivos en orden:
1. `.agent/CONTEXTO_ACTIVO.md` — estado actual del sistema, qué funciona, próximos pasos
2. `.agent/MANIFESTO.md` — visión, arquitectura, reglas técnicas aprendidas
3. `.agent/CATALOGO_SCRIPTS.md` — catálogo completo de scripts (propósito, ejecución, tablas)
4. **Para tareas frontend**: `frontend/design-system/MANUAL_ESTILOS.md` — manual de estilos obligatorio
5. Skills disponibles: `/effi-database`, `/effi-negocio`, `/playwright-effi`, `/telegram-pipeline`

## Convenciones del proyecto

- Scripts en `scripts/` — corren con `node` o `python3` directamente en el host (NO docker exec)
- MariaDB: `mysql -u osadmin -pEpist2487. effi_data -e "..." 2>/dev/null`
- Git: commit + push sin preguntar, con mensaje descriptivo en español
- Al terminar una tarea significativa: actualizar `.agent/CONTEXTO_ACTIVO.md` con el estado nuevo

## Estilo de respuesta

- Conciso y directo — sin preámbulos ni relleno
- Actúa primero, reporta después
- Si algo falla, diagnostica la causa antes de reintentar
