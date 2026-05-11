# Contexto: Seguridad y credenciales

**Última actualización**: 2026-05-11 (Fase A completada)
**Estado actual**: ✅ **Fase A completa** — Infisical activo, 185 secrets importados, 8 servicios refactorizados leyendo de Infisical. **Pendiente Fase B**: rotación de credenciales expuestas.

⚠ **Regla absoluta**: este archivo NO contiene valores de credenciales. Solo arquitectura, decisiones, plan. Los valores viven (transitoriamente) en `/home/osserver/tempoclv/secrets-inventory.env` (gitignored, permisos 600) y (definitivamente) en Infisical.

---

## TL;DR — Decisión arquitectural

**Movemos TODAS las credenciales a Infisical** (gestor de secretos self-hosted en el VPS, accesible solo por Tailscale). Las apps las leen via SDK con cache local. Resultado:

1. Claude / cualquier agente IA NUNCA más ve valores de credenciales en chats
2. Una sola fuente de verdad (cuando rotás, cambiás 1 lugar, los servicios toman el valor al restart)
3. Audit log: quién leyó qué secret, cuándo
4. Cero credenciales en código, en `.env` planos, en docs, en git history
5. Si una credencial se filtra, se rota en 1 click + restart servicios

### Estrategia en 2 PASOS (decidido 2026-05-11 con Santi)

```
PASO A — Centralización (con valores ACTUALES, sin rotar)
─────────────────────────────────────────────────────────
Subir todos los secrets actuales tal cual a Infisical.
Refactor helpers para que apps lean de Infisical.
Validar TODO funciona idéntico que antes.
  → Si algo falla, el problema es la mecánica, no el valor.

PASO B — Rotación de valores (después de validar A)
─────────────────────────────────────────────────────────
De a un servicio por día. Cambio en sistema target + update
Infisical + restart + validar.

DESCARTADO: rotar "lo expuesto" urgente antes de A
  → Santi prefiere consistencia y simplicidad sobre minimizar
    ventana de exposición. Trade-off aceptado.

DESCARTADO: reorganizar repo (shared/security/ + modules/)
  → El repo ya tiene helpers centrales (lib/db_conn.{js,py}).
    Solo agregamos lib/secrets.{js,py} al lado.
```

### Decisión final estructura de centralización — Estrategia C (Pragmática)

**Aprobada por Santi 2026-05-11**. La estructura adoptada para centralizar la seguridad **sin reorganizar el repo**:

```
lib/                                  ← Node (existe, le sumamos)
├── db_conn.js                        ← EXISTE — ajustamos: lee creds de secrets.js por dentro
├── timezone.js                       ← EXISTE — sin cambios
└── secrets.js                        ← NUEVO — cliente Infisical + cache + SSH key loader

scripts/lib/                          ← Python (existe, le sumamos)
├── db_conn.py                        ← EXISTE — ajustamos
├── secrets.py                        ← NUEVO
└── __init__.py                       ← actualiza imports
```

**Principio**: todos los secrets viven en Infisical (1 fuente de verdad). Toda la lógica de lectura de secrets vive en `lib/secrets.{js,py}`. El resto del repo no cambia.

**Lo que NO se centraliza (decisión consciente)**:
- Lógica de firma JWT: cada backend sigue firmando con `jwt.sign(data, secret)` — el secret lo lee de `lib/secrets`, pero la firma queda en cada backend. Cambiar esto sería refactor sin beneficio claro.
- Logging: cada servicio sigue con su logger nativo. Guideline en CLAUDE.md: "nunca loguear vars `*_PASS`, `*_KEY`, `*_TOKEN`, `*_SECRET`".
- Audit log: Infisical lo da de fábrica (cada `get()` queda registrado en su UI).

**Por qué C y no B (centralización total con `lib/security/`)**: B agrega 2-3 capas más (jwt.js + logger.js + audit.js) que protegen marginalmente contra escenarios poco realistas en tu escala. Para 1-2 personas + 8 servicios, C es suficiente y simple. Documentado discusión completa en historial de chat.

---

## 0. Plan de ejecución de HOY (2026-05-11)

### Acciones de Santi en UI (5 min, una sola vez)
1. **Crear Project `os-infra`** en Infisical (`Add New Project`, type Secrets Management)
2. **Crear Machine Identity `admin-bootstrap`** con permisos `Admin` sobre `os-infra`:
   - Settings del project → Access Control → Machine Identities → Create
   - Name: `admin-bootstrap`
   - Auth method: Universal Auth (default)
   - Role: `admin`
   - Generar Client ID + Client Secret
3. Pasar los 2 valores a Claude por chat

### Acciones de Claude (3-4 horas, programático)
| # | Acción | Tiempo | Servicios afectados |
|---|---|---|---|
| 1 | Login a Infisical via API con Machine Identity admin-bootstrap | 5 min | — |
| 2 | Crear 19 folders en `os-infra` | 5 min | — |
| 3 | Bulk import de las 185 entradas desde `tempoclv/secrets-inventory.env` | 10 min | — |
| 4 | Crear Machine Identities específicas por servicio con scope mínimo | 15 min | — |
| 5 | Escribir `lib/secrets.js` + `scripts/lib/secrets.py` (con tests) | 30 min | — |
| 6 | Modificar `lib/db_conn.js` y `scripts/lib/db_conn.py` para leer de `secrets` | 30 min | — |
| 7 | **PILOTO** — Refactor `sistema_gestion` (puerto 9300) | 30 min | gestion |
| 8 | Validar gestion funciona idéntico que antes | 15 min | gestion |
| 9 | Refactor `os-inventario-api` (puerto 9401) | 20 min | inventario |
| 10 | Refactor `scripts/produccion` | 20 min | produccion |
| 11 | Refactor `frontend` ERP (os-erp-frontend, menu.oscomunidad.com) | 20 min | menu erp |
| 12 | Validación general 4 prioritarios | 30 min | los 4 anteriores |
| 13 | Refactor `ia-service` | 20 min | ia-service |
| 14 | Refactor `telegram_bot` | 20 min | bot |
| 15 | Refactor `wa_bridge` | 20 min | wa-bridge |
| 16 | Refactor `effi-webhook` | 15 min | effi |
| 17 | Cleanup: borrar `/home/osserver/tempoclv/` | 1 min | — |
| 18 | Eliminar `.env` originales del filesystem (después de validar todo OK) | 10 min | — |
| 19 | Commit final + push | 5 min | — |

