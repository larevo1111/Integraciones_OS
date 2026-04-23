# Contexto Activo — Integraciones OS
**Actualizado**: 2026-04-23

## Completado 2026-04-23 — Detalles de Producción + reporte de reales + validación (Sistema Gestión v2.8.5)

Módulo completo para que el operario reporte consumos reales en una OP vinculada a una tarea, y nivel ≥ 5 valide (anular + crear nueva con reales + marcar Validado en Effi).

**Entregado:**
- Panel de tarea con acordeón "Detalles de producción" (visible solo si categoría=Producción + `id_op` vinculado).
- Tabla materiales + productos con columnas Material/Estimado/Real (siembra automática desde Effi, unidades desde `os_integracion.unidades_articulos`).
- 4 inputs de tiempo (Alistamiento, Producción, Empaque, Limpieza) + total calculado en vivo.
- Chip de estado (Generada gris / Procesada naranja / Validado verde / Anulada gris oscuro).
- Botón "Procesar" (responsable o nivel ≥ responsable): cambia estado de OP a Procesada en Effi.
- Botón "Validar" (solo nivel ≥ 5): anula OP original + crea nueva con reales + marca Validado. `id_op_original` queda guardado, UI muestra "OP orig: xxxx".
- Decimal tolerante (coma y punto ambos válidos).
- Observación auto-generada: "Validación OS · Reportó: X · Validó: Y · Obs OP orig: ..."

**Versiones**: v2.8.0 → v2.8.5 (12 commits entre `58e54c8` y `021c421`).

**Plan completo** + lista de archivos + pendientes: [.agent/planes/completados/PLAN_DETALLES_PRODUCCION_2026-04-20.md](planes/completados/PLAN_DETALLES_PRODUCCION_2026-04-20.md).

### Infraestructura resuelta durante la ejecución
- **DNS gestion.oscomunidad.com reapuntado al tunnel local** (no al VPS) porque VPS no puede ejecutar Playwright confiablemente contra Effi (Effi limita acciones según IP). Comando: `cloudflared tunnel route dns --overwrite-dns 9cacb3dc-... gestion.oscomunidad.com` (requiere `cert.pem` del VPS). Hostname quitado del config del VPS (`/etc/cloudflared/config.yml`).
- **SSH jump tunnel a Hostinger**: la IP del local está bloqueada por Hostinger. Nuevo servicio `tunnel-hostinger.service` mantiene SSH via VPS Contabo como jumphost. Expone MySQL Hostinger como `127.0.0.1:3313` en el local. `.env` → `DB_COMUNIDAD_SSH_HOST=direct`, `DB_COMUNIDAD_REMOTE_PORT=3313`.
- **`db.js` pool dinámico**: antes cacheaba el pool al arrancar; tras reconexión SSH quedaba obsoleto ("Pool is closed"). Ahora los getters leen el pool actual del helper central en cada acceso.
- **comunidad opcional al arranque**: si Hostinger tarda en responder, el server arranca igual y reintenta en background cada 15s. `/procesar` y `/validar` usan `req.usuario.nombre` del JWT (no dependen de comunidad).

## Módulos activos en paralelo

| Módulo | Archivo de contexto | Estado actual | Prioridad |
|---|---|---|---|
| Servicio IA + Bot Telegram | [contextos/ia_service.md](contextos/ia_service.md) | Super Agente activo, mejora continua cron | Alta |
| Pipeline Effi | [contextos/pipeline_effi.md](contextos/pipeline_effi.md) | Estable, 18 pasos activos | Normal |
| ERP Frontend | [contextos/erp_frontend.md](contextos/erp_frontend.md) | Módulo Ventas completo | Normal |
| Sistema Gestión OS | [contextos/sistema_gestion.md](contextos/sistema_gestion.md) | Jornadas ✅ + Tareas ✅ + Detalles de Producción ✅ (v2.8.5) | Alta |
| EspoCRM | [contextos/espocrm.md](contextos/espocrm.md) | Estable — sin trabajo activo | — |
| Inventario Físico | [contextos/inventario_fisico.md](contextos/inventario_fisico.md) | Operativo — inv.oscomunidad.com, inventarios completos + parciales | Alta |
| Producción | `produccion/` + `scripts/produccion/api.py:9600` | React + Shadcn/ui + Tailwind (style Linear), BD `os_produccion` | Operativo — solicitudes → OPs Effi via Playwright |
| WA Bridge | `wa_bridge/` | ✅ Activo — puerto 3100, número 573214550933 vinculado | Normal |

