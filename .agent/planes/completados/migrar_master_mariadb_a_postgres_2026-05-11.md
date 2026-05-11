# Plan: Migrar conexión `db.master` de MariaDB a PostgreSQL

**Inicio**: 2026-05-11
**Estado**: ✅ password confirmado, listo para ejecutar tras OK final de Santi
**Trigger**: el agente que migró el ERP a Postgres movió `sos_master_erp` allá, pero el código del Sistema Gestión sigue apuntando a MariaDB (que ya no tiene esa BD).

---

## Contexto

- **Antes (hasta 9-may-2026 ~04:00 AM)**: `sos_master_erp` vivía en MariaDB del VPS (puerto 3306, user `os_master`).
- **Después**: la BD fue dropeada de MariaDB y migrada a PostgreSQL 16 (puerto 5432, user `osadmin`). Mismas 16 tablas (sis_usuarios, sis_usuarios_empresas, sis_empresas, sis_modulos, sis_roles, etc.), mismas columnas relevantes.
- **El proceso `os-gestion`** sigue corriendo con `nivelCache` en memoria del 9-may 02:55 AM, por eso login con JWT viejos sigue funcionando, pero queries a master en runtime fallan con `Table 'sos_master_erp.sis_usuarios' doesn't exist`.

## Credenciales confirmadas

| Campo | Valor |
|---|---|
| Host | `127.0.0.1` (mismo VPS, local) |
| Puerto | `5432` |
| Usuario | `osadmin` |
| Password | `4EB1fyLW7iMWLx2ZmGUW` |
| Database | `sos_master_erp` |
| Auth method | `scram-sha-256` (según `/etc/postgresql/16/main/pg_hba.conf`) |

**Probado**: `psql ... SELECT email, nombre, nivel_global FROM sis_usuarios LIMIT 3` devuelve 3 filas ✓

## Estado actual vs deseado

| Componente | Hoy | Mañana |
|---|---|---|
| BD master | apunta a MariaDB `sos_master_erp` (no existe) | apunta a Postgres `sos_master_erp` |
| Driver Node | `mysql2` para todo | `mysql2` para mariadb, **`pg`** para postgres (ambos en `lib/db_conn.js`) |
| User connect | `os_master` (MariaDB) | `osadmin` (Postgres) |
| Placeholders SQL | `?` (MySQL) | `$1, $2, $3...` (Postgres) — manejado por el **adapter unificado** |
| Otras BDs | MariaDB (gestion, integracion, inventario, comunidad) | **se quedan en MariaDB** (sin cambios) |
| Helper central | `lib/db_conn.js` solo mysql2 | `lib/db_conn.js` mysql2 + pg (extensible para futuras BDs Postgres) |

---

## Inventario EXHAUSTIVO de queries master

**13 ocurrencias de `db.master.query()` en `sistema_gestion/api/server.js`**. Todas SELECT (sin INSERT/UPDATE/DELETE).

### Q1 — Línea 70 — `refrescarNiveles()` (cron interno cada 5 min)
```js
const [rows] = await db.master.query('SELECT email, nivel_global AS nivel FROM sis_usuarios')
```
- **Sin placeholders**, sin filtros.
- Tipos: VARCHAR(150), INTEGER.
- Compatible Postgres ✓

### Q2 — Línea 267 — `POST /api/gestion/auth/google` (login Google)
```js
const [[usuario]] = await db.master.query(
  'SELECT email, nombre, nivel_global, estado FROM sis_usuarios WHERE email = ?',
  [email]
)
```
- 1 placeholder `?`. Adapter convierte a `$1`.
- Destructuring `[[usuario]]` → `rows[0]`.
- Compatible Postgres ✓