### Orden de servicios prioritarios (decidido por Santi)

| Prioridad | Servicio | Puerto | Dominio público |
|---|---|---|---|
| 1 — Piloto | **sistema_gestion** | 9300 | gestion.oscomunidad.com |
| 2 | **os-inventario-api** | 9401 | inv.oscomunidad.com |
| 3 | **scripts/produccion** | interno | (parte del Sistema Gestión) |
| 4 | **frontend ERP** (os-erp-frontend) | 9100 | menu.oscomunidad.com |
| 5 | ia-service | 5100 | (interno, llamado por bot) |
| 6 | telegram_bot | — | (sin puerto, polling) |
| 7 | wa-bridge | 3100 | (interno) |
| 8 | effi-webhook | 5050 | (interno) |

### Machine Identities — estrategia final (post-bloqueo API 2026-05-11)

**Plan original**: una identity por servicio con scope mínimo.

**Realidad**: la creación de identities project-managed via API requería permisos a nivel org (no concedidos a `admin-bootstrap`). Solo se pueden crear desde UI por usuario admin de la org.

**Decisión pragmática 2026-05-11**:
- **Fase inicial (HOY)**: todos los servicios usan la misma identity `admin-bootstrap` con scope al project `os-infra`. Token único, en disco con permisos 600.
- **Justificación**: todos los servicios corren en máquinas del propio dueño, tailnet privada, tokens nunca salen del filesystem. Beneficio marginal de scope mínimo vs costo de bloquear avance.
- **Deuda técnica documentada**: post-validación de Fase A (24-48h sin problemas), Santi crea 8 identities scope-mínimo en UI (5 min c/u, ~40 min total) y rota los tokens en cada servicio.

| Machine Identity | Estado actual (2026-05-11) | Plan post-validación |
|---|---|---|
| `admin-bootstrap` | ✅ creada, admin sobre os-infra, usada por TODOS los servicios | mantener para administración Claude/Santi |
| `gestion` | ⏳ pendiente | crear con scope: `/shared/*`, `/backends-erp/GESTION_*`, `/google-oauth/*`, `/admin-vps/*` |
| `inventario` | ⏳ pendiente | crear con scope: `/shared/*` |
| `produccion` | ⏳ pendiente | crear con scope: `/shared/*`, `/backends-erp/PRODUCCION_*` |
| `erp-frontend` | ⏳ pendiente | crear con scope: `/shared/*`, `/backends-erp/IA_ADMIN_*` |
| `ia-service` | ⏳ pendiente | crear con scope: `/shared/*`, `/ia-service/*` |
| `telegram-bot` | ⏳ pendiente | crear con scope: `/shared/*`, `/ia-service/TELEGRAM_*` |
| `wa-bridge` | ⏳ pendiente | crear con scope: `/shared/*` |
| `effi-webhook` | ⏳ pendiente | crear con scope: `/shared/*` |

### Validación post-migración

Cada servicio refactorizado se valida con:
1. `systemctl restart <servicio>` → no debe fallar al arrancar
2. Curl al health endpoint del servicio → debe responder
3. Una operación funcional típica:
   - **gestion**: login + listar tareas
   - **inventario**: GET de un conteo
   - **produccion**: GET de OPs vigentes
   - **menu erp**: cargar dashboard
   - **ia-service**: POST `/ia/consultar` con pregunta simple
   - **bot**: enviar mensaje al bot por Telegram
   - **wa-bridge**: GET `/health`
   - **effi-webhook**: GET `/health`

### Plan de rollback si algo se rompe

Por cada servicio refactorizado, **antes** del cambio:
1. Backup del archivo modificado: `cp service.py service.py.bak-pre-infisical`
2. Git commit del estado pre-cambio (rollback con `git revert`)
3. Si algo falla post-cambio, restaurar desde backup + restart

Como el `.env` original NO se borra hasta el final (paso 18), siempre podemos volver a leer del `.env` cambiando 1 línea de import.

### Después de hoy — PASO B (rotación, en otro día)

Una vez Fase A validada y estable 24-48h:

1. Rotar credenciales **expuestas en GitHub público** primero:
   - Token Telegram bot (vos en BotFather)
   - Pass humana "A" (yo via ALTER USER + passwd)
2. Rotar el resto **de a una por día**:
   - API keys IA (vos en cada console.X.com)
   - Pass paneles SaaS (vos en cada UI)
   - SSH keys (último — generar par nuevo + rotar authorized_keys + actualizar Infisical)
3. Cada rotación: cambio en sistema target → Infisical UI update → restart servicio → validar.

---

## 1. Inventario actual de credenciales (verificado en vivo 2026-05-11)

### 1.1 Acceso al VPS Contabo (94.72.115.156)

| Tipo | Usuario | Auth | Notas |
|---|---|---|---|
| SSH | `root` | SSH key `id_ed25519` (1 sola autorizada) | password auth deshabilitado |
| SSH | `osserver` (UID 1000) | misma SSH key | password auth deshabilitado |
| Login OS (sudo) | `osserver` | password Linux | usado solo internamente para `sudo` |
| Panel Contabo | (cuenta dueño) | pass de cuenta | https://my.contabo.com — recovery de emergencia |
| Tailscale | `vps-contabo` | host autorizado en tailnet `larevo1111@` | desde 2026-05-10 |

### 1.2 MariaDB del VPS

| Usuario | Host | Auth | Uso |
|---|---|---|---|
| `root` | localhost | unix_socket (pass = `'invalid'`, no funcional) | Solo entra root del OS via socket |
| `osadmin` | localhost | `mysql_native_password` | Pass humana (compartida con sudo OS) |
| `os_integracion`, `os_gestion`, `os_master`, `inventario_produccion_effi` | localhost+127.0.0.1 | `mysql_native_password` | Una pass por BD, usadas por apps remotas via SSH tunnel |

### 1.3 PostgreSQL del VPS (desde 2026-05-09)

| BD | Auth | Uso |
|---|---|---|
| `sos_master_erp` | osadmin (pass) | ERP Master multi-tenant (migrado desde MariaDB) |
| `sos_erp` | osadmin (pass) | ERP operativo |

### 1.4 Acceso servidor local (casa, osserver-ms)

