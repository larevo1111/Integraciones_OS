# Contexto Activo - Integraciones_OS

## Estado Actual (2026-03-11)
Pipeline Effi → MariaDB funcional + integración EspoCRM bidireccional **completamente automatizada**.
- Pipeline verificado 2026-03-11: **50/50 tablas** sincronizadas, 487 contactos, 0 errores.
- Pasos 3a/3b/3c/3d (facturas) + 4a/4b/4c/4d (remisiones) analíticos activos.
- Sync Effi → EspoCRM (paso 6c): 487 contactos con ciudad normalizada ("Ciudad - Departamento").
- Sync EspoCRM → Hostinger (paso 6d): tabla `crm_contactos` en Hostinger (DROP+CREATE).
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
- **Paso 3a — calcular_resumen_ventas.py** → `resumen_ventas_facturas_mes` (campos + **year_ant_* y mes_ant_* para 9 métricas**, PK: mes)
- **Paso 3b — calcular_resumen_ventas_canal.py** → `resumen_ventas_facturas_canal_mes` (32 campos, PK: mes+canal, 251 filas)
- **Paso 3c — calcular_resumen_ventas_cliente.py** → `resumen_ventas_facturas_cliente_mes` (34 campos, PK: mes+id_cliente, 600 filas)
- **Paso 3d — calcular_resumen_ventas_producto.py** → `resumen_ventas_facturas_producto_mes` (30 campos, PK: mes+cod_articulo, 697 filas)
- **Paso 4a — calcular_resumen_ventas_remisiones_mes.py** → `resumen_ventas_remisiones_mes` (38 campos, PK: mes, 29 meses)
- **Paso 4b/4c/4d** — remisiones canal/cliente/producto analíticos
- **Paso 5 — sync_hostinger.py** → copia las 50 tablas (41 zeffi + 8 resumen + codigos_ciudades_dane) a Hostinger → DROP local de las 8 resumen. Para tablas `resumen_*` y `codigos_ciudades_dane`: usa DROP+CREATE (garantiza schema actualizado); para `zeffi_*`: CREATE IF NOT EXISTS.
- **Paso 6b — sync_espocrm_marketing.py** → actualiza enums y campos custom en EspoCRM Contact
- **Paso 6c — sync_espocrm_contactos.py** → upsert clientes Effi → EspoCRM Contact (fuente='Effi'). Traduce ciudad Effi → formato "Ciudad - Departamento" (normalización + alias)
- **Paso 6d — sync_espocrm_to_hostinger.py** → `crm_contactos` en Hostinger (DROP+CREATE+INSERT). Usa campos custom (direccion, ciudad_nombre), NO nativos address_*
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
- ~100s para 50 tablas

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
- 34 campos + `_key`, PK `_key` (`mes|id_cliente`), UNIQUE (mes, id_cliente), 603 filas
- `canal` viene del maestro `zeffi_clientes.tipo_de_marketing` (estado actual del cliente)
- **⚠️ Gotcha id_cliente**: `zeffi_facturas_venta_detalle.id_cliente` = "CC 74084937" (con prefijo tipo doc), mientras `zeffi_clientes.numero_de_identificacion` = "74084937". JOIN usa `SUBSTRING_INDEX(d.id_cliente, ' ', -1)`.
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
- 488 contactos: 362 Cliente directo, 106 Negocio amigo, 13 Interno, 7 Red de amigos
- **tipoCliente**: enum propio de EspoCRM (Negocio amigo, Red de amigos, Cliente directo, Interno, Otro). NO se sincroniza desde Effi — se gestiona manualmente. A Effi siempre tipo_cliente=1.
- **calificacionNegocioAmigo**: enum A/B/C, solo visible cuando tipoCliente='Negocio amigo' (dynamicLogic). Todos en B inicialmente.
- **fuente**: readOnly (CRM/Effi). No editable por usuario.
- Otros campos custom: tipoDeMarketing, tarifaPrecios, numeroIdentificacion, tipoIdentificacion, tipoPersona, formaPago, vendedorEffi, enviadoAEffi (bool), **ciudadNombre** (enum: "Ciudad - Depto"), **direccion** + **direccionLinea2** (varchar custom)
- **Municipio**: enum dinámico con formato "Ciudad - Departamento" desde `codigos_ciudades_dane` (effi_data). NO usa campo compuesto `address` ni link a tabla `ciudad` (deprecados)
- **Dirección**: campos custom `direccion` + `direccionLinea2`. Los nativos `address_street/city/state/country` ya NO se usan
- Skill completa: `/espocrm-integracion`

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

