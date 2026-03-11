# Contexto Activo - Integraciones_OS

## Estado Actual (2026-03-11)
Pipeline Effi → MariaDB funcional + integración EspoCRM bidireccional **completamente automatizada**.
- Pasos 3a/3b/3c/3d (facturas) + 4a/4b/4c/4d (remisiones) analíticos activos.
- Sync Effi → EspoCRM (paso 6c): 480+ contactos.
- Sync EspoCRM → Hostinger (paso 6d): tabla `crm_contactos` en Hostinger.
- Generador plantilla + import automático a Effi (pasos 7a y 7b): activos en pipeline.
- 6 tablas resumen compuestas tienen columna `_key` (PK simple = mes|col2) para herramientas externas.
- **AppSheet descartado** — Santi optó por no usarlo.

## Arquitectura de BDs — Dónde vive cada tabla

| Tipo | BD | Tabla(s) |
|---|---|---|
| Raw Effi (41 tablas) | `effi_data` local + `u768061575_os_integracion` Hostinger | `zeffi_*` |
| **Analíticas (8 tablas)** | **SOLO `u768061575_os_integracion` Hostinger** | `resumen_ventas_*` |
| NocoDB meta | `nocodb_meta` local | internas |
| EspoCRM | `espocrm` local | `contact`, `ciudad`, `email_address`, etc. |
| CRM en Hostinger | `u768061575_os_integracion` | `crm_contactos` (480+ contactos) |
| ERP Hostinger | `u768061575_os_comunidad` — **⚠️ NO TOCAR** | propias del ERP |

**Las tablas `resumen_ventas_*` NO existen en local entre corridas del pipeline.** El pipeline las calcula → guarda en local (staging) → sync copia a Hostinger → DROP de local. Fuente de verdad = Hostinger.

## Lo que está funcionando

### Pipeline completo (16 pasos via orquestador.py)
- **Paso 1 — 26 scripts Playwright** exportan módulos de Effi a `/home/osserver/playwright/exports/`
- **Paso 2 — import_all.js** importa **41 tablas** a MariaDB `effi_data` local (TRUNCATE + INSERT)
- **Paso 3a — calcular_resumen_ventas.py** → `resumen_ventas_facturas_mes` (38 campos, PK: mes)
- **Paso 3b — calcular_resumen_ventas_canal.py** → `resumen_ventas_facturas_canal_mes` (32 campos, PK: mes+canal, 251 filas)
- **Paso 3c — calcular_resumen_ventas_cliente.py** → `resumen_ventas_facturas_cliente_mes` (34 campos, PK: mes+id_cliente, 600 filas)
- **Paso 3d — calcular_resumen_ventas_producto.py** → `resumen_ventas_facturas_producto_mes` (30 campos, PK: mes+cod_articulo, 697 filas)
- **Paso 4a — calcular_resumen_ventas_remisiones_mes.py** → `resumen_ventas_remisiones_mes` (38 campos, PK: mes, 29 meses)
- **Paso 4b/4c/4d** — remisiones canal/cliente/producto analíticos
- **Paso 5 — sync_hostinger.py** → copia las 49 tablas (41 zeffi + 8 resumen) a Hostinger → DROP local de las 8 resumen. Para tablas `resumen_*`: usa DROP+CREATE en Hostinger (garantiza schema actualizado); para `zeffi_*`: CREATE IF NOT EXISTS.
- **Paso 6b — sync_espocrm_marketing.py** → actualiza enums y campos custom en EspoCRM Contact
- **Paso 6c — sync_espocrm_contactos.py** → upsert clientes Effi → EspoCRM Contact (fuente='Effi')
- **Paso 6d — sync_espocrm_to_hostinger.py** → `crm_contactos` en Hostinger (TRUNCATE + INSERT)
- **Paso 7a — generar_plantilla_import_effi.py** → XLSX contactos CRM pendientes (fuente='CRM', enviado_a_effi=0)
- **Paso 7b — import_clientes_effi.js** → Playwright sube XLSX a Effi automáticamente (solo si 7a generó)
- **Orquestador**: `scripts/orquestador.py` — corre todos los pasos cada 2h (Lun–Sab 06:00–20:00) vía systemd