| Tipo | Usuario | Auth | Notas |
|---|---|---|---|
| Login OS (sudo) | `osserver` (UID 1000) | password Linux | mismo pass que sudo VPS y `osadmin@MariaDB` ("humana A") |
| MariaDB `root@localhost` | — | unix_socket | `sudo mysql` entra sin pass |
| MariaDB `osadmin@%` | — | `mysql_native_password` | Pass humana A |
| MariaDB `larevo1111@localhost` | — | `mysql_native_password` | Usuario histórico, pass desconocida |
| MariaDB `oc_oc_admin@%` | — | `mysql_native_password` | Usado por OpenCode local |
| code-server | osserver | password propia (en `~/.config/code-server/config.yaml`) | Puerto 9400 localhost |
| VNC (x11vnc) | osserver | password binaria en `~/.vnc/passwd` | Puerto 5900 |
| AnyDesk | — | unattended pass (hash binario, rotable solo por GUI) | Acceso remoto desktop |
| Tailscale | `osserver-ms` | host autorizado en tailnet `larevo1111@` | activo desde 2026-05-03 |

### 1.5 Hostinger (BD os_comunidad y legacy)

| Tipo | Auth | Notas |
|---|---|---|
| SSH | SSH key `~/.ssh/sos_erp` | user `u768061575`, host `109.106.250.195:65002` |
| MariaDB `u768061575_ssierra047` | password | acceso lectura a `os_comunidad` |
| MariaDB user_integracion (legacy) | password | BD `os_integracion` ya migró al VPS — usuario probablemente sin uso |
| Panel hpanel.hostinger.com | password | cuenta dueño |

### 1.6 Resumen — credenciales humanas únicas

| # | Credencial | Cubre |
|---|---|---|
| 1 | **SSH key `id_ed25519`** (en `~/.ssh/` local) | Entra a `root@VPS` y `osserver@VPS` |
| 2 | **SSH key `sos_erp`** (en `~/.ssh/` local) | Entra a `u768061575@hostinger` (jumphost) |
| 3 | **Password humana "A"** | sudo osserver local + sudo osserver VPS + osadmin@MariaDB local + osadmin@MariaDB VPS + panel Contabo |
| 4 | Passes por-BD MariaDB | Una por cada BD/app, viven en `.env` |
| 5 | API keys IA cloud (Anthropic, Google, Groq, DeepSeek, Cerebras, GPT-OSS) | Viven en BD `ia_service_os.ia_agentes.api_key` + `.env` |
| 6 | Tokens Telegram (bot principal + bot alertas sys) | En `scripts/.env` |
| 7 | GitHub PAT (`gho_...`) | Keyring del OS, scopes: repo, admin:public_key, gist, read:org |
| 8 | Cuentas externas (Contabo, Hostinger, Cloudflare, Google) | Gestor personal (SafeInCloud) |

**⚠ Punto de riesgo**: la pass humana "A" se reutiliza en 5 servicios distintos. Si se filtra una, se filtran todas. La migración a Infisical permite separarlas sin esfuerzo.

---

## 2. Hallazgos de la auditoría (2026-05-10 / 2026-05-11)

### 2.1 Exposiciones en GitHub (verificadas con `git grep` + `git log -S`)

| Repo | Visibilidad | Pass actual "A" | Pass vieja `Epist2487` | Token Telegram bot |
|---|---|---|---|---|
| **Integraciones_OS** | **🔴 PÚBLICO** | 1 archivo HEAD + 1 commit | 25 archivos + 80 commits | **2 archivos + 25 commits** |
| **SOS_ERP_descartado** | **🔴 PÚBLICO** | 0 | 1 archivo | 0 |
| configuracion-servidor-local-linux | PÚBLICO | 0 | 0 | 0 |
| sa_opencode | PRIVADO | 0 | 3 archivos | 0 |
| OS_EC | PRIVADO | 1 archivo | 1 archivo | 0 |
| OS_ERP_INTEGRADO | PRIVADO | 1 archivo | 3 archivos | 0 |
| erp_os | PRIVADO | 0 | 12 archivos | 0 |

### 2.2 Riesgos identificados (orden de gravedad)

1. 🔴🔴🔴 **CRÍTICO — Token bot Telegram en repo PÚBLICO** (Integraciones_OS). Cualquiera con acceso al repo puede tomar control total del bot.
2. 🔴🔴 **CRÍTICO — Password humana "A" actual en repo PÚBLICO** (`.agent/docs/INCIDENTE_SEGURIDAD_2026-04-20.md`). Irónico — la doc del incidente publicó la pass nueva.
3. 🟡 **MEDIO — Password vieja `Epist2487.` en repo público** (25 archivos). Ya rotada, no funciona como pass activa, pero mal precedente.
4. 🟡 **MEDIO — Logs commiteados** (`logs/telegram_bot.log`) con tokens.
5. 🟡 **MEDIO — `.agent/.licencias.env`** descubierto tarde — contiene licencias y passes de servicios autohospedados (Grafana, Nextcloud, Minio, EspoCRM, NocoDB, code-server, Elementor).
6. 🟢 **BAJO — Passes en repos privados**. Higiene.

### 2.3 Causas raíz

- No hay pre-commit hook que bloquee secrets (ningún `gitleaks` / `detect-secrets`).
- Práctica histórica: docs usaban la pass como ejemplo (`mysql -u osadmin -pXXX`). Se propagó.
- Logs no estaban en `.gitignore` desde el inicio.
- Múltiples archivos `.env` distribuidos sin inventario centralizado.

---

## 3. Plan de 5 fases — estado y detalle

### ✅ Fase 1 — Tailscale en VPS (completada 2026-05-10)

| # | Acción | Estado |
|---|---|---|
| 1.1 | Instalar tailscale en VPS | ✅ |
| 1.2 | Login interactivo, hostname `vps-contabo` | ✅ |
| 1.3 | Verificar visible en `tailscale status` desde local | ✅ |

**Resultado**: VPS en tailnet con IP `100.86.226.112`. SSH por hostname funciona. tailscaled enabled (autostart).

### ✅ Fase 2 — Infisical en Docker del VPS (completada 2026-05-11)

