# VPS Contabo — Configuración Completa

**Creado**: 2026-04-10
**Propósito**: Servidor de producción para las apps de Origen Silvestre. Reemplaza la dependencia del servidor local de casa (que se pausa cuando se cae el internet).

---

## Especificaciones

| Campo | Detalle |
|---|---|
| Proveedor | Contabo Cloud VPS 20 NVMe |
| Plan | Cloud VPS 20 NVMe |
| IP pública | `94.72.115.156` (fija) |
| Hostname | `vmi3223502` |
| Ubicación | St. Louis, US-Central |
| OS | Ubuntu 24.04 LTS |
| Kernel | 6.8.0-106-generic |
| CPU | 6 vCPU (AMD EPYC) |
| RAM | 12 GB |
| Disco | 100 GB NVMe (96GB usable) |
| Swap | Sin swap configurado |
| Customer ID Contabo | 14849281 |
| Order ID | 14849282 |

---

## Acceso

| Método | Comando / URL |
|---|---|
| SSH root | `ssh root@94.72.115.156` — clave: ver `.agent/.servers.env` |
| SSH osserver | `ssh osserver@94.72.115.156` — misma clave |
| VS Code Remote SSH | Host `vps-os` → ver config abajo |
| code-server (browser) | `http://94.72.115.156:9400` — clave: ver `.agent/.servers.env` |

**Config SSH** (`~/.ssh/config`):
```
Host vps-os
    HostName 94.72.115.156
    User osserver
    IdentityFile ~/.ssh/id_ed25519
```

---

## Stack instalado

| Herramienta | Versión | Notas |
|---|---|---|
| Node.js | 20.20.2 LTS | via NodeSource |
| Python | 3.12.3 | sistema |
| Python venv | `/home/osserver/venv` | para las apps Python |
| MariaDB | 10.11.14 | puerto 3306 local |
| Docker | 29.4.0 | activo y habilitado |
| Nginx | 1.24.0 | activo — reverse proxy futuro |
| Playwright | 1.59.1 | + Chromium headless en `/root/.cache/ms-playwright/` |
| Claude Code | 2.1.101 | instalado global con npm |
| cloudflared | 2026.3.0 | tunnel `vps-os` activo |
| code-server | latest | VS Code en browser |
| Git | 2.43.0 | — |

---

## Usuarios del sistema

| Usuario | Rol |
|---|---|
| `root` | Administración del servidor |
| `osserver` | Corre todos los servicios de la app |

---

## Servicios systemd activos

| Servicio | Puerto | Descripción |
|---|---|---|
| `os-gestion.service` | 9300 | Sistema Gestión OS (Node.js) |
| `os-erp-frontend.service` | 9100 | ERP Frontend (Node.js) |
| `os-inventario-api.service` | 9401 | Inventario API (Python FastAPI) |
| `code-server.service` | 9400 | VS Code en browser |
| `cloudflared.service` | — | Cloudflare Tunnel `vps-os` |
| `mariadb.service` | 3306 | Base de datos |
| `docker.service` | — | Docker daemon |
| `nginx.service` | 80 | Sirviendo WordPress (`/var/www/wordpress`) |
| `php8.3-fpm.service` | socket | PHP-FPM para WordPress |

**Docker (EspoCRM):**
```
espocrm: Up — puerto 8083 — BD: osadmin@host.docker.internal/espocrm
Volumes: /opt/espocrm/html (178MB), /opt/espocrm/data (4.4MB)
docker-compose: /opt/espocrm/docker-compose.yml
```

**WordPress:**
```
Archivos: /var/www/wordpress
Config:   wp-config.php → BD wordpress / osadmin / localhost
Nginx:    /etc/nginx/sites-enabled/wordpress → puerto 80
Estado:   Wizard de instalación pendiente (completar en wp.oscomunidad.com)
```

**Acceso al VPS (SSH puerto 22 bloqueado):**
⚠️ El puerto 22 está bloqueado por el firewall de Contabo (panel cloud, no el OS).
- UFW: inactivo. iptables: sin reglas. fail2ban: sin IPs baneadas.
- **Administrar via code-server**: `http://94.72.115.156:9400`
- **Para habilitar SSH**: customer.contabo.com → VPS → Networking → Firewall → agregar TCP 22

