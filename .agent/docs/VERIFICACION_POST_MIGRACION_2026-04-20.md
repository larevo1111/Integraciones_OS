# Verificación post-migración VPS Contabo

**Fecha**: 2026-04-20 19:20 COT
**Alcance**: verificar todos los servicios activos, dominios públicos, BDs, pipeline y bot tras la migración completa Hostinger → VPS.

---

## 1. Dominios públicos (10/10 HTTP OK)

| Dominio | Servidor | HTTP |
|---|---|---|
| `gestion.oscomunidad.com` | VPS | 200 ✅ |
| `gestion-vps.oscomunidad.com` | VPS | 200 ✅ |
| `menu.oscomunidad.com/` | VPS | 200 ✅ |
| `menu.oscomunidad.com/api/ventas/resumen-mes` | VPS | 200 ✅ (datos reales) |
| `inv.oscomunidad.com/` | VPS | 200 ✅ |
| `inv.oscomunidad.com/health` | VPS | 200 ✅ |
| `crm.oscomunidad.com` | Local (EspoCRM Docker) | 200 ✅ |
| `wp.oscomunidad.com` | VPS (Nginx+WP) | 302 (wizard aún pendiente) |
| `ia.oscomunidad.com` | Local (IA Admin) | 200 ✅ |
| `ia-api.oscomunidad.com/ia/health` | Local (IA Service) | 200 ✅ |

**Test destructivo**: `systemctl stop os-gestion` en el servidor local → `https://gestion.oscomunidad.com/` sigue HTTP 200 → confirma ruta VPS.

## 2. Servicios systemd

### VPS Contabo
```
os-gestion            active
os-erp-frontend       active
os-inventario-api     active
os-sync-api           active       (sync del repo cada 5 min)
cloudflared           active       (tunnel vps-os)
code-server           active
mariadb               active       (10.11.14, timezone -05:00)
nginx                 active       (WordPress)
php8.3-fpm            active
docker                active       (container: espocrm)
```

### Servidor local
```
os-gestion            active       (dev en localhost:9300)
os-erp-frontend       active       (dev en localhost:9100)
os-inventario-api     active       (dev en localhost:9401)
os-ia-admin           active       (ia.oscomunidad.com)
os-ialocal            active       (chat UI Ollama)
wa-bridge             active       (puerto 3100)
ia-service            active       (Flask 5100)
os-telegram-bot       active
effi-pipeline.timer   active       (cron cada 2h L-S 06-20h)
mariadb               active
cloudflared           active       (tunnel os + vps-os dual)
docker                active       (espocrm, n8n, nextcloud, nocodb, phpmyadmin)
```

## 3. Pipeline Effi — último run 2026-04-20 19:04

```
🚀 PIPELINE INICIO — 2026-04-20 19:04:11
  export_all.sh        → 28 ok 0 err [610s]
  import_all.js        → 41 tablas [35s]
  8 calcular_resumen_* → OK
  sync_catalogo        → OK
  asignar_grupo        → OK
  sync_hostinger       → 52/52 tablas → VPS ✅ [130s]
  sync_espocrm_marketing  → OK
  sync_espocrm_contactos  → 498 contactos → VPS ✅
  sync_espocrm_to_hostinger → OK
  sync_inventario_catalogo → 493 artículos → VPS ✅ [2s]
  generar_plantilla_import_effi → sin contactos pendientes
🏁 FIN — ✅ EXITOSO [total 713s]
📧 Email enviado, 📱 Telegram enviado
```

**Confirma** que los scripts Python del pipeline escriben correctamente al VPS (no a Hostinger).

## 4. Test marcador `_origen_datos` (verificación origen de datos)

### Desde servidor local (via SSH tunnel al VPS)
```
integracion → {'servidor': 'VPS_CONTABO_94.72.115.156'}
gestion     → {'servidor': 'VPS_CONTABO_94.72.115.156'}
comunidad   → {'h': 'us-imm-web1922.main-hosting.eu'}   ← Hostinger
```

### Desde VPS (modo directo, sin SSH)
```
integracion → {'servidor': 'VPS_CONTABO_94.72.115.156', 'h': 'vmi3223502'}
gestion     → {'servidor': 'VPS_CONTABO_94.72.115.156', 'h': 'vmi3223502'}
```

✅ Ambos lados convergen en las mismas BDs del VPS. `os_comunidad` sigue en Hostinger como se especificó.

## 5. Bot Telegram + IA Service