| # | Acción | Estado |
|---|---|---|
| 2.1 | Docker stack (backend + postgres + redis) en `/opt/infisical/` | ✅ |
| 2.2 | Bind solo a `127.0.0.1:8080` (cero exposición pública) | ✅ |
| 2.3 | Tailscale Serve con HTTPS automático (cert legítimo) | ✅ |
| 2.4 | SMTP Gmail configurado (app password) | ✅ |
| 2.5 | Backup horario local + rsync via tailnet a casa | ✅ |
| 2.6 | Admin user creado: Santiago Sierra | ✅ |
| 2.7 | 2FA TOTP activado | ✅ |
| 2.8 | Server Console configurado (signup restringido a `gmail.com`) | ✅ |

**Resultado**: Infisical activo en `https://vps-contabo.tail44c420.ts.net`. Solo accesible vía tailnet. Backup E2E validado (134KB dump → casa).

**Decisiones tomadas durante Fase 2**:
- Google OAuth para login → POSPUESTO (mucho trabajo, poco beneficio diario). Mantener email+pass+TOTP.
- Cerrar puerto 22 SSH público VPS → POSPUESTO (decisión separada después de validar tailnet).
- Estructura de organización: **1 project central con folders** (vs N projects por servicio). Razón: equipo de 1-2 personas, separación menos estricta es suficiente y más simple.

### 🟡 Fase 3 — Refactor de helpers para leer de Infisical (en curso)

| # | Acción | Estado |
|---|---|---|
| 3.1 | Inventario exhaustivo de secrets (181 entradas, 18 folders) | ✅ |
| 3.2 | Archivo `tempoclv/secrets-inventory.env` con valores actuales | ✅ |
| 3.3 | Santi revisa el archivo, decide qué rotar | ⏳ EN CURSO |
| 3.4 | Crear primer Project en Infisical UI (`os-infra`) | ⏳ |
| 3.5 | Import del `.env` a Infisical (drag&drop por folder) | ⏳ |
| 3.6 | Rotar credenciales expuestas (BD passes, bot token, etc) | ⏳ |
| 3.7 | Borrar `/home/osserver/tempoclv/` | ⏳ |
| 3.8 | Crear `lib/secrets.js` + `scripts/lib/secrets.py` (wrappers SDK) | ⏳ |
| 3.9 | Piloto: refactorizar `ia-service` | ⏳ |
| 3.10 | Validar 24h piloto | ⏳ |
| 3.11 | Escalar a 7 servicios restantes (telegram-bot, erp, gestion, inventario, wa-bridge, effi-webhook, ialocal) | ⏳ |
| 3.12 | Eliminar `.env` originales del filesystem | ⏳ |

### 🟡 Fase 4 — Limpieza GitHub + gitleaks (pendiente)

| # | Acción | Estado |
|---|---|---|
| 4.1 | Instalar `gitleaks` + pre-commit hook con reglas custom | ⏳ |
| 4.2 | Reemplazar passes y tokens viejos en HEAD de los 7 repos | ⏳ |
| 4.3 | Agregar `logs/*.log` a `.gitignore` + `git rm --cached` | ⏳ |
| 4.4 | (Opcional) `git filter-repo` para borrar history → force-push | ⏳ |

### 🟡 Fase 5 — Blindar WordPress + WooCommerce (pendiente, paralelo)

Setup mínimo aprobado por Santi (30 min, $0, cubre ~99% de ataques reales):

| # | Acción | Estado |
|---|---|---|
| 5.1 | Plugin Wordfence (firewall + 2FA + escáner malware) | ⏳ |
| 5.2 | Cloudflare WAF rules delante de `wp.oscomunidad.com` | ⏳ |
| 5.3 | `define('WP_AUTO_UPDATE_CORE', true);` + auto-update plugins | ⏳ |

**Lo NO incluido (decisión)**: cambio URL login, backups custom, CSP — son extras opcionales.

---

## 4. Estructura definitiva de Infisical (decidida 2026-05-11)

**Modelo**: 1 project (`os-infra`) con folders por dominio. Permisos por path con Machine Identities por servicio.

```
Project: os-infra
│
├── /shared/                  ← creds que usan 2+ servicios
│   ├── DB_LOCAL_*            (MariaDB casa)
│   ├── DB_INTEGRACION_*      (MariaDB VPS via SSH tunnel)
│   ├── DB_INVENTARIO_*       (idem)
│   ├── DB_GESTION_*          (idem)
│   ├── DB_MASTER_*           (idem)
│   ├── DB_COMUNIDAD_*        (Hostinger via jumphost)
│   └── APP_TIMEZONE
│
├── /ia-service/              ← API keys IA + Telegram bots + Gmail
│   ├── ANTHROPIC_API_KEY
│   ├── GOOGLE_API_KEY
│   ├── GROQ_API_KEY
│   ├── DEEPSEEK_API_KEY
│   ├── CEREBRAS_API_KEY
│   ├── TELEGRAM_BOT_TOKEN
│   ├── TELEGRAM_NOTIF_BOT_TOKEN
│   ├── GMAIL_APP_PASSWORD
│   └── TAVILY_API_KEY
│
├── /backends-erp/            ← JWT secrets de cada Node backend
│   ├── IA_ADMIN_JWT_SECRET
│   ├── GESTION_JWT_SECRET
│   └── PRODUCCION_JWT_SECRET
│
├── /admin-local/             ← accesos servidor casa
│   ├── LOCAL_LOGIN_PASS
│   ├── CODESERVER_LOCAL_PASS
│   └── ...
│
├── /admin-vps/               ← accesos VPS
│   ├── CODESERVER_VPS_PASS
│   ├── VPS_LOGIN_PASS
│   └── VPS_PANEL_PASS
│
├── /tunnels/                 ← Cloudflare Tunnel tokens (críticos)
│   ├── CF_TUNNEL_LOCAL_JSON
│   └── CF_TUNNEL_VPS_JSON
│
├── /hostinger/               ← creds Hostinger expandidas
│   ├── HOSTINGER_DB_USER_COMUNIDAD
│   ├── HOSTINGER_DB_PASS_COMUNIDAD
│   └── ...
│
├── /ssh-keys-privadas/       ← keys SSH para apps (memoria pura, no disco)
│   ├── SSH_KEY_VPS_PRIVATE_ED25519
│   └── SSH_KEY_HOSTINGER_PRIVATE
│
├── /github/                  ← PAT de gh CLI
│   └── GITHUB_PAT
│
├── /google-oauth/            ← Client Secret (Client ID es público)
│   └── GOOGLE_OAUTH_CLIENT_SECRET
│
├── /woocommerce/             ← (legacy, verificar si sigue activo)
│   └── WC_CONSUMER_KEY/SECRET
│
├── /infisical-internal/      ← backup recuperación del propio Infisical
│   └── ENCRYPTION_KEY, AUTH_SECRET, etc.
│
└── /cuentas-externas/        ← passwords de paneles SaaS
    └── CONTABO_PANEL_PASS, HOSTINGER_PANEL_PASS, etc. (opcional)
```

