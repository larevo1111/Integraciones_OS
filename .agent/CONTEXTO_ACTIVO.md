# Contexto Activo — Integraciones OS
**Actualizado**: 2026-03-26

## Módulos activos en paralelo

| Módulo | Archivo de contexto | Estado actual | Prioridad |
|---|---|---|---|
| Servicio IA + Bot Telegram | [contextos/ia_service.md](contextos/ia_service.md) | Super Agente activo, mejora continua cron | Alta |
| Pipeline Effi | [contextos/pipeline_effi.md](contextos/pipeline_effi.md) | Estable, 18 pasos activos | Normal |
| ERP Frontend | [contextos/erp_frontend.md](contextos/erp_frontend.md) | Módulo Ventas completo | Normal |
| Sistema Gestión OS | [contextos/sistema_gestion.md](contextos/sistema_gestion.md) | Jornadas ✅ + Tareas ✅ activos | Alta |
| EspoCRM | [contextos/espocrm.md](contextos/espocrm.md) | Integración bidireccional activa | Normal |

## Trabajo activo esta semana (2026-03-26)

- **Sistema Gestión — Jornadas ✅**: Módulo completo (check-in/out, pausas, turno nocturno, 6h gap, reabrir 1h, GestionTable, popup detalle, admin edit, observaciones, notificación Telegram 8pm)
- **Sistema Gestión — Tareas ✅**: TickTick-style activo, fix mobile subtask button + contraste
- **Sistema Gestión — Infra**: SSH tunnel auto-reconnect en db.js, UTC_TIMESTAMP fix en equipo
- **IA Service**: Super Agente Claude Code activo en bot, mejora continua cada 6h
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
| `espocrm` | MariaDB local | CRM (488 contactos) |
| `nocodb_meta` | MariaDB local | Metadatos NocoDB |
| `u768061575_os_integracion` | Hostinger | Fuente de verdad: 51 tablas (41 zeffi + 8 resumen + crm_contactos + catalogo_articulos) |
| `u768061575_os_gestion` | Hostinger | Sistema Gestión OS |
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
| Effi Webhook Flask | 5050 | `effi-webhook.service` | interno |
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
| `.agent/CATALOGO_TABLAS.md` | 47+ tablas con descripciones |
| `.agent/MANIFESTO.md` | Visión, arquitectura y reglas técnicas |
| `.agent/manuales/ia_service_manual.md` | Manual IA service v2.7 |
