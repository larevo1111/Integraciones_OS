# Contexto Activo - Integraciones_OS

## Estado Actual (2026-03-06)
Pipeline Effi → MariaDB completamente funcional y automatizado.

## Lo que está funcionando

### Pipeline de datos Effi
- **21 scripts Playwright** exportan todos los módulos de Effi a `/home/osserver/playwright/exports/`
- **import_all.js** importa 34 tablas a MariaDB `effi_data` (TRUNCATE + INSERT)
- **n8n workflow activo**: corre cada 2 horas automáticamente + trigger manual
  - Nodo 1: `docker exec playwright bash /repo/scripts/export_all.sh`
  - Nodo 2: `docker exec playwright node /repo/scripts/import_all.js`

### Infraestructura
- `playwright`: imagen v1.49.1-jammy (v1.49.1 requerida por kernel 6.17)
- `n8n`: tiene docker CLI y acceso al socket para ejecutar comandos
- SSH server instalado en host (puerto 22) para conexión desde n8n
- MariaDB: BD `effi_data` con 34 tablas, BD `nocodb_meta` para NocoDB

## Próximos Pasos
1. **Webhook en n8n**: agregar tercer trigger Webhook para llamarlo desde NocoDB
2. **NocoDB**: conectar BD `effi_data` como External Data Source
3. **Botón NocoDB**: crear botón que llame el webhook de n8n para trigger manual
4. Crear vistas/dashboards en NocoDB sobre los datos de Effi

## Archivos Clave
- Scripts export: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/`
- Script maestro export: `scripts/export_all.sh`
- Script import: `scripts/import_all.js`
- Docker compose: `/home/osserver/docker/docker-compose.yml`
- Session Effi: `scripts/session.js` (credenciales Effi, session.json)
