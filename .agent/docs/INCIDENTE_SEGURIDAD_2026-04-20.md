# Incidente de seguridad — 2026-04-20

**Descubrimiento**: 2026-04-20 19:45 COT
**Contención**: 2026-04-20 21:40 COT (≈2h del descubrimiento)
**Estado**: 🟢 Contenido. Sin evidencia de uso activo de credenciales leakeadas.

---

## Qué pasó

Un atacante automatizado (bot de los que escanean IPs de Hostinger) explotó una vulnerabilidad del WordPress en `oscomunidad.com` (Hostinger shared hosting) el **2026-04-13** y volvió a meter código el **2026-04-16**. El sitio estaba "a medio empezar" pero eso no importó — los bots no apuntan a sitios populares sino a instalaciones vulnerables.

## Infección encontrada en `public_html/`

### Backdoors principales
- `index.php` — reemplazado por un **C2 client** ofuscado (XOR + base64 + hex2bin) que:
  - Enviaba IP + User-Agent + headers + URL + referer de cada visitante a `https://232pztc.sopmall.top` (servidor de control del atacante)
  - Hacía **SEO cloaking**: a bots de Google les servía spam (pharma/casino), a humanos la página normal
  - Aceptaba **upload remoto** vía `POST action=... uploadedFile`
- `moon.php` — **Tiny File Manager 2.4.3** con `$use_auth = false` → file manager del hosting sin password, accesible vía web
- `file.php` + `G-In.php` (MD5 idénticos) — webshells completas con: terminal del SO, file editor, creador de users admin de WordPress
- `wps.php`, `wp_ok.php`, `todo.php` — más backdoors (redundancia típica del kit)

### Modificaciones en el WP
- Usuario admin falso creado: `system` / `system@hostinger.com` / ID 3, registered `2026-04-16 13:29:48` (mismo timestamp exacto que los backdoors)
- 26+ archivos WP core renombrados con sufijo `_260413070324` (el kit preservó los originales y los reemplazó con sus versiones infectadas)

### Alcance del file-read
El webshell daba acceso de lectura a **todo lo que el user Linux `u768061575` ve**. El atacante pudo leer (y probablemente exfiltrar):
- `erp_descartado/.env` → credenciales de `os_comunidad` (ERP real Effi) + Cloudflare R2
- `campus/config.php` → credenciales de Moodle (`u768061575_toupy`)
- `estructura.sql` (28 KB) → schema (sin datos) de `os_comunidad`
- Backups SQL en `~/backups/bd/*.sql` (5 archivos)

### Qué NO fue comprometido
- Moodle `campus/` — 0 archivos modificados post 2026-04-10
- `wp-content/uploads/` — sin PHP malicioso
- BD `u768061575_os_comunidad` directamente — tiene user MySQL distinto del WP, no era accesible con `wp-config.php`; **pero** sus credenciales sí quedaron leakeadas vía el `.env`
- BDs del VPS Contabo — network aislada, user root MariaDB solo acepta localhost
- BDs locales — puerto 3306 solo expuesto a localhost

## Contención aplicada

### 1. Bloqueo de ejecución PHP en Hostinger

Escrito `.htaccess` en `public_html/` con:
```apache
<IfModule mod_php.c>
  php_flag engine off
</IfModule>
<FilesMatch "\.php$">
  Require all denied
</FilesMatch>
Options -ExecCGI
```
Resultado: todos los `.php` del directorio devuelven 403. El malware no puede ejecutarse ni comunicarse con el C2. Confirmado con `curl` a `/index.php`, `/moon.php`, `/file.php` → HTTP 403.

### 2. Eliminación de elementos activos del ataque
- `DELETE FROM wp_users WHERE ID=3` → user admin falso removido
- `mv erp_descartado/.env → .env.REMOVED_2026-04-20` (en caso de que se reactive PHP, el archivo leakeado ya no está en su ruta)
- `mv copia_erp_ops/ erp_descartado/ erp_os/ → *.QUARANTINED_2026-04-20/` (directorios con código legacy PHP que tenían credenciales viejas hardcoded)
- `mv ~/backups/bd/*.sql ~/estructura.sql → ~/backups_QUARANTINED_2026-04-20/` (backups SQL que el hacker pudo leer, sacados de la ruta visible)

### 3. Rotación de TODAS las credenciales que coincidían con la leakeada

Old password: `Epist2487.` (shared en todos los servicios)
New password: `Pepe2467.` (shared en todos los servicios — decisión del dueño)

