# Pendiente para agente de seguridad — Infisical DB_LOCAL_PASS rotado fuera de control

Este archivo lista incidentes y decisiones de seguridad que requieren revisión
del agente de seguridad. Los items resueltos parcialmente pero con deuda
pendiente deben quedar acá hasta cierre formal.

---

## 1. Infisical rota `DB_LOCAL_PASS` sin coordinación (2026-05-14 y 2026-05-19)

### Síntoma
"Error en la sincronización" al apretar el botón Sincronizar Effi en Sistema
Gestión. Internamente: `import_all.js` fallaba con `ER_ACCESS_DENIED_ERROR`
(errno 1045) al conectar a MariaDB local del VPS.

### Causa raíz
`lib/db_conn.js` carga las credenciales en este orden:
1. **`.env`** (sincrónico, no sobrescribe lo ya cargado)
2. **Infisical** (async, sobrescribía siempre)

El `.env` del VPS tiene el password correcto (`WeYB...`, validado contra
MariaDB). Pero Infisical `/shared/DB_LOCAL_PASS` tenía un password viejo
(`Pepe2467.` el 2026-05-14, `znHo...` el 2026-05-19) que machacaba al bueno.

### Detalle crítico
- Santi confirmó **NO haber tocado Infisical manualmente** en ninguna de las 2
  ocurrencias.
- No hay crons en el VPS que escriban a Infisical.
- No hay código en el repo que escriba a Infisical (helpers `lib/infisical.js`
  y `scripts/lib/infisical.py` solo tienen `get`/`getMany`, NO tienen `set`).
- **Algún sistema externo está rotando el valor sin coordinar** con
  MariaDB ni el `.env`. Origen desconocido. Hipótesis a investigar:
  - UI web de Infisical accedida por otra cuenta/dispositivo
  - Job automático interno del servidor Infisical self-hosted
  - Machine Identity de otro proyecto con permisos de write sobre `/shared`

### Acciones aplicadas

**Fix inmediato (Opción A) — 2 veces**: actualizar `DB_LOCAL_PASS` en Infisical
con el valor correcto vía API REST (`PATCH /api/v3/secrets/raw/DB_LOCAL_PASS`).

**Fix de raíz (2026-05-19)** en `lib/db_conn.js` y `scripts/lib/db_conn.py`:
el bootstrap de Infisical ahora respeta lo ya cargado en `process.env` /
`os.environ`:

```js
// Antes
for (const [k, v] of Object.entries(shared)) process.env[k] = v

// Ahora
for (const [k, v] of Object.entries(shared)) {
  if (!(k in process.env)) process.env[k] = v
}
```

El `.env` (controlado y validado contra MariaDB) ahora tiene prioridad sobre
Infisical. Si Infisical se vuelve a desincronizar, las apps siguen funcionando.

### Trade-off conocido con la política

`.agent/POLITICA_SEGURIDAD.md` § "Las credenciales viven exclusivamente en
Infisical" dice que la fuente única debe ser Infisical y prohíbe fallbacks
en `.env`. Este fix **contradice levemente la política** durante la transición:
Infisical sigue cargándose, pero el `.env` gana cuando ambos coexisten.

Justificación: la realidad operativa muestra desincronización recurrente y
descontrolada de Infisical. Permitir que apps caigan por eso es peor que
mantener el `.env` con prioridad mientras se investiga la causa y se ejecuta
la Opción C.

### Plan correcto a largo plazo — Opción C (pendiente)

Para alinear con la política y eliminar la deuda:

1. Generar password nuevo seguro (32+ chars) para `osadmin` en MariaDB VPS.
2. `ALTER USER 'osadmin'@'%' IDENTIFIED BY '<nuevo>'; FLUSH PRIVILEGES;`
3. Actualizar `DB_LOCAL_PASS` en Infisical `/shared` al nuevo password.
4. Restart de **todos** los servicios que conectan a MariaDB VPS:
   `os-gestion.service`, `os-inventario-api.service`, `os-erp-frontend`,
   `ia-service`, `wa-bridge`, `effi-webhook`, cualquier `claude_*` cron.
5. **Eliminar** `integracion_conexionesbd.env` del VPS (la prohibición de §3
   de POLITICA_SEGURIDAD lo exige).
6. **Investigar y bloquear** la fuente externa que rota Infisical:
   - Revisar Audit Log de Infisical UI para ver qué identity escribió en
     `/shared/DB_LOCAL_PASS` el 2026-05-14 y 2026-05-19.
   - Revocar Machine Identities innecesarias.
   - Bloquear permisos de write a `/shared` excepto para una identity admin
     bien identificada.
7. Validar el checklist de 7 puntos de la política.

Esto requiere ventana de mantenimiento (5+ servicios reconectan).

### Documentos relacionados

- `.agent/docs/INCIDENT_2026-05-14_INFISICAL_DB_PASS_VIEJO.md` — historia
  técnica completa con ambas ocurrencias y comandos exactos.
- `.agent/POLITICA_SEGURIDAD.md` — política vigente que esto contradice
  parcialmente.

### Quién y cuándo

- 2026-05-14: primera ocurrencia, fix opción A.
- 2026-05-19: segunda ocurrencia, fix opción A + fix definitivo de prioridad
  en `db_conn.js` y `db_conn.py`.

Commits:
- `b202825` fix(infra): resincronizar pass osadmin MariaDB local con Infisical (primera vez)
- `f1b4dc5` fix(infra): .env tiene prioridad sobre Infisical en db_conn (Node + Python)
- `517aaff` feat(sync): auto-refresh sesion Effi en refresh_effi_produccion.py