- **IA Service local** (puerto 5100): `{"ok":true,"servicio":"ia_service_os","version":"1.0"}` ✅
- **Bot Telegram**: `/getMe` responde `os_integraciones_bot` ✅

### Incidente transitorio encontrado y resuelto

Durante la verificación, el log del bot mostró errores `Conflict: terminated by other getUpdates request`. Causa: al reiniciar el servicio durante las pruebas, el proceso viejo (PID 1507547) quedó como zombie haciendo polling en paralelo con el nuevo (PID 1631381).

**Fix aplicado**: `kill -9 1507547` — zombie ya no existía al momento del comando (murió entre restart y verificación), pero el bot siguió con errores residuales unos segundos. Logs posteriores confirman estabilidad:

```
19:19:25 httpx POST .../getUpdates "HTTP/1.1 200 OK"
19:19:36 httpx POST .../getUpdates "HTTP/1.1 200 OK"
```

Sin más conflicts. Bot operativo.

**Nota**: el VPS NO tiene `os-telegram-bot.service` (enabled: not-found). Solo corre en el servidor local como corresponde (usa GPU Ollama + contexto de conversaciones localizado).

## 6. BDs — conteos en VPS coinciden con fuente Hostinger

Verificados 2026-04-20 16:48 (no se re-verifican para no ensuciar):
- `zeffi_facturas_venta_encabezados`: 943 ↔ 943
- `zeffi_remisiones_venta_encabezados`: 2335 ↔ 2335
- `zeffi_clientes`: 498 ↔ 498
- `zeffi_trazabilidad`: 67509 ↔ 67509
- `g_tareas`: 472 ↔ 472
- `g_jornadas`: 35 ↔ 35
- `g_proyectos`: 31 ↔ 31
- `g_categorias`: 16 ↔ 16
- `g_etiquetas`: 5 ↔ 5
- `resumen_ventas_facturas_mes`: 16 ↔ 16

Además el pipeline de las 19:04 escribió resúmenes actualizados al VPS (cotización/facturación fresca).

## 7. Conclusión

**✅ MIGRACIÓN ESTABLE.** Todos los servicios corriendo, dominios públicos respondiendo, pipeline escribiendo correctamente al VPS, bot Telegram estable, BDs consistentes.

### Arquitectura final verificada

```
┌─────────────────────────────────┐     ┌──────────────────────────────┐
│  Servidor LOCAL (casa)          │     │  VPS Contabo (94.72.115.156) │
│                                 │     │                              │
│  Cara al usuario:               │     │  Cara al usuario:            │
│  - ia.oscomunidad.com           │     │  - gestion.oscomunidad.com   │
│  - ia-api.oscomunidad.com       │     │  - gestion-vps.oscomunidad   │
│  - crm.oscomunidad.com (Docker) │     │  - menu.oscomunidad.com      │
│                                 │     │  - inv.oscomunidad.com       │
│  Servicios internos:            │     │  - wp.oscomunidad.com        │
│  - IA Service (Ollama GPU)      │     │  - code-vps.oscomunidad.com  │
│  - Bot Telegram                 │     │                              │
│  - Pipeline Effi (cron 2h)      │     │  BDs (producción):           │
│  - WA Bridge                    │     │  - os_integracion (54 t)     │
│                                 │     │  - os_gestion (20 t)         │
│  BDs locales:                   │     │  - os_inventario / effi_data │
│  - effi_data (staging pipeline) │     │    (clones dev del local)    │
│  - ia_service_os                │     │                              │
│  - os_inventario (producción)   │     │                              │
│  - os_whatsapp / espocrm        │     │                              │
│                                 │     │                              │
│  Dev/testing:                   │     │                              │
│  - localhost:9100/9300/9401     │     │                              │
└───────────┬─────────────────────┘     └──────────────────────────────┘
            │ SSH tunnel para BDs VPS + Hostinger (os_comunidad)
            ▼
         ┌────────────────────┐
         │ Hostinger (solo    │
         │ os_comunidad)      │
         └────────────────────┘
```

### Pendientes (no bloqueantes)

- [ ] 2026-04-27: eliminar CNAME `gestion-vps.oscomunidad.com` si sin incidentes
- [ ] 2026-04-27: revocar grants escritura en Hostinger para `u768061575_os_integracion` y `u768061575_os_gestion`
- [ ] Completar wizard de WordPress (`wp.oscomunidad.com`)
- [ ] Ajustar `sync-repo.sh` del VPS para que logee errores de git pull (hoy dice "Sin cambios" aunque falle el merge por pycache — ya solucionado al gitignorar pycache, pero el script debería ser más verbose)