## Trabajo activo (2026-04-23)

### Completado 2026-04-23 — Libro de Recetas de Producción

**Objetivo**: eliminar la deducción manual de recetas para cada OP. Catálogo maestro con receta por producto.

**Infraestructura**:
- BD VPS `inventario_produccion_effi`: 4 tablas nuevas (`prod_recetas`, `_materiales`, `_productos`, `_costos`)
- 8 scripts en `scripts/produccion/libro_recetas/`:
  - `listar_universo.py`, `dossier_producto.py`, `construir_receta.py`, `simular_op.py`, `persistir_receta.py`
  - `sugerir_atribuido.py` — motor propio que atribuye materiales en OPs multi-producto (afinidad semántica + match por cantidad + share)
  - `override_receta.py` — módulo para overrides manuales con razonamiento de Claude/Santi
  - `persistir_todas.py` — procesamiento masivo
- Endpoints API: `/api/recetas`, `/api/recetas/{cod}`, `/api/recetas/{cod}` PATCH, `/api/recetas/stats/resumen`
- UI: `/recetas` (lista con OsDataTable + resumen por familia) y `/recetas/:cod` (detalle con materiales/productos/costos + tarjetas económicas + textarea razonamiento + botones validar/devolver)

**Cobertura**: 108/108 productos con receta (productos producidos desde 2025-01-01). 72/108 validadas (67%). Los 36 en borrador son productos de 1-2 OPs que requieren razonamiento específico con Santi.

**Patrones documentados en skill `produccion-recetas` §12**: densidades (miel 1.28, polen 0.65, propóleo 1.30 g/ml), mapeo envase-peso, query SQL para identificar envase por match de cantidad.

### Completado 2026-04-20 — Inventario parcial abril + módulo Producción

**Inventario físico:**
- Inventario completo marzo 2026: cerrado, ajustes aplicados (361+362+363), informe PDF + análisis IA con Gemini
- Primer inventario parcial 20 abril: 28→33 artículos (con esterilizados), ajustes aplicados, cero artículos negativos en Effi
- Inventarios parciales operativos con preselección inteligente (`/api/inventario/sugerir-articulos`)
- Pestaña Costos con OsDataTable dark, informe PDF automático, análisis IA ejecutivo
- Observaciones en BD (`inv_observaciones`): automáticas + manuales (error_conteo, correccion_costo, hallazgo, manual)
- Soporte hora de corte intra-día (`--hora HH:MM:SS`)
- Envases normales vs esterilizados (mapeo)

**Timezone effi_data:**
- Toda `effi_data` uniformizada en UTC-5: `import_all.js` convierte `zeffi_cambios_estado.f_cambio_de_estado` de UTC a COT

**Costo:**
- Migrado de `costo_promedio` a `costo_manual` en todo el sistema (inventario, resúmenes, informes)

**Módulo Producción (2026-04-21):**
- Directorio: `produccion/` — stack React + Shadcn/ui + Tailwind v4 (style Linear.app)
- API: FastAPI `scripts/produccion/api.py` puerto 9600 (systemd `os-produccion-api`)
- BD: `os_produccion.solicitudes_produccion` (estados: solicitado/programado/en_produccion/producido/validado/cancelado)
- Estado: **operativo** — Jenifer programa solicitudes, Santi las convierte en OPs de Effi
- Tabla OsDataTable portada a React (filtros, subtotales, exportar, modo claro/oscuro)
- Panel detalle lateral al click en fila (sheet drawer)
- Scripts Playwright Effi (creados 2026-04-21):
  - `scripts/import_orden_produccion.js` — crea OPs en Effi desde JSON (probado con OP 2182)
  - `scripts/anular_orden_produccion.js` — anula OPs por ID
