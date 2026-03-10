# Contexto Activo - Integraciones_OS

## Estado Actual (2026-03-10)
Pipeline Effi → MariaDB funcional. Paso 3 analítico activo. NocoDB conectado. Playwright corre en el host.

## Lo que está funcionando

### Pipeline de datos Effi (3 pasos)
- **Paso 1 — 26 scripts Playwright** exportan módulos de Effi a `/home/osserver/playwright/exports/`
- **Paso 2 — import_all.js** importa **39 tablas** a MariaDB `effi_data` (TRUNCATE + INSERT)
- **Paso 3 — calcular_resumen_ventas.py** calcula tabla analítica `resumen_ventas_facturas_mes` (38 campos: fin_, cto_, vol_, cli_, car_, cat_, con_, top_, pry_, ant_)
- **Orquestador**: `scripts/orquestador.py` — corre los 3 pasos cada 2h (Lun–Sab 06:00–20:00) vía systemd
- **n8n workflow activo**: trigger cada 2h + manual + webhook
  - Webhook URL: `https://n8n.oscomunidad.com/webhook/fa393bcf-8eb3-4b14-80bc-bfda8ca42765`

### Playwright — corre en el host (NO Docker)
- Node.js v24.14.0 + Playwright v1.49.1 + Chromium instalados en host
- Symlinks: `/exports` → `/home/osserver/playwright/exports`, `/repo/scripts` → scripts del proyecto
- Contenedor `playwright` eliminado del docker-compose

### resumen_ventas_facturas_mes (estado 2026-03-10)
- 38 campos, 15 meses de datos (2025-01 a 2026-03)
- Campos `_pct` en decimal 0–1 (no multiplicados por 100)
- `pry_*` solo populados para el mes en curso (NULL para meses cerrados)
- `top_*` usa nombres (no IDs/cédulas)
- Devoluciones = NCs de `zeffi_notas_credito_venta_encabezados` (no `devoluciones_venta`)

### NocoDB (nocodb.oscomunidad.com)
- Proyecto: **Origen Silvestre Integrado**
- Fuente externa `effi_data` conectada vía `172.18.0.1:3306`
- Fuente externa `espocrm` conectada vía `172.18.0.1:3306`
- Tabla nativa `Control` con botón "Actualizar Effi" → webhook n8n

### EspoCRM (crm.oscomunidad.com)
- Contenedor: `espocrm` — puerto 8083
- BD: `espocrm` en MariaDB local

### Infraestructura Docker
- `/home/osserver/docker/docker-compose.yml`
- Cloudflare Tunnel: `/etc/cloudflared/config.yml`
- MariaDB corre en el **host** (systemd), NO en Docker — puerto 3306
- Credenciales: `osadmin` / `Epist2487.`

## Próximos Pasos
1. **Vistas SQL en MariaDB**: JOINs entre tablas effi_data para NocoDB y Grafana
2. **Sync Effi → EspoCRM**: pipeline n8n que upserte clientes vía REST API
3. **Conectar NocoDB a resumen_ventas_facturas_mes** como tabla de análisis

## Archivos Clave
- Scripts: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/`
- Exports: `/home/osserver/playwright/exports/`
- Docker compose: `/home/osserver/docker/docker-compose.yml`
- Cloudflare tunnel: `/etc/cloudflared/config.yml`
- Pipeline log: `logs/pipeline.log`
- Credenciales pipeline: `scripts/.env` (no está en git — Gmail + Telegram)
