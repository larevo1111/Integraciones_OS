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

| BD | Tablas | Tamaño | Notas |
|---|---|---|---|
| `os_inventario` | 9 | ~1.2 MB | Migrada 2026-04-10 — datos del inventario físico |
| `effi_data` | 44 | ~64 MB | Migrada 2026-04-10 — snapshot del pipeline |

**Credenciales MariaDB:**
- Usuario: `osadmin` / clave: ver `.agent/.servers.env`
- Acceso: `mysql -u osadmin -p effi_data`

⚠️ **`effi_data` no se actualiza automáticamente** — el pipeline corre en el servidor local. Si se necesita actualizar: `mysqldump effi_data | ssh root@94.72.115.156 'mysql -u osadmin -p effi_data'`

---

## Cloudflare Tunnel

| Campo | Detalle |
|---|---|
| Nombre | `vps-os` |
| ID | `fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a` |
| Credentials | `/root/.cloudflared/fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a.json` |
| Config | `/etc/cloudflared/config.yml` |
| Estado | Activo — pero **DNS siguen apuntando al servidor local** |

**Dominios configurados en el tunnel:**
```
wp.oscomunidad.com       → 80    (WordPress — DNS apunta al VPS ✅)
gestion.oscomunidad.com  → 9300  (DNS aún en servidor local — pendiente corte)
menu.oscomunidad.com     → 9100  (DNS aún en servidor local — pendiente corte)
inv.oscomunidad.com      → 9401  (DNS aún en servidor local — pendiente corte)
```

**Para cortar dominios al VPS** (cuando Santi confirme que todo funciona):
```bash
# Desde el VPS o desde el servidor local con cert.pem
cloudflared tunnel route dns --overwrite-dns vps-os gestion.oscomunidad.com
cloudflared tunnel route dns --overwrite-dns vps-os menu.oscomunidad.com
cloudflared tunnel route dns --overwrite-dns vps-os inv.oscomunidad.com
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

## Estado de migración (2026-04-11)

| App | VPS listo | DNS en VPS | Notas |
|---|---|---|---|
| Sistema Gestión (`gestion.oscomunidad.com`) | ✅ | ❌ pendiente corte | Funcionando en 9300 |
| ERP Frontend (`menu.oscomunidad.com`) | ✅ | ❌ pendiente corte | Funcionando en 9100 |
| Inventario (`inv.oscomunidad.com`) | ✅ | ❌ pendiente corte | Funcionando en 9401 |
| EspoCRM (`crm.oscomunidad.com`) | ✅ Docker | ❌ pendiente corte | Docker puerto 8083 |
| WordPress (`wp.oscomunidad.com`) | ✅ | ✅ DNS en VPS | **Pendiente: completar wizard instalación** |
| IA Service | ❌ no aplica | — | Se queda local (usa GPU/Ollama) |
| Bot Telegram | ❌ no aplica | — | Se queda local |
| Pipeline Effi | ❌ no aplica | — | Se queda local |
| WA Bridge | ❌ no aplica | — | Se queda local |

**Recursos VPS (2026-04-11):**
- Disco: 7.8G usado / 96G total (9% — mucho espacio libre)
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