Componente | Usuario | Dónde | Estado
---|---|---|---
MySQL Hostinger | `u768061575_ssierra047` (os_comunidad) | hPanel manual | ✅ rotado
MySQL Hostinger | `u768061575_osserver` (os_integracion deprecated) | hPanel manual | ✅ rotado
MySQL Hostinger | `u768061575_os_gestion` (os_gestion deprecated) | hPanel manual | ✅ rotado
MariaDB local | `osadmin@%` y `osadmin@172.18.0.%` | `ALTER USER` | ✅ rotado
MariaDB VPS | `osadmin@localhost` | `ALTER USER` | ✅ rotado
MariaDB VPS | `os_integracion@{127.0.0.1, localhost}` | `ALTER USER` | ✅ rotado
MariaDB VPS | `os_gestion@{127.0.0.1, localhost}` | `ALTER USER` | ✅ rotado
Linux | `osserver` local | `chpasswd` | ✅ rotado
Linux | `osserver` VPS | `chpasswd` | ✅ rotado
Linux | `root` VPS | `chpasswd` | ✅ rotado
SSH keys | `~/.ssh/id_ed25519`, `~/.ssh/sos_erp` | — | ✅ sin cambio (keys no estaban leakeadas)

### 4. Limpieza de `Epist2487.` en el repo

Actualizados para usar `Pepe2467.`:
- `integracion_conexionesbd.env` (local + VPS) — todas las `*_PASS` rotadas
- `scripts/inventario/analisis_ia_inventario.py` — refactor al helper `cfg_local()`, ya sin hardcode
- `.agent/.servers.env` — VPS_PASS
- `.vscode/settings.json` — 4 conexiones SQLTools

Eliminados:
- `integracion_conexionesbd.env.prev` / `.prev-rotation` / `.vps.env` (backups con creds viejas)

Grep final `Epist2487` en archivos activos: **0 resultados**. Solo quedan menciones en `.md` (docs históricas) y archivos `.QUARANTINED` de Hostinger (no ejecutables).

### 5. Backup forense

Guardado en `/home/osserver/Proyectos_Antigravity/backups/wordpress_hostinger_compromised_2026-04-20_213141/`:
- `public_html.tar.gz` (453 MB) — copia completa del directorio infectado
- `erp_descartado_env_leakeado.txt` — el `.env` exacto que se leakeó
- `campus_config_leakeado.php` — creds Moodle que se leakearon
- `README.md` — descripción del incidente

## Validación post-contención (2026-04-20 22:00)

Test de conexión desde helper `scripts/lib/db_conn.py` con nuevas passwords:
```
✅ LOCAL effi_data:       943 facturas
✅ LOCAL os_whatsapp:     16 contactos
✅ LOCAL ia_service_os:   17 agentes
✅ VPS os_integracion:    943 facturas
✅ VPS os_gestion:        473 tareas
✅ HOSTINGER os_comunidad: 8 usuarios (con password Pepe2467.)
```

Todos los servicios systemd `active` (local + VPS). Dominios públicos HTTP 200. Sin errores en logs post-restart.

## Pendientes del dueño

1. **Rotar Cloudflare R2** — las keys `R2_ACCESS_KEY_ID` y `R2_SECRET_ACCESS_KEY` del `.env` leakeado siguen activas. Entrar a Cloudflare dashboard → R2 → API Tokens → revocar las viejas + crear nuevas. Actualizar donde se usen.
2. **Rotar password de Moodle** (`campus/`) — entrar al admin de Moodle, cambiar `admin` password y credenciales de su BD.
3. **Considerar cambiar la password `Pepe2467.` por una única por servicio** — el hecho de que todos compartan la misma significa que si se leakea una, se leakean todas. Un gestor de secretos (ej: 1Password, Vaultwarden) es la mejor práctica.
4. **Nuclear el WordPress de Hostinger** cuando tengas 30 minutos — hoy quedó en "modo congelado" (PHP bloqueado). Si no lo vas a usar, se puede eliminar del hPanel. El VPS ya tiene el WP nuevo (`wp.oscomunidad.com`) con Elementor Pro y el template de producto importado.
5. **Actualizar plugins WordPress en el VPS** — Elementor FREE y PRO están en versiones (3.35.5 / 3.35.1) un poco detrás de las últimas (4.0.3). Hacer `wp plugin update --all` en el VPS.
6. **Habilitar 2FA** en hPanel de Hostinger y Cloudflare si no lo tienen ya.

## Lecciones aprendidas

- WordPress "a medio empezar" en shared hosting = target fácil para bots. No importa quién sos.
- Password única compartida entre servicios = explosion radius total si se leakea.
- `.env` con secretos dentro de `public_html` de un WP es una mala idea — vivían ahí archivos legacy `erp_descartado/.env` porque era código PHP del ERP viejo que necesitaba leer creds de Hostinger MySQL. Mejor práctica: `.env` fuera del webroot, o usar env vars del hosting.
- Cualquier archivo PHP hackeado en un dir que ejecute PHP = RCE completo. Bloqueo de PHP por `.htaccess` es la contención más rápida.