## Frontend — Estado actual (2026-03-13)

> **IMPORTANTE**: `menu.oscomunidad.com` NO es el ERP definitivo. Es una **app temporal de visualización de datos** mientras se construye el ERP real. La usan Santi y Jen para ver información de ventas.
> El **ERP real** está en `u768061575_os_comunidad` (Hostinger) — **⚠️ NO TOCAR**.

| Recurso | Ruta | Estado |
|---|---|---|
| Manual de Estilos v2.0 | `frontend/design-system/MANUAL_ESTILOS.md` | ✅ Listo |
| Screenshots de referencia (88) | `frontend/design-system/screenshots/` | ✅ Listos |
| Proyecto Vue + Quasar | `frontend/app/` | ✅ Producción (puerto 9100, os-erp-frontend) |
| URL pública app temporal | menu.oscomunidad.com | ✅ Cloudflare tunnel activo |
| **App IA Admin** | ia.oscomunidad.com | ✅ Activa — puerto 9200, systemd `os-ia-admin.service` |
| Tabla sys_menu | Hostinger `u768061575_os_integracion` | ✅ 36 registros (7 módulos + 29 submenús) |
| **API Express** | `frontend/api/` | ✅ Puerto 9100, systemd `os-erp-frontend` |
| **Resumen Facturación** | `pages/ventas/ResumenFacturacionPage.vue` | ✅ 3 pestañas: Por mes / Por producto / Por grupo. Barra de filtros de fechas (años, trimestres, rango personalizado) en tabs producto/grupo |
| **Detalle Mes** | `pages/ventas/DetalleFacturacionMesPage.vue` | ✅ /ventas/detalle-mes/:mes — KPIs + 6 tablas acordeón + click drill-down |
| **Detalle Cliente** | `pages/ventas/DetalleClienteMesPage.vue` | ✅ /ventas/detalle-cliente/:mes/:id_cliente |
| **Detalle Canal** | `pages/ventas/DetalleCanalMesPage.vue` | ✅ /ventas/detalle-canal/:mes/:canal |
| **Detalle Producto** | `pages/ventas/DetalleProductoMesPage.vue` | ✅ /ventas/detalle-producto/:mes/:cod_articulo |
| **Detalle Factura** | `pages/ventas/DetalleFacturaPage.vue` | ✅ /ventas/detalle-factura/:id_interno/:id_numeracion |
| **Facturas de producto/grupo** | `pages/ventas/DetalleFacturasProductoPage.vue` | ✅ Reutilizable: /ventas/facturas-producto/:cod y /ventas/facturas-grupo/:grupo — KPIs + tabla, click → DetalleFacturaPage |
| **OsDataTable** | `components/OsDataTable.vue` | ✅ Tabla reutilizable. **Fila de subtotales al TOPE** (debajo del header, sticky) — ya NO al pie. Tooltips automáticos, mini-popup, filtros, subtotales, row-click |
| **Cartera CxC** | `pages/ventas/CarteraPage.vue` | ✅ /ventas/cartera — KPIs + tabla resumen por cliente (click → detalle) |
| **Detalle Cartera Cliente** | `pages/ventas/DetalleCarteraClientePage.vue` | ✅ /ventas/cartera/:id_cliente — KPIs + facturas pendientes del cliente |
| **Consignación** | `pages/ventas/ConsignacionPage.vue` | ✅ /ventas/consignacion — 2 tabs: Por cliente / Por producto. Filtro: `vigencia='Vigente'` |
| **Detalle Consignación** | `pages/ventas/DetalleConsignacionPage.vue` | ✅ /ventas/consignacion-orden/:id_orden |
| **Consignación por producto** | `pages/ventas/ConsignacionProductoPage.vue` | ✅ /ventas/consignacion-producto/:cod_articulo — órdenes activas con ese producto |

**⚠️ Antes de cualquier trabajo frontend: leer `frontend/design-system/MANUAL_ESTILOS.md`**
**⚠️ Después de cualquier cambio Vue/JS: `cd frontend/app && npx quasar build`**