- **Logica recetas verificada**: productos se dividen en "lote fijo" (cobertura 73%, tabletas) vs "escalable por unidad" (nibs 100g, miel 640g). Doc en `MANUAL_EFFI_PRODUCCION_INVENTARIOS.md §3`.

### Completado 2026-04-20 — BDs Hostinger marcadas deprecated
- `u768061575_os_integracion` y `u768061575_os_gestion` en Hostinger: todas las tablas renombradas con prefijo `_deprecated_` + tabla `_DEPRECATED_README` con aviso y ruta al VPS.
- Motivo: prevenir que futuros agentes (Claude Code / Antigravity / scripts) consulten datos muertos. Si alguien hace `SELECT ... FROM zeffi_facturas_venta_encabezados` apuntando a Hostinger → error "table not found" (fail-fast).
- `u768061575_os_comunidad` intacta (ERP real Effi, prohibido tocar).
- PWA Service Worker: confirmado que `skipWaiting: true` + `clientsClaim: true` ya están en `quasar.config.js` y el `sw.js` compilado incluye `self.skipWaiting()` + `e.clientsClaim()` + `cleanupOutdatedCaches()`. Las PWAs se actualizan automáticamente al próximo abrir.

### Completado 2026-04-20 — Corte DNS gestion al VPS (migración completada)
- `gestion.oscomunidad.com` → VPS tunnel (antes: servidor local).
- Precondición verificada: `JWT_SECRET` y `GOOGLE_CLIENT_ID` idénticos local/VPS → usuarios NO perdieron sesión.
- Verificado con test destructivo: `systemctl stop os-gestion` en local → gestion.oscomunidad.com sigue HTTP 200.
- `gestion-vps.oscomunidad.com` se deja activo 7 días como red de seguridad. Programado eliminar 2026-04-27.
- Servidor local queda como **dev** (localhost:9300 para testing) y host de **servicios internos** que usan GPU/recursos locales (IA Service, Bot Telegram, Pipeline Effi, WA Bridge, EspoCRM Docker).

### Completado 2026-04-20 — Corte DNS menu + inv al VPS
- `menu.oscomunidad.com` → VPS tunnel (antes: servidor local)
- `inv.oscomunidad.com` → VPS tunnel (antes: servidor local)
- Verificado con test destructivo: `systemctl stop os-erp-frontend.service` en local → menu.oscomunidad.com sigue HTTP 200 (confirma ruta VPS).
- Testing local vía `http://localhost:9100`, `:9300`, `:9401` (mismas BDs del VPS vía SSH tunnel).

### Completado 2026-04-20 — VPS apps funcionando con `.env` propio
- Helper `lib/db_conn.js`/`scripts/lib/db_conn.py` extendido con **modo directo**: si `SSH_HOST=localhost`, salta tunnel SSH y conecta directo al MariaDB del mismo servidor.
- Creado `integracion_conexionesbd.env` en el VPS con modo directo para integracion+gestion, SSH a Hostinger para comunidad.
- Instaladas deps Python (`pymysql`, `sshtunnel`, `python-dotenv`) en el venv del VPS.
- `.gitignore` ajustado: `__pycache__/` y `*.pyc` removidos del tracking (59 archivos).
- Arreglado `sync-repo.sh` del VPS que fallaba silenciosamente por conflicto de pycache sin trackear.

### Completado 2026-04-20 — Migración Hostinger → VPS Contabo (BDs)
- **`os_integracion` y `os_gestion` migradas de Hostinger a VPS Contabo** (94.72.115.156).
- Servicios LOCALES intactos: `effi_data`, `ia_service_os`, `espocrm`, `os_inventario`, `os_whatsapp` siguen en servidor de casa.
- `os_comunidad` se queda en Hostinger (ERP real, prohibido tocar).
- Proceso del corte:
  1. Freeze 7 servicios systemd
  2. Dump delta Hostinger → re-import VPS (DROP+CREATE+restore, re-grant)
  3. `cp integracion_conexionesbd.vps.env integracion_conexionesbd.env` (switch)
  4. Restart servicios
  5. Golden path OK: Gestión login + tareas + ERP ventas + IA bot + Python helpers