### Q3 — Línea 277 — `POST /api/gestion/auth/google` (empresas del usuario)
```js
const [empresas] = await db.master.query(`
  SELECT e.uid, e.nombre, e.siglas, ue.nivel_empresa AS nivel_ue
  FROM sis_usuarios_empresas ue
  JOIN sis_empresas e ON e.uid = ue.empresa_uid
  WHERE ue.usuario_email = ? AND ue.estado = 'activo' AND (e.estado = 'activa' OR e.estado IS NULL)
  ORDER BY e.nombre
`, [email])
```
- 1 placeholder.
- JOIN + WHERE con literal `'activo'` (Postgres usa `'activo'` igual).
- `ORDER BY e.nombre` → compatible.
- Compatible Postgres ✓

### Q4 — Línea 347 — `POST /api/gestion/auth/seleccionar_empresa`
```js
const [[emp]] = await db.master.query(`
  SELECT e.uid, e.nombre, e.siglas
  FROM sis_usuarios_empresas ue
  JOIN sis_empresas e ON e.uid = ue.empresa_uid
  WHERE ue.usuario_email = ? AND ue.empresa_uid = ? AND ue.estado = 'activo' AND (e.estado = 'activa' OR e.estado IS NULL)
`, [decoded.email, empresa_uid])
```
- 2 placeholders → `$1, $2`.
- Compatible Postgres ✓

### Q5 — Línea 441 — `GET /api/gestion/usuarios` (lista usuarios empresa)
```js
const [rows] = await db.master.query(`
  SELECT u.email, u.nombre,
         u.nivel_global AS nivel, u.foto_url AS foto, ue.rol_uid AS rol
  FROM sis_usuarios_empresas ue
  JOIN sis_usuarios u ON u.email = ue.usuario_email
  WHERE ue.empresa_uid = ? AND ue.estado = 'activo' AND u.estado = 'activo'
  ORDER BY u.nombre
`, [req.empresa])
```
- 1 placeholder.
- Alias `AS nivel`, `AS foto`, `AS rol` → compatible Postgres (con lowercase).
- Compatible Postgres ✓

### Q6, Q7, Q8 — Líneas 672, 742, 823 — adorno nombre en tareas/proyectos
```js
const [users] = await db.master.query(
  `SELECT email, nombre FROM sis_usuarios WHERE email IN (${allEmails.map(() => '?').join(',')})`,
  allEmails
)
```
- N placeholders (variable según tamaño array).
- **WHERE col IN (?, ?, ?)** con array dinámico → adapter convierte a `$1, $2, $3`.
- ⚠️ **Cuidado**: si `allEmails.length = 0`, el SQL queda `IN ()` → error en Postgres. Verificar guard `if (allEmails.length)` antes.
  - Q6 (línea 670): `if (allEmails.length)` ✓
  - Q7 (línea 740): TODO verificar
  - Q8 (línea 821): TODO verificar
- Compatible Postgres con guard ✓

### Q9 — Línea 1653 — adorno nombre en otro endpoint
```js
const [users] = await db.master.query(
  `SELECT email, nombre FROM sis_usuarios WHERE email IN (${emails.map(()=>'?').join(',')})`,
  emails
)
```
- Igual a Q6/7/8. Verificar guard. Compatible Postgres ✓

### Q10 — Línea 2020 — `_jobValidar` lookup nombre del que procesó
```js
const [[uMaster]] = await db.master.query(
  'SELECT nombre FROM sis_usuarios WHERE email = ?',
  [procRow[0].procesado_por]
)
```
- 1 placeholder, dentro de try/catch que solo escribe a log si falla.
- Compatible Postgres ✓

### Q11 — Línea 3463 — `GET /api/gestion/jornadas/historial` (filtro por nivel)
```js
const [usuariosInferiores] = await db.master.query(
  'SELECT email FROM sis_usuarios WHERE nivel_global < ?',
  [req.usuario.nivel]
)
```
- 1 placeholder, comparación INT.
- Compatible Postgres ✓

