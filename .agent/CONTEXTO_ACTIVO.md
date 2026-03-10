# Contexto Activo - Integraciones_OS

## Estado Actual (2026-03-10)
Pipeline Effi → MariaDB funcional. Paso 3 analítico activo. NocoDB conectado. Playwright corre en el host.

## Lo que está funcionando

### Pipeline de datos Effi (3 pasos)
- **Paso 1 — 26 scripts Playwright** exportan módulos de Effi a `/home/osserver/playwright/exports/`
- **Paso 2 — import_all.js** importa **39 tablas** a MariaDB `effi_data` (TRUNCATE + INSERT)
- **Paso 3a — calcular_resumen_ventas.py** → `resumen_ventas_facturas_mes` (38 campos, PK: mes)
- **Paso 3b — calcular_resumen_ventas_canal.py** → `resumen_ventas_facturas_canal_mes` (29 campos, PK: mes+canal, 193 filas)
- **Orquestador**: `scripts/orquestador.py` — corre los 3 pasos cada 2h (Lun–Sab 06:00–20:00) vía systemd
- **n8n workflow activo**: trigger cada 2h + manual + webhook
  - Webhook URL: `https://n8n.oscomunidad.com/webhook/fa393bcf-8eb3-4b14-80bc-bfda8ca42765`

### Playwright — corre en el host (NO Docker)
- Node.js v24.14.0 + Playwright v1.49.1 + Chromium instalados en host
- Symlinks: `/exports` → `/home/osserver/playwright/exports`, `/repo/scripts` → scripts del proyecto
- Contenedor `playwright` eliminado del docker-compose

### Tablas analíticas (estado 2026-03-10)
**resumen_ventas_facturas_mes**
- 38 campos, 15 meses (2025-01 a 2026-03)
- Campos `_pct` en decimal 0–1; `pry_*` solo mes corriente; `top_*` usa nombres
- Devoluciones = NCs de `zeffi_notas_credito_venta_encabezados`

**resumen_ventas_facturas_canal_mes**
- 29 campos, PK (mes, canal), 193 filas
- `fin_ventas_netas_sin_iva = precio_bruto_total - descuento_total` (precio_neto_total incluye IVA — gotcha crítico)
- `fin_pct_del_mes` = % participación canal en total mes (suma 1.0 por mes)
- NO incluye car_, con_, devoluciones (sin campo canal en esas fuentes)

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
1. **Siguientes vistas analíticas**: resumen por cliente (`_cliente_mes`) y por producto (`_producto_mes`)
2. **App de datos**: decidir entre AppSheet (conocido, MySQL nativo) vs Appsmith (self-hosted Docker)
3. **Sync Effi → EspoCRM**: pipeline n8n que upserte clientes vía REST API

## Archivos Clave
- Scripts: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/`
- Exports: `/home/osserver/playwright/exports/`
- Docker compose: `/home/osserver/docker/docker-compose.yml`
- Cloudflare tunnel: `/etc/cloudflared/config.yml`
- Pipeline log: `logs/pipeline.log`
- Credenciales pipeline: `scripts/.env` (no está en git — Gmail + Telegram)