**Total**: 18 folders, 185 secrets inventariados.

---

## 5. Rotación de credenciales — proceso

### 5.1 Cómo funciona la rotación (concepto)

```
PASO 1 — Rotación inicial (una sola vez, AHORA)
─────────────────────────────────────────────
Cada credencial vive en su SISTEMA TARGET:
  • Pass MariaDB → vive en MariaDB
  • Token Telegram → vive en BotFather
  • Pass Linux → vive en /etc/shadow
  • API key Anthropic → vive en console.anthropic.com

Hay que ir a CADA sistema target y rotar. Infisical no puede
cambiar la pass de MariaDB por sí mismo — solo guarda el valor
que se le dice.

Tiempo total: ~40 min (la mayoría automatizable con scripts).

PASO 2 — Rotaciones futuras (todas iguales)
─────────────────────────────────────────────
Ya con Infisical:
  1. Cambiar valor en sistema target (ALTER USER / BotFather / etc.)
  2. Actualizar en Infisical UI
  3. Restart de servicios → toman el nuevo valor automáticamente

NO hay que editar 17 archivos `.env`. Cambio en 2 lugares
coordinados desde 1 UI.
```

### 5.2 Categorización del trabajo manual vs automático

| Categoría | Cómo se rota | Tipo | Tiempo |
|---|---|---|---|
| 5 pass MariaDB (osadmin local/VPS + users por BD) | Script Python: `ALTER USER` + UPDATE Infisical + verify | 🤖 Auto | 2 min |
| 2 pass Linux (sudo local/VPS) | `passwd osserver` × 2 (interactivo, te pide tipear) | 🤖 Semi-auto | 30 seg |
| Pass Hostinger DB users | SQL ALTER USER + UPDATE Infisical | 🤖 Auto | 1 min |
| Token Telegram bot | Manual en BotFather (`/revoke` + `/newtoken`) | 🧍 Manual UI | 2 min |
| API keys IA (Anthropic, Google, Groq, etc.) | Manual en cada console: revoke + create | 🧍 Manual UI | 2-3 min c/u |
| OAuth Client Secret Google | Manual en console.cloud.google.com | 🧍 Manual UI | 2 min |
| Pass panel Contabo / Hostinger / Cloudflare | Manual en cada panel | 🧍 Manual UI | 2 min c/u |
| WooCommerce keys | Manual en wp-admin (si sitio activo) | 🧍 Manual UI | 5 min |
| **SSH keys** | NO se rotan ahora (no estuvieron expuestas, solo en filesystem) | — | 0 |
| 3 JWT secrets | Generar random + UPDATE Infisical + restart | 🤖 Auto | 1 min |

**Tiempo total**: ~10 min automatizado + 30-40 min manual repartido (se puede hacer por sesiones).

### 5.3 Estrategia recomendada de orden

1. **HOY URGENTE** (lo expuesto en repo PÚBLICO):
   - Pass `osadmin` MariaDB (todos los servers)
   - Pass Linux sudo (local + VPS)
   - Token Telegram bot
2. **ESTA SEMANA**:
   - API keys IA (las que estuvieron en repos privados)
   - WooCommerce keys (si el sitio sigue activo)
   - Google OAuth Client Secret
3. **CUANDO QUIERAS**:
   - Pass panel Contabo / Hostinger / Cloudflare (cambiar manualmente en cada panel)

---

## 6. Cómo recuperarse si se pierde el acceso (disaster recovery)

### Si se pierde la SSH key local `~/.ssh/id_ed25519`
1. Entrar a panel Contabo (my.contabo.com) → consola web del VPS
2. Login como `root` con la password Linux del VPS
3. Agregar nueva clave pública en `~/.ssh/authorized_keys` y `/home/osserver/.ssh/authorized_keys`

**Mitigación pendiente**: configurar 2da SSH key de backup (Fase 3 opcional).

### Si se pierde la password humana "A"
1. Acceso SSH al VPS aún funciona (con key) → entrar como `root` → `passwd osserver` para resetear
2. Para MariaDB osadmin: como root del OS, entrar con `sudo mysql` y `ALTER USER 'osadmin'@'localhost' IDENTIFIED BY 'nueva';`

### Si se pierde acceso al panel Contabo
Email de recuperación de Contabo → my.contabo.com/account-recovery

### Si Infisical cae (post Fase 2)
1. Cache local cifrada con TTL 1h sigue funcionando hasta que expire
2. Restart docker-compose en VPS: `cd /opt/infisical && docker compose up -d`
3. Si la BD Postgres de Infisical se corrompió: restaurar último backup de `/backups/infisical/` o `/home/osserver/backups/infisical/`

### Si se pierde el master password de Infisical
**Hay 24 backup codes de 2FA TOTP**. Después de eso:
1. Hay archivos backup horario del Postgres de Infisical
2. Restaurar dump y resetear admin user via SQL (proceso técnico documentado en su docs)

---

## 7. Riesgos del plan + mitigaciones

| Riesgo | Mitigación |
|---|---|
| Infisical = single point of failure | Cache local cifrada TTL 1h + backup automático Postgres horario + backup remoto via tailnet |
| Refactor masivo rompe producción | Piloto obligatorio con 1 servicio, validar 24h antes de escalar |
| Git history scrubbing rompe forks | Auditar forks con `gh` antes de force-push (no debería haber) |
| 2FA Infisical lockout | 24 backup codes guardados en SafeInCloud (gestor personal) + papel físico |
| Cambios en `.env` durante refactor pueden romper apps | Mantener `.env` plano como fallback durante piloto |

---

## 8. Decisiones pospuestas (opcionales, no priorizadas)