### Q12 — Línea 3490 — `GET /api/gestion/jornadas/historial` (enriquecer nombres)
```js
const [users] = await db.master.query(
  `SELECT email, nombre FROM sis_usuarios WHERE email IN (${emails.map(() => '?').join(',')})`,
  emails
)
```
- Igual patrón. Guard previo: `if (jornadas.length)` (línea 3488) ✓
- Compatible Postgres ✓

### Q13 — Línea 3724 — `GET /api/gestion/jornadas/equipo` (enriquecer nombres + nivel)
```js
const [usuarios] = await db.master.query(
  `SELECT email, nombre, nivel_global FROM sis_usuarios WHERE email IN (${placeholders})`,
  emails
)
```
- Guard previo: `if (jornadas.length > 0)` (línea 3721) ✓
- Compatible Postgres ✓

---

### Inventario PYTHON (módulos que también usan master)

**3 archivos** usan `from lib import master` (de `scripts/lib/db_conn.py`):

#### P1 — `scripts/produccion/api.py` (servicio FastAPI activo en VPS)
- **Línea 68-76** `_buscar_usuario_os(email)` — login Google del módulo Producción
- **Línea 142-...** `GET /api/produccion/encargados` — **AQUÍ está el bug que ve Santi** (no aparecen encargados)
- Uses: `with master(dict_cursor=True) as conn` + `cur.execute("... %s", (val,))`
- Placeholders: `%s` (pymysql) → psycopg también usa `%s` → **CERO cambios en queries** ✓

#### P2 — `scripts/notif_jornadas_abiertas.py` (cron)
- Notifica por Telegram jornadas que quedaron abiertas
- Lookup nombres de usuarios desde master

#### P3 — `scripts/notif_jornada_no_iniciada.py` (cron)
- Notifica jornadas que no se iniciaron
- Lookup nombres de usuarios desde master

**Buena noticia**: en Python, `psycopg2`/`psycopg` usa exactamente la misma sintaxis de placeholders `%s` que `pymysql`. Las queries NO cambian. Solo cambia el módulo importado y el cursor (manejado dentro del helper).

### Resumen del análisis

| Aspecto | Verificación |
|---|---|
| Total queries Node | 13 |
| Total queries Python | 5+ (en 3 archivos) |
| INSERT/UPDATE/DELETE | 0 (todas SELECT) |
| `GROUP_CONCAT` | 0 (no se usa en queries master) |
| `IFNULL` / `ISNULL` | 0 (no se usa) |
| `LIMIT N` (sin OFFSET) | 0 (queries master no paginan) |
| Placeholders `?` | Sí — el adapter los convierte a `$N` |
| `WHERE col IN (?,?,?)` con array vacío | Existen 5 queries (Q6-9, Q12, Q13) — TODAS tienen guard antes ✓ |
| Tipos especiales (JSON, BOOLEAN, BLOB) | 0 — solo VARCHAR/INTEGER |
| Funciones MySQL-only | 0 |

**Compatibilidad: 100%. CERO refactor de queries necesario** si uso adapter.

---

## Arquitectura — helper central (NO hardcode en cada app)

**Regla CLAUDE.md (REGLA ABSOLUTA — Conexiones a BD)**: todas las credenciales y los pools viven en **`lib/db_conn.js`** (helper único). Las apps importan y usan los getters.

Sigo ese patrón: agrego soporte Postgres al helper central, y `sistema_gestion/api/db.js` solo expone el getter como hace con los otros pools.

Esquema:

```
lib/db_conn.js
├── pools mysql2 (mariadbd)
│   ├── _remotas.GESTION      (MariaDB SSH/direct)
│   ├── _remotas.INTEGRACION  (MariaDB SSH/direct)
│   ├── _remotas.INVENTARIO   (MariaDB SSH/direct)
│   └── _remotas.COMUNIDAD    (MariaDB SSH/direct)
├── pools pg (postgresql) ← NUEVO
│   └── _remotasPg.MASTER     (Postgres direct/local)
├── adapter mysql2-compat para pools pg ← NUEVO
└── API pública
    ├── gestion(), integracion(), inventario(), comunidad()  (mysql2)
    └── master()  → adapter pg con API mysql2 ← MIGRA aquí

sistema_gestion/api/db.js
└── solo getters: master, gestion, integracion, inventario, comunidad
    (sin tocar al cambiar la BD subyacente)
```