### Jerarquía de navegación drill-down (módulo Ventas)
```
ResumenFacturacionPage — tab Por mes
  └─ click fila → DetalleFacturacionMesPage (mes)
       ├─ click canal    → DetalleCanalMesPage
       ├─ click cliente  → DetalleClienteMesPage
       ├─ click producto → DetalleProductoMesPage
       └─ click factura  → DetalleFacturaPage ⭐ (vista canónica)

ResumenFacturacionPage — tab Por producto (con filtro fechas)
  └─ click fila → DetalleFacturasProductoPage (/facturas-producto/:cod)
       └─ click factura → DetalleFacturaPage ⭐

ResumenFacturacionPage — tab Por grupo (con filtro fechas)
  └─ click fila → DetalleFacturasProductoPage (/facturas-grupo/:grupo)
       └─ click factura → DetalleFacturaPage ⭐

ConsignacionPage — tab Por cliente
  └─ click → ConsignacionClientePage → click orden → DetalleConsignacionPage

ConsignacionPage — tab Por producto
  └─ click → ConsignacionProductoPage → click orden → DetalleConsignacionPage
```

### catalogo_articulos — tabla de grupos de producto
- **BD**: `effi_data` local (y sincronizada a Hostinger via pipeline)
- **Propósito**: mapear `cod_articulo` → `grupo_producto` (nombre sin gramaje/presentación)
- **Campos**: `cod_articulo` (PK), `descripcion`, `grupo_producto`, `actualizado_en`, `grupo_revisado`
- **500 registros**: 176 con `grupo_producto` asignado (solo productos vendidos alguna vez)
- **Asignación**: regex determinístico (`scripts/asignar_grupo_producto.py`). Groq solo para nuevas referencias futuras.
- **Pipeline paso 4e**: `sync_catalogo_articulos.py` detecta nuevos cod_articulo vendidos y les asigna grupo automáticamente
- **Colación**: `utf8mb4_unicode_ci` (igual que zeffi_*)

### API Express — endpoints activos en server.js
- `/api/ventas/resumen-mes|canal|cliente|producto` — tablas resumen Hostinger
- `/api/ventas/facturas|cotizaciones|remisiones` — encabezados zeffi (con filtro mes)
- `/api/ventas/resumen-por-producto` — toda la vida por cod_articulo, JOIN catalogo_articulos. Acepta `?desde=&hasta=`
- `/api/ventas/resumen-por-grupo` — toda la vida por grupo_producto. Acepta `?desde=&hasta=`
- `/api/ventas/anios-facturas` — años distintos disponibles en zeffi_facturas_venta_detalle
- `/api/ventas/facturas-producto/:cod_articulo` — facturas donde aparece el producto
- `/api/ventas/facturas-grupo/:grupo` — facturas donde aparece cualquier ref. del grupo
- `/api/ventas/cliente-productos|canal-clientes|canal-productos|canal-facturas|canal-remisiones` — drill-down por canal
- `/api/ventas/producto-canales|producto-clientes|producto-facturas` — drill-down por producto
- `/api/ventas/factura/:id_interno/:id_numeracion` — encabezado + ítems de una factura
- `/api/ventas/cartera|cartera-cliente|cartera-cliente/:id` — módulo CxC
- `/api/ventas/consignacion` — OVs activas (`vigencia='Vigente'`)
- `/api/ventas/consignacion/:id_orden` — detalle de orden
- `/api/ventas/consignacion-cliente/:id_cliente` — órdenes activas del cliente
- `/api/ventas/consignacion-por-producto` — órdenes activas agrupadas por cod_articulo
- `/api/ventas/consignacion-producto/:cod_articulo` — órdenes activas con ese producto
- `/api/tooltips` — ~60 descripciones de columnas
- `/api/columnas/:tabla` — columnas de cualquier tabla Hostinger
- `/api/export/:recurso` — CSV / XLSX / PDF

### OsDataTable — componente reutilizable
- Props: `rows`, `columns ({key,label,visible})`, `loading`, `title`, `recurso`, `mes`, `tooltips`
- Emits: `row-click`
- **Fila de subtotales al TOPE** (justo debajo del `<thead>`, sticky top:36px) — **no al pie**
- Mini-popup por columna: Filtro (6 operadores), Ordenamiento, Subtotal (Σ x̄ ↑ ↓)
- Tooltips: carga `/api/tooltips` automáticamente (caché global, no necesita prop)
- Formato: `fin_/cto_/car_` → `$COP`, `_pct/_margen` → `%` (×100), resto → número con `.` miles