**Arrancar/parar servicios (desde code-server terminal):**
```bash
systemctl status os-gestion
systemctl restart os-gestion
journalctl -u os-gestion -f
```

---

## Bases de datos (MariaDB local VPS)

| BD | Tablas | Tamaño | Rol |
|---|---|---|---|
| **`os_integracion`** | 54 | ~66 MB | **PRODUCCIÓN** desde 2026-04-20 — fuente de verdad del pipeline Effi |
| **`os_gestion`** | 20 | ~1 MB | **PRODUCCIÓN** desde 2026-04-20 — Sistema Gestión OS (tareas, jornadas) |
| `os_inventario` | 9 | ~1.2 MB | Dev/dup 2026-04-10 (producción sigue en servidor local) |
| `effi_data` | 44 | ~64 MB | Dev/dup 2026-04-10 (staging real en servidor local) |
| `espocrm` | 140 | ~14 MB | Dev (Docker EspoCRM) |
| `sos_erp`, `sos_master_erp`, `wordpress` | — | — | Legacy / WordPress |

**Timezone MariaDB**: `default-time-zone = "-05:00"` en `/etc/mysql/mariadb.conf.d/50-server.cnf`. `NOW()` devuelve hora Colombia nativo.

**Usuarios MySQL (creados 2026-04-20):**
- `os_integracion@{127.0.0.1,localhost}` — ALL PRIVILEGES en `os_integracion`
- `os_gestion@{127.0.0.1,localhost}` — ALL PRIVILEGES en `os_gestion`
- `osadmin@localhost` — root de administración (para `effi_data`, `os_inventario`)

**Acceso desde servidor local (producción)**: SSH tunnel automático vía helpers `lib/db_conn.js` y `scripts/lib/db_conn.py`, que leen `integracion_conexionesbd.env`. Usuario SSH: `osserver` con key `~/.ssh/id_ed25519`.

---

## Cloudflare Tunnel

| Campo | Detalle |
|---|---|
| Nombre | `vps-os` |
| ID | `fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a` |
| Credentials | `/root/.cloudflared/fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a.json` |
| Config | `/etc/cloudflared/config.yml` |
| Estado | Activo — pero **DNS siguen apuntando al servidor local** |

**Dominios configurados en el tunnel VPS (`vps-os`):**
```
wp.oscomunidad.com           → 80    (WordPress — DNS apunta al VPS ✅)
code-vps.oscomunidad.com     → 9400  (code-server VPS ✅)
gestion-vps.oscomunidad.com  → 9300  (Gestión en VPS, instancia dev/backup ✅)
gestion.oscomunidad.com      → 9300  (Reservado para cuando se corte DNS de producción)
menu.oscomunidad.com         → 9100  (Reservado)
inv.oscomunidad.com          → 9401  (Reservado)
```

**Dominios configurados en el tunnel LOCAL (`os` — ID `9cacb3dc`):**
```
gestion.oscomunidad.com    → 9300  (Producción ✅)
menu.oscomunidad.com       → 9100  (Producción ✅)
inv.oscomunidad.com        → 9401  (Producción ✅)
crm.oscomunidad.com        → 8083  (EspoCRM producción ✅)
ia-api.oscomunidad.com     → 5100  (IA Service expuesto para que el VPS lo use ✅)
+ 13 servicios más (nocodb, n8n, nextcloud, grafana, etc.)
```

⚠️ **Regla de SSL de Cloudflare gratis**: solo cubre 1 nivel (`*.oscomunidad.com`). Por eso el dev usa `gestion-vps.oscomunidad.com` (con guión) y no `vps.gestion.oscomunidad.com` (2 niveles, no cubierto).