**Beneficios**:
- Si mañana migramos `gestion` o `integracion` a Postgres también, agrego `_remotasPg.GESTION` con la misma lógica del helper. Sin tocar `sistema_gestion/api/db.js` ni queries.
- ia-admin, frontend ERP, etc. importan del mismo helper: si requieren master en el futuro, una sola línea: `const pool = await db.master()`.
- Las credenciales siguen en `integracion_conexionesbd.env` exclusivamente.

---

## Plan de ejecución

### Paso 1 — Credenciales (sin tocar VPS aún)
Agregar al `integracion_conexionesbd.env` (gitignored) y al `.env.example`:

```ini
# Master en Postgres (migración 2026-05-09)
DB_MASTER_PG_HOST=127.0.0.1
DB_MASTER_PG_PORT=5432
DB_MASTER_PG_USER=osadmin
DB_MASTER_PG_PASS=4EB1fyLW7iMWLx2ZmGUW
DB_MASTER_PG_NAME=sos_master_erp
```

Las variables viejas `DB_MASTER_*` (MariaDB) → eliminar del `.env` real, dejar comentadas en `.example` con nota.

### Paso 2 — Instalar driver `pg` en el helper central
```bash
cd lib && npm install pg
```
- O `cd <raíz repo> && npm install pg` si lib/ no tiene package.json propio.
- Tiempo: ~10s.
- Sin SSH tunnel — Postgres es local al VPS.

### Paso 3 — Extender `lib/db_conn.js` con soporte Postgres + adapter

Agrego al final del módulo (antes del `module.exports`):

```js
// ─── Postgres pools (NUEVO 2026-05-11) ────────────────────────────
// Sigue el mismo patrón que mysql2 pero usa pg. Adapter mysql2-compat
// para que los consumers que esperan `const [rows] = await pool.query(...)`
// sigan funcionando sin cambios.

let _Pg = null
function _loadPg() {
  if (!_Pg) _Pg = require('pg')
  return _Pg
}

const _remotasPg = {
  MASTER: { pool: null, ready: false, adapter: null },
}

function _cfgPg(prefijo) {
  return {
    host:     process.env[`DB_${prefijo}_PG_HOST`] || '127.0.0.1',
    port:     parseInt(process.env[`DB_${prefijo}_PG_PORT`] || '5432', 10),
    user:     process.env[`DB_${prefijo}_PG_USER`],
    pass:     process.env[`DB_${prefijo}_PG_PASS`],
    database: process.env[`DB_${prefijo}_PG_NAME`],
  }
}

function _adapterPg(pool) {
  return {
    async query(sql, params = []) {
      let i = 0
      const pgSql = sql.replace(/\?/g, () => `$${++i}`)
      const r = await pool.query(pgSql, params)
      // Emular [rows, fields] de mysql2 — destructuring [rows] sigue funcionando
      return [r.rows, r.fields]
    },
    async getConnection() { return pool.connect() }
  }
}

async function _conectarPg(prefijo) {
  const st = _remotasPg[prefijo]
  if (st.ready && st.adapter) return st.adapter
  const cfg = _cfgPg(prefijo)
  if (!cfg.user || !cfg.pass || !cfg.database) {
    throw new Error(`Config DB_${prefijo}_PG_* incompleta en integracion_conexionesbd.env`)
  }
  const { Pool } = _loadPg()
  st.pool = new Pool({
    host: cfg.host, port: cfg.port,
    user: cfg.user, password: cfg.pass, database: cfg.database,
    max: 10, idleTimeoutMillis: 30000, connectionTimeoutMillis: 5000,
  })
  st.pool.on('error', (err) => console.error(`[db_conn:${prefijo} pg pool error]`, err.message))
  // Probe
  await st.pool.query('SELECT 1')
  st.adapter = _adapterPg(st.pool)
  st.ready = true
  console.log(`[db_conn:${prefijo}] Pool Postgres listo → ${cfg.host}:${cfg.port}/${cfg.database}`)
  return st.adapter
}
```