## Servicio Central de IA — `ia_service_os` (actualizado 2026-03-13)

> **SCOPE**: Este servicio NO es exclusivo de Integraciones_OS. Es el servicio de IA de TODA la empresa OS.
> Sirve a bot de Telegram, ERP, futuras apps, cualquier proyecto OS.
> **Admin panel**: `ia-admin/` — app Vue+Quasar activa en puerto 9200, `os-ia-admin.service`. 7 páginas: Dashboard, Agentes, Tipos, Logs, Playground, Usuarios, Contextos. Auth Google OAuth + JWT propio (2 pasos: Google → selección empresa → JWT final con `empresa_activa`).

### Multi-empresa (multi-tenant) — IMPLEMENTADO 2026-03-13

**Plan completo:** `.agent/planes/actuales/PLAN_MULTITENANT_IA.md`
**Manual:** `.agent/docs/MANUAL_EMPRESAS_USUARIOS.md`

- **Todas las tablas** tienen campo `empresa` (excepto `ia_agentes` — config global)
- **Todos los campos de auditoría**: `usuario_creacion`, `usuario_ult_mod`, `created_at`, `updated_at`
- **Nuevas tablas**: `ia_empresas` (uid PK, nombre, siglas) + `ia_usuarios_empresas` (email + empresa_uid + rol)
- **JWT 2 pasos**: Google auth → JWT temporal con lista empresas → seleccionar empresa → JWT final con `empresa_activa`
- **`empresa` NUNCA viene del cliente** — siempre inyectada desde JWT en middleware `requireAuth`
- **Empresa activa**: `ori_sil_2` (Origen Silvestre). Santiago=admin, Jennifer=viewer.
- **Frontend**: Header con nombre usuario + empresa, LoginPage con paso 2 selección, authStore con `empresa_activa`

**Pendientes menores:**
- 2.7 `GET /api/ia/empresa-activa` endpoint (datos de empresa actual)
- 3.3 Filtro empresa en `/ia/logs` Flask
- 4.5 Empresa switcher refresca datos en páginas (cuando haya >1 empresa)

**Plan completo:** `.agent/planes/plan_ia_service.md`
**Plan RAG/Contexto:** `.agent/planes/rag_contexto.md`
**Tareas Antigravity:** `.agent/tareas_antigravity_rag.md`

### Arquitectura
- **Código:** `scripts/ia_service/` — módulo Python con función `consultar()`
- **BD:** `ia_service_os` en MariaDB local (8 tablas: 5 originales + 3 RAG)
- **API Flask:** puerto 5100, systemd `ia-service.service`
- **Admin:** Express puerto 9200, `os-ia-admin.service`, sirve frontend Quasar compilado
- **Uso:** cualquier proyecto llama `POST http://localhost:5100/ia/consultar`

### Stack de Contexto en 6 Capas (IMPLEMENTADO 2026-03-13)
```
CAPA 1 — System prompt base del tipo        → ia_tipos_consulta.system_prompt
CAPA 2 — RAG (fragmentos relevantes)        → ia_rag_fragmentos (FULLTEXT search) ← NUEVO
CAPA 3 — Schema BD (DDL tablas analíticas)  → esquema.py caché 1h desde Hostinger
CAPA 4 — Resumen conversación comprimido    → ia_conversaciones.resumen (≤1000 palabras)
CAPA 5 — Últimos 5 mensajes verbatim        → ia_conversaciones.mensajes_recientes ← NUEVO
CAPA 6 — Pregunta actual del usuario        → input directo
```

### 17 tablas + 1 vista en `ia_service_os`
Ver manual completo: `.agent/manuales/ia_service_manual.md`
Tablas clave: `ia_agentes`, `ia_tipos_consulta`, `ia_temas`, `ia_conversaciones`, `ia_logs`, `ia_consumo_diario`, `ia_ejemplos_sql`, `ia_rag_documentos`, `ia_rag_fragmentos`, `ia_usuarios`, `ia_empresas`, `ia_usuarios_empresas`, `ia_config`, `ia_conexiones_bd`, `ia_esquemas`, `bot_sesiones`, `bot_tablas_temp`, `v_consumo_hoy`