| Item | Estado | Cuándo retomar |
|---|---|---|
| Google OAuth (SSO) en Infisical | Pospuesto — mucho setup GCP para poco beneficio diario | Si login email+pass+TOTP se vuelve incómodo |
| Cerrar puerto 22 SSH público del VPS | Pospuesto — Santi quiere entender mejor primero | Después de validar Tailscale Serve por unos días |
| 2da SSH key de backup para VPS | Pospuesto | Antes de que se rompa algo. Quick-win |
| Git history scrubbing con filter-repo | Pospuesto | Solo si auditoría externa lo requiere o por higiene estética |
| Separar la pass humana "A" en 5 distintas | Implícito al migrar a Infisical | Durante Fase 3 — al rotar, ponemos pass distinta por sistema |

---

## 9. Decisiones de arquitectura NO triviales (por qué se eligió)

| Decisión | Por qué se eligió | Alternativa descartada |
|---|---|---|
| **Infisical** self-hosted vs Vaultwarden/Vault/Doppler | SDK Python/Node limpios, UI buena, gratis self-hosted, sweet spot complejidad/funcionalidad | Vaultwarden (no para apps), Vault (overkill), Doppler (costo + dependencia externa) |
| **1 project + folders** vs N projects | Equipo de 1-2 personas, todos los servicios son tuyos, mayoría de secrets son compartidos | N projects + imports cruzados — más complejo de administrar |
| **Tailscale** privado vs puerto público | Cero superficie pública, latencia P2P direct, mantenimiento cero | VPN tradicional (WireGuard manual), exponer pub con Cloudflare Access |
| **Bind 127.0.0.1 + tailscale serve** vs bind tailnet IP directo | Cert HTTPS automático, no requiere `ufw` ni configuración firewall manual | Bindear directamente a IP tailnet — funcional pero menos limpio |
| **SSH keys EN Infisical** vs solo en filesystem | Apps las usan programáticamente (db_conn helpers), consistencia con resto de secrets, beneficio operacional para mover servicios | Solo en `~/.ssh/` — best practice clásica pero menos práctico para apps |
| **Memoria pura para SSH keys** vs `/tmp/` temporal | paramiko/ssh2 aceptan key como string/Buffer — cero escritura a disco | `/tmp/` temporal (Linux moderno, RAM en tmpfs) — válido pero subóptimo |

---

## 10. Referencias

- **Incidente inicial**: [.agent/docs/INCIDENTE_SEGURIDAD_2026-04-20.md](../docs/INCIDENTE_SEGURIDAD_2026-04-20.md)
- **Bitácora del incidente PG**: `~/Proyectos_Antigravity/OS_EC/.agent/bitacoras/2026-04-20_descubrimiento_infra_real.md`
- **Centralización creds**: [feedback_conexiones_bd_env.md](../../../.claude/projects/-home-osserver-Proyectos-Antigravity-Integraciones-OS/memory/feedback_conexiones_bd_env.md)
- **Servers**: [.agent/.servers.env](../.servers.env) (gitignored)
- **Licencias**: [.agent/.licencias.env](../.licencias.env) (gitignored)
- **Inventario actual transitorio**: `/home/osserver/tempoclv/secrets-inventory.env` (gitignored, permisos 600, se borra después de subir a Infisical)
- **Infisical URL**: https://vps-contabo.tail44c420.ts.net (solo tailnet)
- **Infisical docker-compose**: `/opt/infisical/docker-compose.yml` (en VPS)
- **Backup Infisical**: `/var/backups/infisical/` (VPS, retención 7d) + `/home/osserver/backups/infisical/` (casa, retención 30d)

---

## 11. ESTADO FINAL FASE A — completado 2026-05-11 ✅

Fecha exacta: tarde-noche del 11 de mayo 2026 (~5 horas de trabajo, una sola sesión).

### 11.1 Resultados verificados

| # | Componente | Estado | Validación |
|---|---|---|---|
| 1 | **Project `os-infra`** en Infisical | ✅ creado | UI muestra 185 secrets en 19 folders |
| 2 | **Machine Identity `admin-bootstrap`** | ✅ activa | Universal Auth funcionando, token 30 días |
| 3 | **19 folders** en `/` del project | ✅ todos | Verificado con `GET /api/v1/folders` |
| 4 | **185 secrets** importados | ✅ todos | Conteo coincide local (185) ↔ Infisical (185) |
| 5 | **SSH keys privadas** en `/ssh-keys-privadas/` | ✅ 4 entradas | VPS + Hostinger, públicas y privadas |
| 6 | **Backup horario Infisical** | ✅ funcionando | VPS local + rsync via tailnet a casa |
| 7 | **`lib/infisical.js` + `scripts/lib/infisical.py`** | ✅ creados | Test 100% OK (get, getMany, getSSHKey) |
| 8 | **`lib/db_conn.{js,py}`** modificado | ✅ refactor con bootstrap Infisical + SSH key memoria pura | Sin cambios para callers |
| 9 | **8 servicios refactorizados** | ✅ todos activos | Ver tabla 11.2 |
| 10 | **Documento de plan** | ✅ este archivo | Plan + decisiones + arquitectura completa |

### 11.2 Servicios migrados (todos active + respondiendo HTTP 200)

| Servicio | Servidor | Puerto | Modificaciones |
|---|---|---|---|
| **ia-service** | local | 5100 | `scripts/ia_service/config.py` bootstrap `/ia-service/*` → os.environ |
| **os-telegram-bot** | local | — | Hereda de ia-service (mismo proceso config) |
| **os-gestion** | local | 9300 | `sistema_gestion/api/server.js` → `cargarSecretsInfisical()` antes de `app.listen` |
| **os-inventario-api** | local | 9401 | `scripts/inventario/api.py` JWT_SECRET (antes hardcoded) → Infisical |
| **os-produccion-api** | local | 9600 | `scripts/produccion/api.py` JWT + GOOGLE_CLIENT_ID → Infisical |
| **wa-bridge** | local | 3100 | Sin cambio directo — usa `lib/db_conn` (ya migrado) |
| **effi-webhook** | local | 5050 | Sin cambio directo — usa `lib/db_conn` |
| **os-erp-frontend** | **VPS** | 9100 | `lib/db_conn.js` (ya migrado, git pull + restart) |

### 11.3 Cómo funciona el flujo de credenciales ahora