- Backup Hostinger conservado: `/home/osserver/Proyectos_Antigravity/backups/u768061575_os_{integracion,gestion}/`
- Plan completo: `.agent/planes/completados/migracion_bd_hostinger_a_vps_contabo_2026-04-20.md`
- SSH key osserver@VPS autorizada desde servidor local (id_ed25519).
- MariaDB VPS: `default-time-zone=-05:00` nativo.

### Completado 2026-04-20 — Centralización de conexiones BD
- **Todas las credenciales de BD movidas a `integracion_conexionesbd.env`** (raíz del repo, gitignored).
- Plantilla versionada: `integracion_conexionesbd.env.example`.
- Helpers: `lib/db_conn.js` (Node) y `scripts/lib/db_conn.py` (Python). Cargan el `.env` automáticamente.
- 35 archivos refactorizados (5 servicios Node + 30 scripts Python): ningún host/user/pass/database hardcoded.
- API Node: `db.local('effi_data')`, `db.integracion()`, `db.gestion()`, `db.comunidad()`.
- API Python: `with local(db) as conn:`, `with integracion() as conn:`, `with gestion()`, `with comunidad()`, o `cfg_local()` / `cfg_remota_ssh(prefijo)` / `cfg_remota_db(prefijo)` para scripts legados.
- Validado: 7 servicios reiniciados y respondiendo. Smoke Python OK. Próximo paso: migrar `os_integracion` y `os_gestion` al VPS → solo editando el `.env`.

### Completado sesiones anteriores
- **Hostinger inalcanzable**: ISP bloqueaba la IP. Solución: Cloudflare WARP instalado (`warp-cli connect/disconnect`).
- **OpenCode modelo removido**: `mimo-v2-pro-free` ya no existe en OpenCode. Cambiado a `opencode/qwen3.6-plus-free` en `superagente_oc.py`.
- **Bot conflictos polling**: Múltiples restarts lo resolvieron. Causado por cambios de red (WARP).
- **ialocal sobreescribía modelo Ollama**: `ialocal/server.js` usaba `qwen2.5-coder:14b` como default, desplazaba a `qwen-coder-ctx` de VRAM. Corregido a `qwen-coder-ctx`.
- **Auto-corrección LIKE**: `_corregir_igualdad_nombres()` en servicio.py convierte `vendedor = 'X'` → `LIKE '%X%'` antes de ejecutar SQL.
- **Agregados pre-calculados**: `_calcular_agregados()` calcula SUM/MAX/MIN de columnas numéricas y los inyecta en el prompt de respuesta para que el LLM no sume mal.
- **Validación tablas inexistentes**: `obtener_columnas_reales()` ahora detecta tablas que no existen y sugiere alternativas.
- **Diagnóstico diario**: `scripts/diagnostico_diario.py` cron 6:30am. Revisa servicios, BDs, Hostinger, WARP, GPU, apps, pipeline, bot, disco. Envía reporte por bot principal con botón "Abrir con Claude Code" si hay fallos.

### ⚠️ PROBLEMA ABIERTO: Ollama lento (200s vs 14s en benchmark)

**Hechos comprobados:**
- Benchmark 29 marzo: modelo `qwen-coder-ctx` (qwen2.5-coder:14b + num_ctx=28672), 44K tokens input, latencia 12-17s, 15/15 SQL correctas
- Hoy 3 abril: mismo modelo `qwen-coder-ctx`, 25K tokens reales (medido con API nativa), latencia 180-200s, 10/15 SQL correctas
- Ollama versión 0.18.3, binario del 25 de marzo (no cambió)
- GPU: RTX 3060 12GB. Modelo ocupa 10.2GB VRAM.
- Ollama hace offloading parcial a RAM: 21 de 49 capas del modelo van a RAM, 284 graph splits por batch
- Consulta directa con prompt chico (32 tokens): 0.3s prompt eval + 22s load (primera vez) o 0.1s load (modelo ya cargado)
- Swap al 100% (8GB/8GB)