### Agentes configurados
| slug | modelo | Estado |
|---|---|---|
| `gemini-pro` | gemini-2.5-pro | ✅ Activo — SQL complejo |
| `gemini-flash` | gemini-2.5-flash | ✅ Activo — redacción |
| `gemini-flash-lite` | gemini-2.5-flash-lite | ✅ Activo — alto volumen |
| `gemma-router` | gemma-3-27b-it | ✅ Activo — enrutador fallback |
| `groq-llama` | llama-3.3-70b-versatile | ✅ Activo — enrutador principal (key configurada 2026-03-13) |
| `deepseek-chat` | deepseek-chat | ✅ Activo — recomendado para bot (nivel_minimo=1) |
| `deepseek-reasoner` | deepseek-reasoner | ✅ Activo (nivel_minimo=7 — solo admin) |
| `claude-sonnet` | claude-sonnet-4-6 | ✅ Activo — documentos premium |

**Estado del servicio (2026-03-13):** ✅ Activo — RAG + temas + empresa + enrutador dual (tipo+tema)
**Módulo RAG:** `scripts/ia_service/rag.py` — fragmentación + búsqueda FULLTEXT por empresa+tema
**Temas seeded:** 7 temas para ori_sil_2 (comercial, finanzas, produccion, administracion, marketing, estrategia, general)
**⚠️ `ia_rag_colecciones` fue eliminada** — reemplazada por `ia_temas` (con empresa, schema_tablas, system_prompt)

### Función principal (firma actualizada 2026-03-13)
```python
resultado = consultar(
    pregunta="¿Cuánto vendimos ayer?",
    tipo=None,           # None = enrutar automático vía Groq
    agente=None,         # None = usar preferido del tipo
    usuario_id="santi",
    canal="telegram",
    empresa="ori_sil_2", # ← multi-empresa
    tema=None,           # ← None = enrutador detecta automáticamente
    conversacion_id=None,
    nombre_usuario=None,
    contexto_extra="",   # ← para ERP: contexto de pantalla activa
    cliente=None,        # ← dict {nombre, identificacion, tipo_id, telefono, email}
                         #    para agentes de atención al cliente (CRM)
)
# Devuelve: ok, conversacion_id, respuesta, formato, tabla, sql, agente, tokens, costo_usd, log_id, tema, empresa
```

## Próximos Pasos
1. **QA bot IA** — probar en Telegram: preguntas de días de semana, consultas vacías, /agente con DeepSeek
2. **Migrar embeddings históricos** — `python3 -m scripts.ia_service.actualizar_system_prompt` (ya corrido) + `migrar_embeddings_faltantes()` cuando haya ejemplos acumulados
3. **Subir archivos de raíz a RAG** — 6 archivos (docx, pdf, pptx) → Administración en ia.oscomunidad.com
4. **Continuar app temporal** (menu.oscomunidad.com): páginas de Remisiones, módulo Clientes, módulo Productos.
5. **Limpiar contactos TEST**: `UPDATE contact SET deleted=1 WHERE description='TEST_PIPELINE_DELETE';` en BD `espocrm` + borrar en Effi manual

## Completado 2026-03-15 — QA exhaustivo ia_service + 5 bugs críticos corregidos

**Score QA: ~55/60 consultas correctas (92%)** — ver `.agent/QA_REGISTRO.md` para detalles

### Bugs corregidos
- ✅ **BUG-A — vigencia detalles producción**: `'Orden vigente'` no `'Vigente'` en `zeffi_articulos_producidos`/`zeffi_materiales`
- ✅ **BUG-B — `zeffi_trazabilidad.tipo_de_movimiento`**: valores reales son `'Creación de transacción'`/`'Anulación de transacción'`. Para filtrar por tipo usar campo `transaccion LIKE 'FACTURA DE VENTA%'`
- ✅ **BUG-C — `zeffi_trazabilidad.vigencia_de_transaccion`**: valores reales `'Transacción vigente'`/`'Transacción anulada'`
- ✅ **BUG-D — `zeffi_ordenes_compra_encabezados.estado`**: valor real `'Pendiente de recibir'` (no `'Vigente'`)
- ✅ **BUG-E — Tiempos producción negativos**: añadido filtro `TIMESTAMPDIFF >= 0` en `<reglas_sql>`

