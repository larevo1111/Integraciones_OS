# Contexto Activo - Integraciones_OS

## Estado Actual (2026-03-09)
Pipeline Effi → MariaDB funcional. NocoDB conectado a effi_data y espocrm. EspoCRM instalado. Playwright migrado al host.

## Lo que está funcionando

### Pipeline de datos Effi
- **26 scripts Playwright** exportan módulos de Effi a `/home/osserver/playwright/exports/`
- **import_all.js** importa **39 tablas** a MariaDB `effi_data` (TRUNCATE + INSERT, host: `127.0.0.1`)
- **n8n workflow activo**: corre cada 2 horas + trigger manual + webhook
  - Webhook URL: `https://n8n.oscomunidad.com/webhook/fa393bcf-8eb3-4b14-80bc-bfda8ca42765`

### Playwright — migrado al host
- **Ya NO corre en Docker** — corre directamente en el host
- Node.js v24.14.0 + Playwright v1.49.1 + Chromium instalados en host
- Symlinks creados para compatibilidad con rutas Docker:
  - `/exports` → `/home/osserver/playwright/exports`
  - `/scripts` → `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts`
  - `/repo/scripts` → `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts`
- Contenedor `playwright` eliminado del docker-compose

### NocoDB (nocodb.oscomunidad.com)
- Proyecto: **Origen Silvestre Integrado**
- Fuente externa `effi_data` conectada vía `172.18.0.1:3306`
- Fuente externa `espocrm` conectada vía `172.18.0.1:3306`
- Tabla nativa `Control` con botón "Actualizar Effi" → webhook n8n
- Grant MariaDB: `osadmin@172.18.0.%` para acceso desde contenedores Docker

### EspoCRM (crm.oscomunidad.com)
- Contenedor: `espocrm` — puerto 8083
- BD: `espocrm` en MariaDB local
- Admin: `admin` / `Epist2487.`
- DNS CNAME configurado en Cloudflare

### Infraestructura Docker
- `/home/osserver/docker/docker-compose.yml`
- Cloudflare Tunnel: `/etc/cloudflared/config.yml`
- MariaDB corre en el **host** (systemd), NO en Docker
- Bot Telegram: contenedor `bot_telegram` (ya existía)

## Orquestador Python (activo desde 2026-03-08)
- `scripts/orquestador.py` — pipeline completo cada 2h vía systemd
- Credenciales en `scripts/.env` (Gmail + Telegram bot `@os_integraciones_bot`)
- Notificaciones: email siempre + Telegram en error
- Test: `python3 scripts/orquestador.py --forzar`

## Próximos Pasos
1. **Vistas SQL en MariaDB**: JOINs entre tablas effi_data para NocoDB y Grafana
2. **Sync Effi → EspoCRM**: pipeline n8n que upserte clientes vía REST API

## Archivos Clave
- Scripts: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/`
- Exports: `/home/osserver/playwright/exports/`
- Docker compose: `/home/osserver/docker/docker-compose.yml`
- Cloudflare tunnel: `/etc/cloudflared/config.yml`
