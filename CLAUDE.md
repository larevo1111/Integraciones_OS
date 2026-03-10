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

## Convenciones del proyecto

- Scripts en `scripts/` — corren con `node` o `python3` directamente en el host
- MariaDB: `mysql -u osadmin -pEpist2487. effi_data -e "..." 2>/dev/null`
- Git: commit + push sin preguntar, con mensaje descriptivo en español
- Skills disponibles: `/effi-database`, `/effi-negocio`, `/playwright-effi`, `/telegram-pipeline`
- Memoria del proyecto: `.claude/projects/.../memory/MEMORY.md`

## Estilo de respuesta

- Conciso y directo — sin preámbulos ni relleno
- Actúa primero, reporta después
- Si algo falla, diagnostica la causa antes de reintentar