Y modifico el `module.exports` final:

```js
module.exports = {
  TIMEZONE,
  local(dbName) { return poolLocal(dbName) },
  // MySQL
  integracion() { return _conectarRemota('INTEGRACION') },
  gestion()     { return _conectarRemota('GESTION') },
  inventario()  { return _conectarRemota('INVENTARIO') },
  comunidad()   { return _conectarRemota('COMUNIDAD') },
  // Postgres
  master()      { return _conectarPg('MASTER') },   // ← CAMBIA: ahora Postgres
  // Sync getters
  get poolIntegracion() { return _remotas.INTEGRACION.pool },
  get poolGestion()     { return _remotas.GESTION.pool },
  get poolInventario()  { return _remotas.INVENTARIO.pool },
  get poolComunidad()   { return _remotas.COMUNIDAD.pool },
  get poolMaster()      { return _remotasPg.MASTER.adapter },  // ← cambia el shape
}
```

### Paso 4 — Simplificar `sistema_gestion/api/db.js`

Como el helper central ya maneja todo, `sistema_gestion/api/db.js` queda igual de simple:

```js
const central = require('../../lib/db_conn')

async function conectar() {
  // master ahora es Postgres (instantáneo, sin SSH)
  await Promise.all([
    central.master(),
    central.gestion(),
    central.integracion(),
    central.inventario(),
  ])
  intentarComunidad()
  console.log(`[db] Pools listos — timezone: ${central.TIMEZONE}`)
}

async function intentarComunidad() {
  try {
    await central.comunidad()
    console.log('[db] comunidad (Hostinger) listo (legacy)')
  } catch (err) {
    console.warn('[db] comunidad reintentando en 15s:', err.message)
    setTimeout(intentarComunidad, 15000)
  }
}

module.exports = {
  conectar,
  get master()      { return central.poolMaster },     // ahora es adapter pg
  get comunidad()   { return central.poolComunidad },
  get gestion()     { return central.poolGestion },
  get integracion() { return central.poolIntegracion },
  get inventario()  { return central.poolInventario },
}
```

Nota: el helper central elimina ya `_remotas.MASTER` viejo (mysql) y los getters lo reemplazan. Importante NO romper `db_conn.js` para apps que no usan master.

### Paso 4b — Extender `scripts/lib/db_conn.py` (Python — para producción y crons)

Mismo principio: helper central maneja la diferencia de driver. Las apps no cambian.

```python
# scripts/lib/db_conn.py — agregar al final del módulo

# ─── Soporte Postgres (NUEVO 2026-05-11) ────────────────────────
# Helper para master que ahora vive en Postgres.
# psycopg usa los mismos placeholders %s que pymysql → cero cambios en queries.

def _cfg_pg(prefijo):
    e = os.environ
    return dict(
        host     = e.get(f'DB_{prefijo}_PG_HOST', '127.0.0.1'),
        port     = int(e.get(f'DB_{prefijo}_PG_PORT', '5432')),
        user     = e.get(f'DB_{prefijo}_PG_USER'),
        password = e.get(f'DB_{prefijo}_PG_PASS'),
        database = e.get(f'DB_{prefijo}_PG_NAME'),
    )

@contextmanager
def _conn_pg(prefijo, dict_cursor=False):
    """Context manager para Postgres. API compatible con pymysql:
    `with master(dict_cursor=True) as conn: cur = conn.cursor(); cur.execute(...)`
    """
    import psycopg
    from psycopg.rows import dict_row
    cfg = _cfg_pg(prefijo)
    if not cfg['user'] or not cfg['password'] or not cfg['database']:
        raise RuntimeError(f"Config DB_{prefijo}_PG_* incompleta")
    row_factory = dict_row if dict_cursor else None
    kwargs = dict(
        host=cfg['host'], port=cfg['port'],
        user=cfg['user'], password=cfg['password'], dbname=cfg['database'],
        connect_timeout=15,
    )
    if row_factory:
        kwargs['row_factory'] = row_factory
    conn = psycopg.connect(**kwargs)
    try:
        yield conn
    finally:
        conn.close()
```