```
┌──────────────────────────────────────────────────────────────────┐
│  INFISICAL (https://vps-contabo.tail44c420.ts.net)               │
│  Project: os-infra                                                │
│  185 secrets en 19 folders                                        │
│  Solo accesible vía tailnet privada                              │
└──────────────────────────────────────────────────────────────────┘
                            │
                            │  HTTPS via tailnet
                            │  (Universal Auth — token JWT)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  lib/infisical.{js,py}  — cliente SDK con cache memoria          │
│                                                                   │
│   get(key, folder)      → valor del secret (string)              │
│   getMany(folder)       → todos los secrets de un folder         │
│   getSSHKey(which)      → SSH key como string (Node) / objeto    │
│                            paramiko (Python). Memoria pura.       │
└──────────────────────────────────────────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ lib/db_conn.js │  │ scripts/lib/   │  │ código de cada │
│ /db_conn.py    │  │ db_conn.py     │  │ servicio       │
│                │  │                │  │                │
│ Bootstrap al   │  │ Lee /shared/   │  │ Carga propio   │
│ import:        │  │ al import →    │  │ folder al      │
│ /shared/ →     │  │ os.environ     │  │ startup:       │
│ process.env    │  │                │  │ /backends-erp, │
│                │  │ SSH key como   │  │ /ia-service,   │
│ SSH key como   │  │ paramiko       │  │ etc.           │
│ Buffer en      │  │ object en      │  │                │
│ memoria        │  │ memoria        │  │                │
└────────────────┘  └────────────────┘  └────────────────┘
                            │
                            ▼ FALLBACK si Infisical no responde
┌──────────────────────────────────────────────────────────────────┐
│  integracion_conexionesbd.env + scripts/.env + sistema_gestion/  │
│  api/.env + etc. (vivos durante transición — eliminamos al final)│
└──────────────────────────────────────────────────────────────────┘
```

### 11.4 Cómo se autentica cada servicio contra Infisical

**Mecanismo**: Universal Auth (Client ID + Client Secret de la Machine Identity).

**Hoy (Fase A)**: TODOS los servicios usan la misma identity `admin-bootstrap`:
- Client ID: `5605ebaf-950c-421b-8dc8-b37b67bc27bf`
- Client Secret: en `/home/osserver/tempoclv/.infisical_admin_bootstrap.env` (permisos 600)

**Cómo lo encuentran los servicios**:
1. **Servicios LOCAL**: `infisical.{js,py}` carga del archivo `tempoclv/...env` si las env vars del proceso no están definidas.
2. **ERP Frontend en VPS**: idem — el archivo `tempoclv/` se replicó al VPS via scp.
3. **Sistema Gestión local**: además, las env vars Infisical están en su `.env` propio (sistema_gestion/api/.env) — más explícito.

**Después (Fase B planeada)**: cada servicio tendrá su Machine Identity con scope mínimo. Hay que crearlas en UI (5 min c/u, ~40 min total) y reemplazar el Client ID/Secret en cada uno.

### 11.5 Cómo está cubierta cada categoría de secret

| Categoría | Antes | Ahora |
|---|---|---|
| Pass MariaDB (osadmin local + VPS + por-BD) | `integracion_conexionesbd.env` | Infisical `/shared/DB_*_PASS` → bootstrap a process.env |
| SSH keys | `~/.ssh/id_ed25519` + `~/.ssh/sos_erp` filesystem | Infisical `/ssh-keys-privadas/` → cargada como objeto paramiko/Buffer en memoria pura (sin tocar disco) |
| API keys IA cloud (11 agentes) | BD `ia_service_os.ia_agentes.api_key` | BD (sin cambio — sigue siendo fuente para el servicio) + duplicado en Infisical `/ia-service/IA_AGENT_KEY_*` para auditoría/recovery |
| Token Telegram bot | `scripts/.env` | Infisical `/ia-service/TELEGRAM_*` → bootstrap |
| JWT secrets de backends | hardcoded (inventario) o `.env` (gestion, produccion) | Infisical `/backends-erp/*_JWT_SECRET` → carga al startup del servicio |
| Google OAuth Client ID | `.env` (público pero ahí) | Infisical `/google-oauth/` |
| Google OAuth Client Secret | `.env` | Infisical `/google-oauth/` |
| Passwords paneles SaaS (Contabo, Hostinger, Cloudflare) | gestor personal (SafeInCloud) | Infisical `/cuentas-externas/` (con valores "COMPLETAR" — Santi llena si quiere) |
| Pass humana sudo + osadmin (la "A") | `.env` y propagada | Infisical `/shared/DB_LOCAL_PASS` + `/admin-local/LOCAL_LOGIN_PASS` |

### 11.6 Bug crítico arreglado durante Fase A

**`JWT_SECRET` hardcoded en `scripts/inventario/api.py:22`**: valor literal en código fuente, **expuesto en repo público** desde su creación. Fix:
- Valor copiado a Infisical `/backends-erp/INVENTARIO_JWT_SECRET`
- Archivo modificado para leer de Infisical con fallback al valor viejo (solo hasta validar y rotar en Fase B)

Es la única exposición de tipo "JWT secret hardcoded en código" que detecté. El resto de servicios ya leía de `.env` (que está gitignored).

### 11.7 Archivos creados/modificados

**Nuevos**:
- `lib/infisical.js` — cliente Infisical Node
- `scripts/lib/infisical.py` — cliente Infisical Python
- `.agent/contextos/seguridad.md` (este documento)
- `/home/osserver/tempoclv/secrets-inventory.env` (TRANSITORIO, se borra)
- `/home/osserver/tempoclv/.infisical_admin_bootstrap.env` (mientras admin-bootstrap exista)
- `/home/osserver/tempoclv/.infisical_access_token` (cache token, regenerable)
- `/opt/infisical/docker-compose.yml` (en VPS — stack levantado)
- `/opt/infisical/.env` (en VPS — secrets internos de Infisical)
- `/opt/infisical/backup.sh` (en VPS — script de backup horario)

**Modificados**:
- `lib/db_conn.js` — bootstrap Infisical + SSH key memoria pura
- `scripts/lib/db_conn.py` — idem
- `sistema_gestion/api/server.js` — carga JWT + Google OAuth de Infisical
- `sistema_gestion/api/.env` — agrega vars INFISICAL_*
- `scripts/inventario/api.py` — JWT de Infisical (fix de hardcoded)
- `scripts/produccion/api.py` — JWT + Google OAuth de Infisical
- `scripts/ia_service/config.py` — bootstrap `/ia-service/*` a os.environ

