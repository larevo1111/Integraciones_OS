# Contexto Activo - Integraciones_OS

## Estado Actual (2026-03-10)
Pipeline Effi → MariaDB funcional + integración EspoCRM bidireccional activa.
- Pasos 3a/3b/3c/3d (facturas) + 4a/4b/4c/4d (remisiones) analíticos activos.
- Sync Effi → EspoCRM (paso 6c): 480 contactos.
- Sync EspoCRM → Hostinger (paso 6d): tabla `crm_contactos` en Hostinger.
- Generador plantilla Effi (paso 7): genera XLSX de contactos CRM para importar a Effi.

## Arquitectura de BDs — Dónde vive cada tabla

| Tipo | BD | Tabla(s) |
|---|---|---|
| Raw Effi (39 tablas) | `effi_data` local + `u768061575_os_integracion` Hostinger | `zeffi_*` |
| **Analíticas (5 tablas)** | **SOLO `u768061575_os_integracion` Hostinger** | `resumen_ventas_*` |
| NocoDB meta | `nocodb_meta` local | internas |
| EspoCRM | `espocrm` local | internas |
| ERP Hostinger | `u768061575_os_comunidad` — **⚠️ NO TOCAR** | propias del ERP |

**Las tablas `resumen_ventas_*` NO existen en local entre corridas del pipeline.** El pipeline las calcula → guarda en local (staging) → sync copia a Hostinger → DROP de local. Fuente de verdad = Hostinger.

## Lo que está funcionando

### Pipeline de datos Effi (6 pasos)
- **Paso 1 — 26 scripts Playwright** exportan módulos de Effi a `/home/osserver/playwright/exports/`
- **Paso 2 — import_all.js** importa **39 tablas** a MariaDB `effi_data` local (TRUNCATE + INSERT)
- **Paso 3a — calcular_resumen_ventas.py** → `resumen_ventas_facturas_mes` (38 campos, PK: mes)
- **Paso 3b — calcular_resumen_ventas_canal.py** → `resumen_ventas_facturas_canal_mes` (32 campos, PK: mes+canal, 251 filas)
- **Paso 3c — calcular_resumen_ventas_cliente.py** → `resumen_ventas_facturas_cliente_mes` (34 campos, PK: mes+id_cliente, 600 filas)
- **Paso 3d — calcular_resumen_ventas_producto.py** → `resumen_ventas_facturas_producto_mes` (30 campos, PK: mes+cod_articulo, 697 filas)
- **Paso 4a — calcular_resumen_ventas_remisiones_mes.py** → `resumen_ventas_remisiones_mes` (38 campos, PK: mes, 29 meses)
- **Paso 4b/4c/4d** — remisiones canal/cliente/producto analíticos
- **Paso 5 — sync_hostinger.py** → copia las 47 tablas (39 zeffi + 8 resumen) a Hostinger → DROP local de las 8 resumen
- **Paso 6b — sync_espocrm_marketing.py** → actualiza enums y campos custom en EspoCRM Contact
- **Paso 6c — sync_espocrm_contactos.py** → upsert 480 clientes Effi → EspoCRM Contact (fuente='Effi')
- **Paso 6d — sync_espocrm_to_hostinger.py** → `crm_contactos` en Hostinger (480 contactos)
- **Paso 7 — generar_plantilla_import_effi.py** → XLSX para importar contactos CRM a Effi (manual)
- **Orquestador**: `scripts/orquestador.py` — corre todos los pasos cada 2h (Lun–Sab 06:00–20:00) vía systemd
- **n8n workflow activo**: trigger cada 2h + manual + webhook
  - Webhook URL: `https://n8n.oscomunidad.com/webhook/fa393bcf-8eb3-4b14-80bc-bfda8ca42765`

### Sync a Hostinger (paso 5)
- Script: `scripts/sync_hostinger.py`
- Destino: `u768061575_os_integracion` en Hostinger MySQL
- Usuario MySQL Hostinger: `u768061575_osserver` / `Epist2487.`
- SSH tunnel: `109.106.250.195:65002` vía `~/.ssh/sos_erp`
- Estrategia: TRUNCATE + INSERT lotes 500 + DROP local de tablas resumen al final
- ~100s para 44 tablas (~63k filas en zeffi_trazabilidad = más pesada)