### `ia_tipos_consulta.system_prompt` estado final
- Columna: MEDIUMTEXT (ampliada de TEXT — 65K limitado)
- Tamaño: **67,454 chars / ~74KB** en BD
- Tablas documentadas: **53 tablas** (todas Hostinger)
- `<reglas_sql>`: 8+ gotchas incluyendo los 5 nuevos de esta sesión

### Datos verificados vs Hostinger
Cotizaciones: 8→$4.2M | Consignaciones: 13→$7.76M | CxC: $17.2M | CxP: $75.7M | Stock miel: 923 ud | Ticket promedio: $201,218 | Producción top: NIBS DE CACAO 77,478 ud

---

## Completado 2026-03-15 — Catálogo completo de tablas y campos (53 tablas)

**Objetivo:** Ninguna tabla ni campo debe faltar en el catálogo del sistema de IA.

### Cambios aplicados
- ✅ **`ia_tipos_consulta.system_prompt` (analisis_datos) expandido** — de 40,452 → 64,368 chars
  - `<tablas_disponibles>`: de 42 → **53 tablas** (añadidas 10 faltantes + 1 sección nueva)
  - `<diccionario_campos>`: de 19 → **53+ tablas documentadas** (añadidas ~34 tablas)
- ✅ **Columna `system_prompt` ampliada** — de `TEXT` a `MEDIUMTEXT` en `ia_tipos_consulta` (16MB límite)
- ✅ **Nuevo tema `operaciones`** creado en `ia_temas`:
  - Tablas: `zeffi_trazabilidad`, `zeffi_guias_transporte`, `zeffi_ajustes_inventario`, `zeffi_traslados_inventario`, `zeffi_inventario`, `catalogo_articulos`
- ✅ **`ia_temas` actualizados:**
  - `produccion`: añadido `zeffi_cambios_estado`
  - `finanzas`: añadido `zeffi_comprobantes_ingreso_detalle` + `zeffi_tipos_egresos`
  - `administracion`: añadidas todas las tablas de catálogos/maestros + `codigos_ciudades_dane` + `zeffi_empleados`
- ✅ **CATALOGO_TABLAS.md actualizado** — descripciones corregidas para `zeffi_guias_transporte` y `zeffi_cambios_estado`

### Tablas nuevas incorporadas al catálogo
`crm_contactos`, `zeffi_ajustes_inventario`, `zeffi_cambios_estado`, `zeffi_comprobantes_ingreso_detalle`, `zeffi_guias_transporte`, `zeffi_otros_costos`, `zeffi_tipos_egresos`, `zeffi_traslados_inventario`, `zeffi_trazabilidad`, `codigos_ciudades_dane`

### Pruebas post-actualización (3/3 OK)
- crm_contactos: 362 Cliente directo, 106 Negocio amigo ✅
- zeffi_trazabilidad: últimos movimientos de miel encontrados ✅
- zeffi_comprobantes: $1,852,036 recaudado este mes ✅

---

## Completado 2026-03-15/16 — QA completo ia_service + fixes críticos

**Score QA: 12/12 preguntas correctas** — ver `.agent/QA_REGISTRO.md` para detalles

### Fixes aplicados
- ✅ **Enrutador con fallback multi-agente** — cuando Groq está en rate limit, prueba gemma-router, luego gemini-flash-lite. Default final cambiado a `analisis_datos` (no conversacion). `scripts/ia_service/servicio.py`
- ✅ **Enrutador con contexto completo** — recibe `resumen_anterior + historial` para clasificar preguntas de seguimiento correctamente
- ✅ **Resumen delegado a Groq** — `_generar_resumen_groq()`: resumen máx 600 palabras, llamada separada posterior, no bloquea la respuesta. DeepSeek bajó de 80+ seg a ~20-30s.
- ✅ **schema_tablas corregido** — produccion tenía `zeffi_articulos` (inexistente). Corregido con las 7 tablas de producción reales. finanzas y comercial ampliados.
- ✅ **Cotizaciones estados corregidos** — estado correcto es `'Pendiente de venta'` (no 'Vigente'). System_prompt + 4 ejemplos SQL corregidos (IDs 55,67,76,85).
- ✅ **System prompt enrutador reescrito** — cubre todos los módulos: compras, producción, cotizaciones, consignación, cartera, devoluciones, rankings.
- ✅ **System prompt analisis_datos ampliado** — tablas de producción + compras en `<diccionario_campos>` + 7 nuevos ejemplos SQL.