Y modificar la función `master()`:

```python
# Antes:
# def master(dict_cursor=False):  return remota('MASTER', dict_cursor)

# Después:
def master(dict_cursor=False):
    """sos_master_erp en Postgres (migrado 2026-05-09).
    Devuelve conexión psycopg con API compatible con pymysql."""
    return _conn_pg('MASTER', dict_cursor)

def cfg_master(dict_cursor=True):
    """DEPRECATED: master ahora es Postgres. Use master() context manager."""
    raise NotImplementedError(
        "cfg_master() ya no aplica — master es Postgres. Usar `with master() as conn:` directamente."
    )
```

**Diferencia API pymysql vs psycopg**:
- `pymysql.connect(database=X)` → `psycopg.connect(dbname=X)` ← parámetro distinto, manejado en helper.
- `conn.cursor()` igual.
- `cursor.execute("... %s", (val,))` igual.
- `dict_cursor`: pymysql usa `cursors.DictCursor`, psycopg usa `row_factory=dict_row` ← manejado en helper.
- **Cero cambios en código de las apps**. La API expuesta sigue siendo idéntica.

### Paso 4c — Instalar `psycopg` en VPS

```bash
sudo -u osserver pip install --user psycopg[binary]
# O en venv si los servicios usan venv
```

Verificar qué venv usan los services:
- `os-produccion-api.service` o como se llame
- `os-inventario-api.service`
- Crons

### Paso 5 — Deploy

1. **Local**:
   ```bash
   # editar .env y agregar DB_MASTER_PG_*
   # editar sistema_gestion/api/db.js
   # commit
   ```

2. **VPS**:
   ```bash
   sshpass rsync -az integracion_conexionesbd.env VPS:.../
   sshpass rsync -az sistema_gestion/api/db.js VPS:.../sistema_gestion/api/
   sshpass ssh VPS "cd sistema_gestion/api && npm install pg && systemctl restart os-gestion.service"
   ```

3. **Verificar logs**:
   ```
   [db] Pool master Postgres listo
   [db] Pools listos (gestion+integracion+inventario MariaDB, master Postgres)
   [niveles] Caché actualizado: 7 usuarios
   ```

### Paso 6 — Tests E2E (ver sección "Plan de testeo" abajo)

### Paso 7 — Commit + docs
- Bump `v2.11.13`
- Commit: `fix(gestion): migrar conexión master de MariaDB a Postgres (v2.11.13)`
- Update `CONTEXTO_ACTIVO.md`, `contextos/sistema_gestion.md`, MEMORY.md
- Mover plan a `completados/`

---

## Plan de TESTEO minucioso

### Pre-deploy (en local)
- [ ] **T0** — `node -e "require('./sistema_gestion/api/db.js')"` — sin errores de sintaxis.
- [ ] **T0b** — `npm test` en `sistema_gestion/api/` si hay tests (revisar).

### Tests funcionales post-deploy (cada query del inventario)

#### Bloque A — Auth (Q1, Q2, Q3, Q4)
- [ ] **TA1** — Restart servicio. Log debe decir `[niveles] Caché actualizado: 7 usuarios`.
  - Si falla → cae en `catch` → no rompe, pero nivelCache vacío.
