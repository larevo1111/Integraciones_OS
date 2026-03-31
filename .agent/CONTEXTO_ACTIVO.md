# Contexto Activo — Integraciones OS
**Actualizado**: 2026-03-30

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

## Trabajo activo esta semana (2026-03-30)

- **Bot Telegram — Super Agente OpenCode ✅**: Nuevo agente SAOC con multi-modelo (MiMo V2 Pro texto + Omni visión)
- **Bot Telegram — Menú simplificado ✅**: Solo 3 agentes: Qwen Local, SA Claude, SA OpenCode
- **Bot Telegram — Timeouts ✅**: SA Claude y SAOC ambos a 1200s (20 min)
- **Bot Telegram — Fix systemd ✅**: KillMode=process (pipeline sobrevive restart) + Wants ia-service (bot no muere si ia-service reinicia)
- **IA Service — Warmup Ollama ✅**: Pre-flight check antes de llamar agentes locales. Detecta Ollama caído, modelo frío, y precarga automáticamente
- **IA Service — Keywords período actual ✅**: Ampliados para forzar SQL fresco en más consultas de ventas
- **Inventario Físico ✅**: App completa en inv.oscomunidad.com. Vue 3 + FastAPI. Login, conteo, validación unidades, auditoría, fotos, grupos MP/PP/PT/INS/DS
- **Pendiente próximo**: Notificaciones jornada olvidada (activas vía cron 8pm L-V)

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