**Para cortar dominios al VPS** (cuando se decida invertir local/VPS):
```bash
# Desde el servidor local (tiene cert.pem):
cloudflared tunnel route dns --overwrite-dns fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a gestion.oscomunidad.com
cloudflared tunnel route dns --overwrite-dns fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a menu.oscomunidad.com
cloudflared tunnel route dns --overwrite-dns fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a inv.oscomunidad.com
```

---

## SSH key de Hostinger en VPS

La key `sos_erp` está copiada en `/home/osserver/.ssh/sos_erp` — permite que las apps hagan el tunnel SSH a Hostinger MySQL.

Verificar: `ssh -i ~/.ssh/sos_erp -p 65002 u768061575@109.106.250.195 echo OK`

---

## Estructura del repo

```
/home/osserver/Proyectos_Antigravity/Integraciones_OS/  ← repo clonado de GitHub
/home/osserver/venv/                                     ← venv Python
/home/osserver/.ssh/sos_erp                              ← SSH key Hostinger
/home/osserver/.config/code-server/config.yaml          ← config code-server
/root/.cloudflared/                                      ← credenciales tunnel
/etc/cloudflared/config.yml                             ← config tunnel
```

---

## Estrategia de dominios (actualizado 2026-04-20 corte parcial)

**Decisión**: migración gradual de producción del servidor local al VPS. Gestión se queda en local como producción estable mientras se testea el VPS. ERP e inventario ya cortados al VPS.

| Dominio | Apunta a | Rol | Notas |
|---|---|---|---|
| `gestion.oscomunidad.com` | **VPS** ← 2026-04-20 | **Producción en VPS** | Corte DNS ejecutado (JWT_SECRET idéntico → sesiones persistieron) |
| `gestion-vps.oscomunidad.com` | VPS | Redundante/testing | Programado eliminar 2026-04-27 (red de seguridad 7 días) |
| `menu.oscomunidad.com` | **VPS** ← 2026-04-20 | **Producción en VPS** | Corte DNS ejecutado |
| `inv.oscomunidad.com` | **VPS** ← 2026-04-20 | **Producción en VPS** | Corte DNS ejecutado |
| `crm.oscomunidad.com` | Local | **Producción** | EspoCRM Docker local — no migrado |
| `code-vps.oscomunidad.com` | VPS | code-server VS Code remoto | — |
| `wp.oscomunidad.com` | VPS | WordPress (solo VPS) | — |

### Arquitectura de datos tras el corte BD (2026-04-20)

Las BDs `os_integracion` y `os_gestion` viven ahora en el VPS. Hay una sola fuente de verdad, por lo que **cualquier app** (sea local o VPS) lee/escribe las mismas tablas:

- Apps en **servidor local** → SSH tunnel al VPS (`lib/db_conn.js` modo SSH)
- Apps en **VPS** → conexión directa al MariaDB del propio VPS (`lib/db_conn.js` modo directo, detecta `SSH_HOST=localhost`)
- `os_comunidad` sigue en Hostinger (ERP real Effi, prohibido tocar) — ambos lados la consultan vía SSH tunnel

### Testing / dev

Para probar cambios antes de deployar, Santi usa el servidor local en `localhost`:
- `http://localhost:9300` → Gestión (conecta al VPS via SSH tunnel, misma BD que producción)
- `http://localhost:9100` → ERP
- `http://localhost:9401` → Inventario

Google OAuth ya tiene `localhost:9300` registrado como origen (por el dev server `quasar dev`), así que el login funciona en local sin configuración extra.

⚠️ **Cuidado**: al ser la misma BD que producción, una escritura en localhost también afecta producción. Escrituras de prueba deben hacerse con conciencia.

### Corte DNS (cómo se hizo)

Desde el servidor local, con `cloudflared` autenticado al tunnel VPS:
```bash
cloudflared tunnel route dns --overwrite-dns fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a menu.oscomunidad.com
cloudflared tunnel route dns --overwrite-dns fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a inv.oscomunidad.com
```

Para **revertir** al tunnel local:
```bash
cloudflared tunnel route dns --overwrite-dns 9cacb3dc menu.oscomunidad.com
cloudflared tunnel route dns --overwrite-dns 9cacb3dc inv.oscomunidad.com
```