- [ ] **TA2** — JWT viejo: `curl GET /api/gestion/auth/me` con JWT existente → 200 OK.
- [ ] **TA3** — Login fresco con id_token de Google **real** (Santi se loguea):
  - `POST /auth/google` → 200 OK, JWT final si 1 empresa, temporal si varias.
  - Verifica Q2 (lookup en sis_usuarios) + Q3 (empresas del usuario).
- [ ] **TA4** — Selección de empresa (si usuario multi-empresa): `POST /auth/seleccionar_empresa` → 200 OK.
  - Verifica Q4.
- [ ] **TA5** — Usuario inactivo (forzar): `UPDATE sis_usuarios SET estado='inactivo' WHERE email='test@...' ` y reintentar login → 403 esperado.

#### Bloque B — Listas de usuarios (Q5)
- [ ] **TB1** — `GET /api/gestion/usuarios` con JWT válido → 200 con lista. Comparar count vs `SELECT COUNT(*) FROM sis_usuarios_empresas WHERE empresa_uid='Ori_Sil_2' AND estado='activo'`.
- [ ] **TB2** — Verificar que cada usuario tiene `email, nombre, nivel, foto, rol`.

#### Bloque C — Adorno de nombres en tareas/proyectos (Q6, Q7, Q8, Q9)
- [ ] **TC1** — `GET /api/gestion/tareas` → cada tarea con responsables muestra `responsables_nombres` (no solo emails).
- [ ] **TC2** — Crear tarea con 3 responsables → al fetchear muestra los 3 nombres correctos.
- [ ] **TC3** — Tarea sin responsables (`responsables_csv = ''`) → no rompe (verificar guard `if (allEmails.length)`).
- [ ] **TC4** — Endpoint de proyectos/dificultades/etc. también muestra nombres.

#### Bloque D — Validar OP (Q10)
- [ ] **TD1** — Procesar y luego validar una OP de prueba (NO en producción real — usar OP test) → observación nueva debe incluir "Reportó: NombreReal" (no email).
  - **OJO**: validar dispara Playwright → solo hacer si OP de prueba existe.
- [ ] **TD1-alt** — Si no hay OP test, verificar via curl que el flujo se completa hasta el punto del lookup, mock con OP que YA fue validada.

#### Bloque E — Jornadas (Q11, Q12)
- [ ] **TE1** — `GET /api/gestion/jornadas/historial` con JWT nivel ≥7 → 200, sin filtro por usuario.
- [ ] **TE2** — `GET /api/gestion/jornadas/historial` con JWT nivel <7 → 200, solo jornadas de usuarios inferiores + propias.
  - Verifica Q11.
- [ ] **TE3** — Verificar que cada jornada tiene `nombre_usuario` correcto (no email).
  - Verifica Q12.

#### Bloque F — Equipo (Q13)
- [ ] **TF1** — `GET /api/gestion/jornadas/equipo?desde=...&hasta=...` → 200 con lista.
- [ ] **TF2** — Cada jornada debe tener `Nombre_Usuario` y `Nivel_Acceso` poblados (no null si el usuario existe en master).

### Tests de robustez

- [ ] **TR1** — Saturar el pool: 20 requests paralelos a `/api/gestion/usuarios` → todos 200 OK.
- [ ] **TR2** — Postgres caído (parar `systemctl stop postgresql`, esperar 5s, levantar): el servicio debe re-conectarse al volver.
- [ ] **TR3** — Query con email no existente en Postgres: comportamiento controlado (no rompe, devuelve null).

### Tests del adapter

