# Contexto: Pipeline Effi
**Actualizado**: 2026-03-23

## Estado

Pipeline completo activo. 18 pasos. Verificado 2026-03-11: 50/50 tablas OK, 487 contactos, 0 errores.
Orquestador ejecuta cada 1h (Lun–Sab 06:00–20:00) vía systemd.

## Arquitectura de BDs

| BD | Ubicación | Rol |
|---|---|---|
| `effi_data` | MariaDB local | Staging — 41 tablas `zeffi_*` permanentes + `catalogo_articulos`. Las `resumen_ventas_*` existen solo durante el pipeline |
| `u768061575_os_integracion` | Hostinger | Fuente de verdad final. 51 tablas (41 zeffi + 8 resumen + `crm_contactos` + `catalogo_articulos`) |
| `u768061575_os_comunidad` | Hostinger | ERP en producción. **PROHIBICIÓN ABSOLUTA — nunca tocar** |

**Regla clave**: Las `resumen_ventas_*` NO existen en local entre corridas. Pipeline las calcula → staging local → sync a Hostinger → DROP local. Fuente de verdad = Hostinger.

## Credenciales

| Recurso | Usuario | Pass |
|---|---|---|
| MariaDB local | `osadmin` | `Epist2487.` |
| Hostinger MySQL `u768061575_os_integracion` | `u768061575_osserver` | `Epist2487.` |
| Hostinger MySQL `u768061575_os_comunidad` | `u768061575_ssierra047` | `Epist2487.` |
| Hostinger SSH | user=`u768061575`, key=`~/.ssh/sos_erp`, host=`109.106.250.195:65002` | — |

Hostinger NO permite compartir un usuario MySQL entre 2 BDs diferentes — cada BD tiene su propio usuario.

## Comandos base

```bash
# MariaDB local
mysql -u osadmin -pEpist2487. effi_data -e "..." 2>/dev/null

# Correr pipeline completo
python3 scripts/orquestador.py --forzar

# Correr paso individual
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts
node export_X.js       # Playwright (HOST, no Docker)
python3 sync_hostinger.py
```

## 18 pasos del pipeline

| Paso | Script | Descripción |
|---|---|---|
| 1 | 26 scripts Playwright en `export_all.sh` | Exportan módulos de Effi a `/home/osserver/playwright/exports/` |
| 2 | `import_all.js` | XLSX → effi_data local (TRUNCATE + INSERT, 41 tablas) |
| 3a | `calcular_resumen_ventas.py` | `resumen_ventas_facturas_mes` (38 campos, 15 meses, PK: mes) |
| 3b | `calcular_resumen_ventas_canal.py` | `resumen_ventas_facturas_canal_mes` (32 campos, PK: mes+canal, 251 filas) |
| 3c | `calcular_resumen_ventas_cliente.py` | `resumen_ventas_facturas_cliente_mes` (34 campos, PK: mes+id_cliente, 603 filas) |
| 3d | `calcular_resumen_ventas_producto.py` | `resumen_ventas_facturas_producto_mes` (30 campos, PK: mes+cod_articulo, 697 filas) |
| 4a | `calcular_resumen_ventas_remisiones_mes.py` | `resumen_ventas_remisiones_mes` (38 campos, PK: mes, 29 meses) |
| 4b | `calcular_resumen_ventas_remisiones_canal.py` | Remisiones por canal |
| 4c | `calcular_resumen_ventas_remisiones_cliente.py` | Remisiones por cliente |
| 4d | `calcular_resumen_ventas_remisiones_producto.py` | Remisiones por producto |
| 4e | `sync_catalogo_articulos.py` | Detecta nuevos cod_articulo vendidos → inserta en `catalogo_articulos` con grupo |
| 4f | `asignar_grupo_producto.py --groq` | Asigna grupo a artículos sin grupo (regex + Groq si falla regex) |
| 5 | `sync_hostinger.py` | effi_data + resumen + catalogo_articulos → Hostinger (~42 tablas, ~100s). DROP local tablas resumen al final |
| 6b | `sync_espocrm_marketing.py` | Actualiza enums dinámicos en EspoCRM Contact |
| 6c | `sync_espocrm_contactos.py` | Upsert clientes Effi → EspoCRM Contact (fuente='Effi') con ciudad normalizada |
| 6d | `sync_espocrm_to_hostinger.py` | EspoCRM → `crm_contactos` en Hostinger (DROP+CREATE+INSERT) |
| 7a | `generar_plantilla_import_effi.py` | CRM pendientes → XLSX `/tmp/import_clientes_effi_<hoy>.xlsx` |
| 7b | `import_clientes_effi.js` | Playwright sube XLSX a Effi (solo si 7a generó) |