Verificación usada: detener el servicio en el servidor local y comprobar que la URL sigue respondiendo HTTP 200 → confirma que el tráfico va al VPS.

## IA Service: cómo lo llama el VPS

El IA Service corre **solo en local** (usa GPU/Ollama). El VPS no puede tenerlo.
Pero el VPS **sí necesita llamarlo** (ej: sugerir categoría de tareas).

**Solución**: se expuso el IA Service por Cloudflare Tunnel local como `ia-api.oscomunidad.com`.

- **Desde local**: `IA_SERVICE_URL=http://127.0.0.1:5100` (default, no necesita .env)
- **Desde VPS**: `IA_SERVICE_URL=https://ia-api.oscomunidad.com` (configurado en `.env`)

El código detecta protocolo http/https automáticamente. Misma URL path (`/ia/simple`), mismo contrato, sin if/else en el código. Ver `sistema_gestion/api/server.js` → función `sugerir-categoria`.

## Sync repo local → VPS (cron + API)

El VPS pull del repo automáticamente cada 5 min. También tiene un endpoint HTTP para pull manual.

| Componente | Ubicación |
|---|---|
| Script sync | `/home/osserver/sync-repo.sh` (VPS) |
| Cron | cada 5 min (`crontab -u root`) |
| Log | `/home/osserver/sync.log` (VPS) |
| API HTTP | `http://94.72.115.156:9500/sync` (POST, header `x-token: os-sync-2487`) |
| Servicio | `os-sync-api.service` (Node.js) |

El script detecta qué archivos cambiaron y reinicia solo los servicios afectados:
- `sistema_gestion/` → reinicia `os-gestion`
- `frontend/` → reinicia `os-erp-frontend`
- `scripts/inventario/` → reinicia `os-inventario-api`

**Sync manual desde cualquier lado:**
```bash
curl -X POST -H "x-token: os-sync-2487" http://94.72.115.156:9500/sync
```

## Estado de migración (2026-04-18)

| App | VPS listo | DNS | Notas |
|---|---|---|---|
| Sistema Gestión | ✅ | Prod local + `gestion-vps.*` en VPS | IA categoría funciona en ambos |
| ERP Frontend | ✅ | Solo local (prod) | VPS listo pero sin dev subdom |
| Inventario | ✅ | Solo local (prod) | VPS listo pero sin dev subdom |
| EspoCRM | ✅ Docker | Solo local (prod) | VPS Docker puerto 8083 |
| WordPress | ✅ | `wp.oscomunidad.com` → VPS ✅ | **Pendiente: completar wizard** |
| code-server VPS | ✅ | `code-vps.oscomunidad.com` ✅ | 25 extensiones + settings copiados |
| IA Service | ❌ no aplica | `ia-api.oscomunidad.com` (local) | Se queda local, expuesto para VPS |
| Bot Telegram | ❌ no aplica | — | Se queda local |
| Pipeline Effi | ❌ no aplica | — | Se queda local |
| WA Bridge | ❌ no aplica | — | Se queda local |

**Recursos VPS (2026-04-18):**
- Disco: 7.9G usado / 96G total (9%)
- RAM: 1.3G usada / 11G total

**Probar VPS directamente (sin DNS):**
- `http://94.72.115.156:9300` → Gestión
- `http://94.72.115.156:9100` → ERP
- `http://94.72.115.156:9401` → Inventario
- `http://94.72.115.156:8083` → EspoCRM
- `http://94.72.115.156/` → WordPress

## Pendientes

| Tarea | Quién | Notas |
|---|---|---|
| Abrir puerto 22 SSH | Santi (panel Contabo) | customer.contabo.com → Networking → Firewall |
| Completar instalación WordPress | Santi | Entrar a wp.oscomunidad.com y llenar el wizard |
| Cortar DNS gestion/menu/inv al VPS | Santi (cuando confirme) | `cloudflared tunnel route dns --overwrite-dns vps-os <dominio>` desde local |
| Cortar DNS crm al VPS | Santi (cuando confirme) | Igual que los anteriores |