- [ ] **TAD1** — Query sin placeholders → no toca SQL.
- [ ] **TAD2** — Query con 1 placeholder → convierte a `$1`.
- [ ] **TAD3** — Query con 5 placeholders → convierte a `$1, $2, $3, $4, $5` en orden.
- [ ] **TAD4** — Query con `?` dentro de un string literal (ej. `'hola?'`) → **CUIDADO**: el regex `/\?/g` reemplaza TODOS los `?` aunque estén dentro de strings.
  - **Verificación**: revisar las 13 queries del inventario. Ninguna tiene `?` dentro de strings literales. ✓
  - **Defensa futura**: si alguien agrega query con literal `?`, debe escapar o usar `$1` directo. Documentar.

### Tests de regresión (NO se debe romper)
- [ ] **TZ1** — Tareas/OPs/Solicitudes siguen funcionando (queries a `db.gestion`, `db.integracion`, `db.inventario` no se tocaron).
- [ ] **TZ2** — Cron `os-gestion auto-cierre` jornadas sigue corriendo (no toca master).
- [ ] **TZ3** — Bot Telegram / IA Service / Pipeline Effi (otros servicios) siguen operativos.
- [ ] **TZ4** — Inventario físico (`inv.oscomunidad.com`) sigue OK — NO usa master.

### Tests Python — Módulo Producción (`prod.oscomunidad.com`)
- [ ] **TP1** — Reiniciar `os-produccion-api.service` (o como se llame). Log debe arrancar sin errores.
- [ ] **TP2** — Login Google a producción: `POST /api/auth/google` con id_token real → 200 OK con JWT.
  - Verifica P1 (`_buscar_usuario_os`).
- [ ] **TP3** — `GET /api/produccion/encargados` con JWT válido → **devuelve lista de encargados con nombre y CC** (este es el bug actual).
  - Verifica P1 (`listar_encargados`).
- [ ] **TP4** — Frontend Producción: al programar una OP, el dropdown de encargados debe mostrar Deivy, Laura, Santi, Jenifer, etc. con sus nombres y CC.

### Tests Python — Crons
- [ ] **TP5** — Ejecutar manualmente `python3 scripts/notif_jornadas_abiertas.py` → no debe fallar al consultar master.
- [ ] **TP6** — Ejecutar manualmente `python3 scripts/notif_jornada_no_iniciada.py` → idem.

### Rollback test
- [ ] **TR-rollback** — Revertir `db.js` al backup `db.js.bak` y restart → estado anterior (jornadas/equipo rotos pero login con JWT viejo OK).

---

## Cosas que NO hago

- ❌ Crear usuario nuevo Postgres (uso `osadmin` como dijo Santi).
- ❌ Migrar otras BDs (gestion, integracion, inventario, comunidad) — siguen en MariaDB.
- ❌ Modificar permisos de `osadmin` (ya es Superuser).
- ❌ Tocar el código de pipeline / IA Service / WA Bridge.
- ❌ Habilitar binlogs MariaDB.
- ❌ Eliminar usuario `os_master` de MariaDB (lo dejo huérfano por si acaso, no afecta).

## Riesgo y rollback

- **Riesgo**: Bajo. Adapter mantiene API idéntica a mysql2. Si algo falla, rollback es 1 línea (revertir `db.js`).
- **Rollback**:
  1. `sshpass ssh VPS "cp sistema_gestion/api/db.js.bak sistema_gestion/api/db.js && systemctl restart os-gestion.service"`
  2. Estado anterior restaurado en <5 seg.

## Tiempo estimado

| Paso | Tiempo |
|---|---|
| 1 (env) | 2 min |
| 2 (npm install pg) | 1 min |
| 3 (refactor db.js + adapter) | 15 min |
| 4 (deploy) | 5 min |
| 5 (tests E2E completos) | 30 min |
| 6 (commit + docs) | 10 min |
| **Total** | **~60 min** |

---

## Próximo paso

**Esperando OK final de Santi para iniciar Paso 1.**

Una vez confirme, ejecuto todo en una tanda y reporto resultados de cada bloque de test.