## Estrategia sync_hostinger.py

- TRUNCATE + INSERT lotes 500 filas
- Para tablas `resumen_*` y `codigos_ciudades_dane`: DROP + CREATE (garantiza schema actualizado)
- Para `zeffi_*`: CREATE IF NOT EXISTS
- DROP local de las 8 tablas resumen al final
- ~100s para 50 tablas

## 8 tablas analíticas (SOLO Hostinger)

| Tabla | PK | Descripción |
|---|---|---|
| `resumen_ventas_facturas_mes` | mes | 38 campos, 15 meses |
| `resumen_ventas_facturas_canal_mes` | `_key` (mes\|canal) | 32 campos, 251 filas |
| `resumen_ventas_facturas_cliente_mes` | `_key` (mes\|id_cliente) | 34 campos, 603 filas |
| `resumen_ventas_facturas_producto_mes` | `_key` (mes\|cod_articulo) | 30 campos, 697 filas |
| `resumen_ventas_remisiones_mes` | mes | 38 campos, 29 meses |
| `resumen_ventas_remisiones_canal_mes` | `_key` (mes\|canal) | — |
| `resumen_ventas_remisiones_cliente_mes` | `_key` (mes\|id_cliente) | — |
| `resumen_ventas_remisiones_producto_mes` | `_key` (mes\|cod_articulo) | — |

**6 tablas resumen compuestas** tienen columna `_key` (PK simple = `mes|col2`) para herramientas externas.

Convenciones de campos:
- `_pct` = valor decimal 0–1
- `pry_*` = solo mes corriente (proyección)
- `top_*` = nombres (top clientes, productos)
- `ant_*` = año anterior

## catalogo_articulos

| Campo | Descripción |
|---|---|
| `cod_articulo` | PK |
| `descripcion` | Nombre del artículo |
| `grupo_producto` | Nombre sin gramaje/presentación |
| `actualizado_en` | Timestamp |
| `grupo_revisado` | Flag revisión manual |

- 500 registros; 176 con `grupo_producto` asignado
- Solo productos vendidos alguna vez
- Asignación: regex determinístico + Groq para referencias nuevas
- Colación: `utf8mb4_unicode_ci` (igual que zeffi_*)
- Sincronizada a Hostinger via pipeline

## Playwright — configuración técnica

- Corre en el HOST (NO en Docker)
- Node.js v24.14.0 + Playwright v1.49.1 + Chromium instalados en host
- **v1.58.2 crashea con SIGSEGV en kernel 6.17** → usar v1.49.1
- Symlinks: `/exports` → `/home/osserver/playwright/exports`, `/repo/scripts` → scripts del proyecto
- Contenedor `playwright` eliminado del docker-compose
- Ejecución: `cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts && node export_X.js`

## Gotchas críticos de Effi

- `precio_neto_total` en detalle de facturas **incluye IVA** — usar `precio_bruto_total - descuento_total`
- `?sucursal=1` → todos los históricos; `?vigente=1` → solo activos (no usar para histórico)
- Módulos con `window.open`: interceptar la URL en lugar de esperar download event
- **id_cliente en facturas/remisiones**: formato "CC 74084937" (con prefijo tipo doc), mientras `zeffi_clientes.numero_de_identificacion` = "74084937". Para JOIN usar `SUBSTRING_INDEX(d.id_cliente, ' ', -1)`
- **`zeffi_clientes` tiene NITs duplicados** (al menos 3: 39440347, 90173460334, 9999999). JOIN directo infla sumas. SIEMPRE deduplicar: `LEFT JOIN (SELECT numero_de_identificacion, MAX(forma_de_pago) FROM zeffi_clientes GROUP BY numero_de_identificacion) c ON ...`