### Playwright — corre en el host (NO Docker)
- Node.js v24.14.0 + Playwright v1.49.1 + Chromium instalados en host
- Symlinks: `/exports` → `/home/osserver/playwright/exports`, `/repo/scripts` → scripts del proyecto
- Contenedor `playwright` eliminado del docker-compose

### Tablas analíticas — estado 2026-03-10 (todas en Hostinger)
**resumen_ventas_facturas_mes**
- 38 campos, 15 meses (2025-01 a 2026-03)
- Campos `_pct` en decimal 0–1; `pry_*` solo mes corriente; `top_*` usa nombres
- Devoluciones = NCs de `zeffi_notas_credito_venta_encabezados`

**resumen_ventas_facturas_canal_mes**
- 32 campos, PK (mes, canal), 251 filas
- `fin_ventas_netas_sin_iva = precio_bruto_total - descuento_total` (precio_neto_total incluye IVA — gotcha crítico)
- `fin_pct_del_mes` = % participación canal en total mes (suma 1.0 por mes)
- `con_consignacion_pp` = OVs atribuidas al canal via id_cliente → canal histórico (mapping más-frecuente)
- 58 filas son canales con solo consignaciones (sin facturas ese mes)

**resumen_ventas_facturas_cliente_mes**
- 34 campos, PK (mes, id_cliente), 600 filas
- `canal` viene del maestro `zeffi_clientes.tipo_de_marketing` (estado actual del cliente)
- `cli_es_nuevo = 1` si es la primera factura histórica del cliente
- `con_consignacion_pp` = OVs directamente por id_cliente (sin mapping)
- SUM(cliente_mes) vs resumen_mes: diff ≤ 0.26 (solo redondeo DECIMAL)

**resumen_ventas_remisiones_mes**
- 38 campos, PK mes, 29 meses (2023-11 a 2026-03)
- Incluye: "Pendiente de facturar" + "Convertida a factura". Excluye: anuladas reales (348).
- `rem_pendientes / rem_facturadas / rem_pct_facturadas` = estado actual (dinámico)
- Devoluciones de `zeffi_devoluciones_venta_encabezados` (27 registros)
- Encabezados: formato coma decimal. Detalle: números planos (2 helpers distintos).
- diff_total vs fuente = 0.00

### NocoDB (nocodb.oscomunidad.com)
- Proyecto: **Origen Silvestre Integrado**
- Fuente externa `effi_data` conectada vía `172.18.0.1:3306` (solo tablas zeffi_ — las resumen NO están aquí)
- Fuente externa `espocrm` conectada vía `172.18.0.1:3306`
- Tabla nativa `Control` con botón "Actualizar Effi" → webhook n8n

### EspoCRM (crm.oscomunidad.com)
- Contenedor: `espocrm` — puerto 8083
- BD: `espocrm` en MariaDB local
- 480 contactos (Effi) + contactos CRM manuales
- Campos custom en Contact: tipoDeMarketing, tipoCliente, tarifaPrecios, numeroIdentificacion, tipoIdentificacion, tipoPersona, formaPago, vendedorEffi, fuente (enum: CRM/Effi), enviadoAEffi (bool)
- Entidad Ciudad: 12,237 ciudades (Colombia/Ecuador/Rep.Dom/Guatemala) con id_effi
- Workflow EspoCRM → Effi: crear contacto con fuente=CRM → generar_plantilla_import_effi.py → subir XLSX a Effi (manual por ahora)

### Infraestructura Docker
- `/home/osserver/docker/docker-compose.yml`
- Cloudflare Tunnel: `/etc/cloudflared/config.yml`
- MariaDB corre en el **host** (systemd), NO en Docker — puerto 3306
- Credenciales: `osadmin` / `Epist2487.`

## Próximos Pasos
1. **import_clientes_effi.js**: script Playwright que suba el XLSX generado a Effi automáticamente (solo después de validar el XLSX manualmente en Effi)
2. **Conectar AppSheet** a `crm_contactos` en Hostinger para portal de contactos
3. **Paso 7 al pipeline**: agregar generador XLSX + Playwright import como paso automático

## Archivos Clave
- Scripts: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/`
- Exports: `/home/osserver/playwright/exports/`
- Docker compose: `/home/osserver/docker/docker-compose.yml`
- Cloudflare tunnel: `/etc/cloudflared/config.yml`
- Pipeline log: `logs/pipeline.log`
- Credenciales pipeline: `scripts/.env` (no está en git — Gmail + Telegram)