**Commits hechos**:
- `45d3390` — feat(seguridad): centralizar credenciales en Infisical
- `c48d369` — feat(ia-service): bootstrap secrets desde Infisical

---

## 12. FASE B — Rotación (PENDIENTE — siguiente paso)

### Requisitos previos cumplidos para empezar Fase B
- [x] Infisical funcionando como single source of truth
- [x] Servicios leyendo de Infisical (con fallback)
- [x] 24h de estabilidad esperadas (validar mañana 12-may que nada explotó)
- [ ] Crear 8 Machine Identities scope-mínimo (UI, 5 min c/u) — esto es Fase B también

### Orden de rotación recomendado (lo expuesto primero)

#### 🔴 Día 1 — credenciales expuestas en GitHub PÚBLICO
1. **Token bot Telegram** (Santi en BotFather):
   - `/revoke` el bot → `/newtoken`
   - Actualizar en Infisical UI: `/ia-service/TELEGRAM_BOT_TOKEN`
   - Restart `os-telegram-bot.service`
   - Validar: enviar mensaje al bot, debe responder
2. **Pass humana "A"** (osadmin MariaDB local + VPS + sudo OS):
   - Generar pass random nueva (yo te ayudo)
   - SQL: `ALTER USER 'osadmin'@'localhost' IDENTIFIED BY 'NUEVA';` en local + VPS
   - `passwd osserver` en local + VPS
   - Update Infisical: `/shared/DB_LOCAL_PASS` + `/admin-local/LOCAL_LOGIN_PASS` + `/admin-vps/VPS_LOGIN_PASS`
   - Restart de TODOS los servicios (toman pass nueva)
   - Validar: cada servicio reconecta a MariaDB sin error

#### 🟡 Días siguientes — uno por día
3. **API keys IA** (vos en cada console.X.com):
   - console.anthropic.com → revoke + create → update Infisical `/ia-service/IA_AGENT_KEY_CLAUDE_SONNET` + BD `ia_agentes` slug=`claude-sonnet`
   - aistudio.google.com → idem para `IA_AGENT_KEY_GEMINI_*` (los 4)
   - console.groq.com → idem para `IA_AGENT_KEY_GROQ_LLAMA` + `IA_AGENT_KEY_GPT_OSS_120B`
   - platform.deepseek.com → idem para `IA_AGENT_KEY_DEEPSEEK_*` (los 2)
   - cloud.cerebras.ai → idem `IA_AGENT_KEY_CEREBRAS_LLAMA`
4. **OAuth Client Secret Google** (console.cloud.google.com):
   - Regenerar el client secret
   - Update Infisical `/google-oauth/GOOGLE_OAUTH_CLIENT_SECRET`
   - Restart gestion + produccion + erp-frontend
5. **JWT secrets** (los 4: ia-admin, gestion, produccion, inventario):
   - Generar random nuevos
   - Update Infisical en `/backends-erp/`
   - Restart servicios → **invalida sesiones activas** (todos los logueados tienen que loguear de nuevo — hacelo en horario tranquilo)
6. **Hostinger users + Cloudflare API tokens**:
   - Hostinger panel → cambiar pass de DB users
   - Cloudflare dashboard → regenerar API token si lo tenés activo
7. **Pass paneles SaaS** (cuando quieras, manualmente)

### Una vez rotado todo

- [ ] Borrar `/home/osserver/tempoclv/secrets-inventory.env` (valores viejos)
- [ ] Borrar `/home/osserver/tempoclv/.infisical_admin_bootstrap.env` SI creamos machine identities por servicio antes
- [ ] Eliminar valores antiguos de los `.env` que ya quedan obsoletos (`integracion_conexionesbd.env` → mantener solo INFISICAL_* + APP_TIMEZONE; el resto eliminar)
- [ ] Considerar Fase 4 — gitleaks pre-commit + history scrubbing

---

## 13. Cómo usar el sistema desde aquí adelante

### Para Claude (yo) en futuras sesiones

**Para conectar a una BD**: igual que antes, sin cambios.
```python
from lib import local, integracion
with local('ia_service_os') as conn:
    ...
```

**Para leer un secret específico**:
```python
from lib.infisical import get
api_key = get('GMAIL_APP_PASSWORD', '/ia-service')
```

**NUNCA en futuras sesiones**:
- Yo NO veo valores de secrets (solo nombres y paths)
- Si Santi me pide "agregá una API key nueva", le digo "creála en Infisical UI" — no la manipulo yo
- Si necesito un secret nuevo en código, escribo `get('NEW_KEY', '/folder')` con un nombre claro, y le digo a Santi qué nombre creó en Infisical

### Para Santi cuando rote un secret

1. Cambiar el valor en el sistema target (BotFather, ALTER USER, console.X.com, etc.)
2. En Infisical UI: ir al folder → editar el secret → pegar valor nuevo → Save
3. Restart del/los servicio(s) que lo usan: `sudo systemctl restart NOMBRE.service`
4. Validar: hacer una operación funcional del servicio

### Para Santi cuando agregue un servicio nuevo

1. En Infisical UI: crear los secrets del nuevo servicio en el folder correspondiente
2. En código del servicio: `require('../lib/infisical').get('KEY_NAME', '/folder')`
3. Agregar `INFISICAL_CLIENT_ID` y `INFISICAL_CLIENT_SECRET` al `.env` o systemd Environment del servicio (mientras siga usando `admin-bootstrap`)
4. Restart del servicio

### Para Santi cuando quiera revocar un acceso

1. En Infisical UI: Identity → revoke client secret → confirm
2. Generar uno nuevo si el servicio lo sigue necesitando
3. Update Infisical credentials del servicio + restart

---

## 14. Tabla de contactos / endpoints clave

| Recurso | URL / Path |
|---|---|
| Infisical UI | https://vps-contabo.tail44c420.ts.net (solo tailnet) |
| Infisical API | mismo dominio + `/api/v1/...` |
| Tailscale admin | https://login.tailscale.com/admin |
| Panel Contabo VPS | https://my.contabo.com |
| Cloudflare dashboard | https://dash.cloudflare.com |
| Hostinger panel | https://hpanel.hostinger.com |
| BotFather Telegram | https://t.me/BotFather |
| GitHub repos | https://github.com/larevo1111 |