## Semántica de zeffi_ordenes_venta_encabezados (Consignación)

- `vigencia = 'Vigente'` → OV activa, mercancía en calle. **ÚNICO filtro correcto para "consignación activa"**
- `vigencia = 'Anulada'` + `estado_facturacion = 'Pendiente'` → anulada/retirada sin venta
- `vigencia = 'Anulada'` + `estado_facturacion = 'Remisionada'` → OV convertida a remisión (venta consolidada)
- `vigencia = 'Anulada'` + `estado_facturacion = 'Facturada'` → OV facturada (venta consolidada)

**NUNCA filtrar solo por `ultimo_estado + estado_facturacion`** — devuelve 475 filas con 462 ya cerradas.

## Flujo CRM → Effi (pasos 7a+7b automatizados)

1. Vendedor crea contacto en EspoCRM (`fuente='CRM'`, `enviado_a_effi=0` automáticos)
2. Pipeline paso 7a: genera `/tmp/import_clientes_effi_<hoy>.xlsx`
3. Pipeline paso 7b: Playwright sube el XLSX a Effi via "Crear o modificar clientes masivamente"
   - URL: `https://effi.com.co/app/tercero/cliente`
   - Selector file: `#modalImportarCrearMasivo input[type="file"]`
   - Selector submit: `#modalImportarCrearMasivo #btn_submit`
4. Contacto queda con `enviado_a_effi=1`

## Mapeos plantilla importación Effi (36 columnas)

- `tipo_identificacion` texto → ID numérico (dict hardcoded `TIPO_ID_MAP`)
- `tipo_persona` → 1 (Física) / 2 (Jurídica)
- `regimen_tributario` → 5 (natural) / 4 (jurídica)
- `tarifa_precios` nombre → id (desde `zeffi_tarifas_precios`)
- `tipo_de_marketing` nombre → id (desde `zeffi_tipos_marketing`)
- `ciudad_id` → `id_effi` (tabla `ciudad`)
- `email_responsable`: siempre `'equipo.origensilvestre@gmail.com'`
- `sucursal=1`, `moneda=COP`, `permitir_venta=1`

## Infraestructura

- Docker compose: `/home/osserver/docker/docker-compose.yml`
- Cloudflare tunnel: `/etc/cloudflared/config.yml`
- MariaDB corre en el HOST (systemd), NO en Docker — puerto 3306
- NocoDB (nocodb.oscomunidad.com): proyecto "Origen Silvestre Integrado", fuente `effi_data` + `espocrm` vía `172.18.0.1:3306`

## Archivos clave

| Archivo | Propósito |
|---|---|
| `scripts/orquestador.py` | Orquestador pipeline completo |
| `scripts/export_all.sh` | Lanza los 26 scripts Playwright |
| `scripts/import_all.js` | XLSX → MariaDB 41 tablas |
| `scripts/sync_hostinger.py` | Sync a Hostinger |
| `scripts/calcular_resumen_ventas*.py` | Cálculo tablas analíticas facturas |
| `scripts/calcular_resumen_ventas_remisiones*.py` | Cálculo tablas analíticas remisiones |
| `scripts/sync_catalogo_articulos.py` | Gestión catalogo_articulos |
| `scripts/asignar_grupo_producto.py` | Asignación grupos con regex+Groq |
| `scripts/.env` | Credenciales (NO en git — Gmail + Telegram) |
| `logs/pipeline.log` | Log del pipeline |
| `.agent/CATALOGO_SCRIPTS.md` | Catálogo completo de todos los scripts |
| `.agent/CATALOGO_TABLAS.md` | 47+ tablas con descripciones de negocio |
