# Contexto Activo — Integraciones OS
**Actualizado**: 2026-04-20

## Módulos activos en paralelo

| Módulo | Archivo de contexto | Estado actual | Prioridad |
|---|---|---|---|
| Servicio IA + Bot Telegram | [contextos/ia_service.md](contextos/ia_service.md) | Super Agente activo, mejora continua cron | Alta |
| Pipeline Effi | [contextos/pipeline_effi.md](contextos/pipeline_effi.md) | Estable, 18 pasos activos | Normal |
| ERP Frontend | [contextos/erp_frontend.md](contextos/erp_frontend.md) | Módulo Ventas completo | Normal |
| Sistema Gestión OS | [contextos/sistema_gestion.md](contextos/sistema_gestion.md) | Jornadas ✅ + Tareas ✅ activos | Alta |
| EspoCRM | [contextos/espocrm.md](contextos/espocrm.md) | Estable — sin trabajo activo | — |
| Inventario Físico | [contextos/inventario_fisico.md](contextos/inventario_fisico.md) | App activa inv.oscomunidad.com, BD + scripts listos | Alta |
| WA Bridge | `wa_bridge/` | ✅ Activo — puerto 3100, número 573214550933 vinculado | Normal |

## Trabajo activo (2026-04-20)

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
| `os_inventario` | MariaDB local | Inventario físico (inv_conteos, inv_rangos, inv_auditorias) |
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