### Flujo CRM → Effi (automatizado)
1. Vendedor crea contacto en EspoCRM (fuente='CRM', enviado_a_effi=0 automáticos)
2. Pipeline paso 7a: genera `/tmp/import_clientes_effi_<hoy>.xlsx`
3. Pipeline paso 7b: Playwright lo sube a Effi via "Crear o modificar **clientes** masivamente"
4. Contacto queda con enviado_a_effi=1

### Sync a Hostinger (paso 5)
- Script: `scripts/sync_hostinger.py`
- Destino: `u768061575_os_integracion` en Hostinger MySQL
- Usuario MySQL Hostinger: `u768061575_osserver` / `Epist2487.`
- SSH tunnel: `109.106.250.195:65002` vía `~/.ssh/sos_erp`
- Estrategia: TRUNCATE + INSERT lotes 500 + DROP local de tablas resumen al final
- ~100s para 49 tablas

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
- 32 campos + `_key`, PK `_key` (`mes|canal`), UNIQUE (mes, canal), 251 filas
- `fin_ventas_netas_sin_iva = precio_bruto_total - descuento_total` (precio_neto_total incluye IVA — gotcha crítico)
- `fin_pct_del_mes` = % participación canal en total mes (suma 1.0 por mes)
- `con_consignacion_pp` = OVs atribuidas al canal via id_cliente → canal histórico (mapping más-frecuente)
- 58 filas son canales con solo consignaciones (sin facturas ese mes)

**resumen_ventas_facturas_cliente_mes**
- 34 campos + `_key`, PK `_key` (`mes|id_cliente`), UNIQUE (mes, id_cliente), 600 filas
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
- 480+ contactos (Effi) + contactos CRM manuales
- Campos custom en Contact: tipoDeMarketing, tipoCliente, tarifaPrecios, numeroIdentificacion, tipoIdentificacion, tipoPersona, formaPago, vendedorEffi, fuente (enum: CRM/Effi), enviadoAEffi (bool), ciudad_id (link → Ciudad)
- Entidad Ciudad: 12,237 ciudades (Colombia/Ecuador/Rep.Dom/Guatemala) con id_effi

### Infraestructura Docker
- `/home/osserver/docker/docker-compose.yml`
- Cloudflare Tunnel: `/etc/cloudflared/config.yml`
- MariaDB corre en el **host** (systemd), NO en Docker — puerto 3306
- Credenciales: `osadmin` / `Epist2487.`

### Botón "Enviar a Effi" en EspoCRM (activo)
- Botón verde en la ficha de Contacto (detail view) → dispara pasos 7a+7b a demanda
- Flujo: botón JS → `POST /api/v1/ImportEffi/action/triggerImport` (PHP) → Flask 172.18.0.1:5050 → scripts 7a+7b
- Flask server: `scripts/webhook_server.py`, systemd service `effi-webhook.service` (activo, auto-restart)
- Archivos versionados en `espocrm-custom/` con instrucciones de deploy

## Frontend — Estado actual

| Recurso | Ruta | Estado |
|---|---|---|
| Manual de Estilos v2.0 | `frontend/design-system/MANUAL_ESTILOS.md` | ✅ Listo |
| Screenshots de referencia (88) | `frontend/design-system/screenshots/` | ✅ Listos |
| Índice de screenshots | `frontend/design-system/screenshots/INDEX.md` | ✅ Listo |
| Proyecto Vue + Quasar | `frontend/` | ⏳ Por iniciar |

**⚠️ Antes de cualquier trabajo frontend: leer `frontend/design-system/MANUAL_ESTILOS.md`**

## Próximos Pasos
1. **Limpiar contactos de prueba**: `UPDATE contact SET deleted=1 WHERE description='TEST_PIPELINE_DELETE';` en BD `espocrm`. También borrar en Effi manualmente (3 clientes: Pedro Ruiz, Farmacia Salud Natural, Ana Lucía Montoya).

## Archivos Clave
- Scripts: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/`
- Exports: `/home/osserver/playwright/exports/`
- Docker compose: `/home/osserver/docker/docker-compose.yml`
- Cloudflare tunnel: `/etc/cloudflared/config.yml`
- Pipeline log: `logs/pipeline.log`
- Credenciales pipeline: `scripts/.env` (no está en git — Gmail + Telegram)