### Datos verificados contra Hostinger
- Ventas hoy: $1,110,251 ✅ exacto
- Top 1 producto mes: Miel Os Vidrio 640g → $1,111,790 ✅ exacto
- Cotizaciones pendientes: 7 → $4,159,930 ✅ exacto
- Consignaciones activas: 13 vigentes ✅ exacto

### Próximo paso pendiente
1. Bot Telegram: probar en real con Santi

---

## Completado 2026-03-14 — Mejoras IA analítica + documentación completa
- ✅ **XML en system prompt** — `<rol>`, `<precision>`, `<tablas_disponibles>`, `<diccionario_campos>`, `<reglas_sql>`, `<ejemplos>` (34,667 chars)
- ✅ **Embeddings semánticos** — `scripts/ia_service/embeddings.py`: Google text-embedding-004 + cosine similarity. Fallback a keywords LIKE. Generación en background al guardar ejemplos.
- ✅ **Retry resultado vacío** — 0 filas → `_obtener_fecha_maxima()` + reenvío al LLM con contexto, máx 2 reintentos
- ✅ **Arquitectura dos capas** — `agente_sql` (Gemini Flash, gratis) para SQL; agente del usuario para análisis/respuesta
- ✅ **Reglas positivas** — QUÉ HACER en vez de QUÉ NO HACER en todo el system prompt
- ✅ **DeepSeek accesible** — nivel_minimo=1, primero en menú /agente, recomendado para uso diario
- ✅ **Campo `cliente` en API** — `POST /ia/consultar` acepta `cliente: {nombre, identificacion, tipo_id, telefono, email}` → inyectado en Capa 0b del system prompt. Permite agentes de atención al cliente que saben con quién hablan.
- ✅ **DDL fallback expandido** — `esquema.py`: TABLAS_RELEVANTES de 13 → 30 tablas (producción, compras, inventario, CxC, proveedores, etc.)
- ✅ **Catálogo de tablas** — `.agent/CATALOGO_TABLAS.md`: 47 tablas con descripciones de negocio (cuándo usar cada una). Referencia para el equipo humano.
- ✅ **Manual ia_service reescrito** — `.agent/manuales/ia_service_manual.md` v2.0: 20 secciones completas.
- ✅ **Principio filosófico en MANIFESTO** — "enseñar a razonar, no memorizar": cuándo agregar reglas vs cuándo mejorar el contexto general.
- ✅ **Todos los agentes activos** — groq-llama (llama-3.3-70b-versatile), deepseek-chat, deepseek-reasoner, claude-sonnet (4-6): todos con key + activo=1 en BD.

## Completado 2026-03-13
- ✅ ia-service: arquitectura RAG multitema+empresa — ia_temas, ia_rag_documentos, ia_rag_fragmentos
- ✅ ia-service: enrutador dual (tipo+tema), 6 capas de contexto, empresa multi-tenant
- ✅ ia-admin: módulo Contextos RAG — UI Vue completa + 8 endpoints API
- ✅ Documentación Antigravity Google Labs — `.agent/docs/ANTIGRAVITY_GOOGLE_LABS.md`
- ✅ Roles del equipo actualizados en MANIFESTO.md (Antigravity Google Labs ≠ Subagentes Claude)
- ✅ **Módulo Conexiones BD** — ia_conexiones_bd + ia_esquemas por tema, conector.py multi-BD, UI ConexionesPage + editor schema en Contextos, endpoints Flask /ia/conexion/test + /ia/esquema/sync
- ✅ **Multi-empresa (multi-tenant) completo** — BD migrada, backend con auth 2 pasos, frontend con header empresa + login 2 pasos
  - Nuevas tablas: `ia_empresas`, `ia_usuarios_empresas`
  - Todas las tablas existentes con campo `empresa` + auditoría
  - JWT temporal → JWT final con `empresa_activa`
  - DashboardPage: bug fecha y optional chaining corregidos

## Archivos Clave
- Scripts: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/`
- Exports: `/home/osserver/playwright/exports/`
- Docker compose: `/home/osserver/docker/docker-compose.yml`
- Cloudflare tunnel: `/etc/cloudflared/config.yml`
- Pipeline log: `logs/pipeline.log`
- Credenciales pipeline: `scripts/.env` (no está en git — Gmail + Telegram)