**Lo que NO se ha determinado:**
- Si el benchmark tenía el mismo offloading o si en ese momento cabía completo en VRAM
- Por qué la misma configuración da 14s entonces y 200s ahora
- Si hay una regresión de Ollama con offloading parcial (hay issues reportados en GitHub: #12037, #12504, #11060)
- Si el swap al 100% está causando que las capas en RAM se vayan a disco

**Configuración Ollama actual:**
- Agente BD: `ollama-qwen-coder` → `modelo_id=qwen-coder-ctx`
- Modelo: FROM qwen2.5-coder:14b, PARAMETER num_ctx 28672
- Endpoint: `http://localhost:11434/v1`
- Provider: `openai_compat.py`
- El endpoint /v1 reporta tokens INCORRECTOS (reporta 57K cuando son 25K reales)
- Ollama está activo pero el modelo no debe estar cargado en VRAM hasta que se necesite (warmup automático)

## Regla de actualización

Al empezar a trabajar en un módulo → leer su contexto.
Al terminar tarea significativa → actualizar el contexto del módulo.
MEMORY.md de Claude siempre refleja el módulo activo y su estado.

---

## Arquitectura general del sistema

### BDs

| BD | Ubicación | Rol |
|---|---|---|
| `effi_data` | MariaDB local | Staging pipeline (41 tablas zeffi_* + catalogo_articulos) |
| `ia_service_os` | MariaDB local | Servicio IA (17 tablas + 1 vista) |
| `os_whatsapp` | MariaDB local | WA Bridge (wa_config, wa_contactos, wa_mensajes_entrantes, wa_mensajes_salientes) |
| `espocrm` | MariaDB local | CRM (488 contactos) |
| `nocodb_meta` | MariaDB local | Metadatos NocoDB |
| `u768061575_os_integracion` | Hostinger | Fuente de verdad: 51 tablas (41 zeffi + 8 resumen + crm_contactos + catalogo_articulos) |
| `u768061575_os_gestion` | Hostinger | Sistema Gestión OS |
| `os_inventario` | MariaDB local | Inventario físico (inv_conteos, inv_rangos, inv_auditorias, inv_teorico, inv_observaciones) |
| `u768061575_os_comunidad` | Hostinger | **ERP REAL — PROHIBICIÓN ABSOLUTA, NO TOCAR** |

MariaDB corre en el **host** (systemd), NO en Docker — puerto 3306.
Credenciales locales: `osadmin` / `Epist2487.`

### Servicios activos

| Servicio | Puerto | Systemd | URL |
|---|---|---|---|
| ERP Frontend API | 9100 | `os-erp-frontend` | menu.oscomunidad.com |
| IA Admin | 9200 | `os-ia-admin.service` | ia.oscomunidad.com |
| Sistema Gestión | 9300 | `os-gestion.service` | gestion.oscomunidad.com |
| IA Service Flask | 5100 | `ia-service.service` | interno |
| WA Bridge | 3100 | `wa-bridge.service` | interno — ver `.agent/CATALOGO_APIS.md` |
| Effi Webhook Flask | 5050 | `effi-webhook.service` | interno |
| Inventario API | 9401 | `os-inventario-api.service` | inv.oscomunidad.com |
| EspoCRM | 8083 | Docker | crm.oscomunidad.com |
| NocoDB | — | Docker | nocodb.oscomunidad.com |

### Archivos clave globales

| Archivo | Propósito |
|---|---|
| `scripts/orquestador.py` | Orquestador pipeline (cada 2h Lun-Sab 06:00-20:00) |
| `scripts/.env` | Credenciales (NO en git) |
| `logs/pipeline.log` | Log del pipeline |
| `/home/osserver/docker/docker-compose.yml` | Docker compose |
| `/etc/cloudflared/config.yml` | Cloudflare tunnel |
| `.agent/CATALOGO_SCRIPTS.md` | Catálogo completo de scripts |
| `.agent/CATALOGO_APIS.md` | Catálogo de todas las APIs HTTP internas (ia_service, wa_bridge) |
| `.agent/CATALOGO_TABLAS.md` | 47+ tablas con descripciones |
| `.agent/MANIFESTO.md` | Visión, arquitectura y reglas técnicas |
| `.agent/manuales/ia_service_manual.md` | Manual IA service v2.7 |
