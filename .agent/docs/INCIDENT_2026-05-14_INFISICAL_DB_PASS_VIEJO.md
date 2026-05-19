# Incident 2026-05-14 — Infisical sobrescribía DB_LOCAL_PASS con valor viejo

## Síntoma

El botón "Sincronizar Effi" en el Sistema Gestión OS mostraba toast rojo:
**"Error en la sincronización"**. El sync había estado roto desde algún momento posterior a la migración a Infisical (2026-05-11).

## Diagnóstico

`scripts/refresh_effi_produccion.py` exporta + invoca `import_all.js`. El último paso fallaba con:

```
ER_ACCESS_DENIED_ERROR
errno: 1045 sqlState: '28000'
```

Investigando el orden de carga de credenciales en `lib/db_conn.js`:

1. `cargarEnv(.env)` — sincrónico, NO sobrescribe (`if (!(k in process.env))`)
2. `_bootstrapInfisical()` — async, **SÍ sobrescribe** (`process.env[k] = v`)

Resultado:

| Origen | DB_LOCAL_PASS |
|---|---|
| `integracion_conexionesbd.env` (VPS) | `WeYBeOGF02TGtHr5CngB9KBi` ✅ (válido contra MariaDB) |
| Infisical `/shared` | `Pepe2467.` ❌ (password viejo, sobrescribía) |

El `.env` tenía el password correcto (cambiado al instalar MariaDB en VPS), pero Infisical guardaba uno viejo que el bootstrap async escribía DESPUÉS y machacaba el bueno.

## Fix aplicado (Opción A — 2026-05-14)

Actualizar el secret `DB_LOCAL_PASS` en Infisical `/shared` con el password actual real de MariaDB en VPS.

Hecho vía API REST de Infisical (no hay CLI instalado, ni el helper `lib/infisical.js` expone `set`):

- Login con Machine Identity (`/api/v1/auth/universal-auth/login`)
- PATCH a `/api/v3/secrets/raw/DB_LOCAL_PASS` con `workspaceId`, `environment=prod`, `secretPath=/shared`, `secretValue=<nuevo>`
- Verificación GET pre/post

Restart `os-gestion.service` para que el helper Infisical lea el valor actualizado.

## Plan correcto largo plazo (Opción C)

**Rotar el password de MariaDB del VPS** y guardar el nuevo en Infisical (donde ya solo viviría una vez). Pasos:

1. Generar password nuevo seguro (32+ chars).
2. `ALTER USER 'osadmin'@'%' IDENTIFIED BY '<nuevo>'; FLUSH PRIVILEGES;` en MariaDB VPS.
3. Actualizar `DB_LOCAL_PASS` en Infisical `/shared` al nuevo password (mismo método API que el fix A).
4. Restart todos los servicios que conectan a MariaDB del VPS: `os-gestion.service`, `os-inventario-api.service`, `os-erp-frontend`, `ia-service`, `wa-bridge`, etc.
5. Actualizar el `integracion_conexionesbd.env` local del servidor para que no quede desactualizado (o **eliminarlo** ya que el fallback se considera deuda — punto §80 de POLITICA_SEGURIDAD).
6. Validar el checklist de 7 puntos de la política.

**Pendiente**: ejecutar la opción C cuando haya ventana de mantenimiento. Por ahora el sistema funciona con la opción A.

## Lecciones

- `lib/db_conn.js` actualmente prioriza Infisical sobre `.env`. Eso es **correcto** según la política — pero implica que cualquier desfase entre el password real de MariaDB y el de Infisical rompe TODO. La fuente de verdad debe ser Infisical, no el `.env`.
- El `.env` debería eliminarse después de migrar todas las credenciales (la política § "Prohibiciones absolutas" lo exige).
- Falta una verificación de salud que detecte estos desfases sin esperar a que un operador haga clic en "Sincronizar Effi".

---

## Reincidencia 2026-05-19

El bug se repitió en la misma forma exacta: Infisical tenía un password viejo
(`znHo...`) y el `.env` el bueno (`WeYB...`). Santi confirmó que **NO ha tocado
Infisical manualmente**. No hay crons ni scripts del repo que escriban a Infisical.
La rotación viene de algún sistema externo desconocido (posiblemente la UI web
de Infisical accedida por otro dispositivo / cuenta, o un job interno del
servidor Infisical).

## Fix definitivo (2026-05-19)

Cambio de prioridad en los helpers de carga de credenciales:

- `lib/db_conn.js` (Node) — el bootstrap de Infisical ahora hace
  `if (!(k in process.env)) process.env[k] = v`. Si la variable ya viene del
  `.env`, **no se sobreescribe**.
- `scripts/lib/db_conn.py` (Python) — mismo principio con `if _k not in os.environ`.

Esto invierte la jerarquía: ahora el `.env` (cuyo valor podemos validar
contra MariaDB en cualquier momento) tiene prioridad. Infisical pasa a ser
"fallback" para variables ausentes en el `.env`.

**Trade-off conocido**: contradice levemente la política § "Infisical es fuente
única" durante la transición. Pero la realidad operativa muestra que algo está
rotando Infisical fuera de nuestro control, y la consecuencia (apps caídas
por desincronización) es peor que el incumplimiento parcial de la política.
La meta de Opción C (rotar MariaDB + eliminar `.env`) sigue vigente — cuando
se ejecute, ya no habrá `.env` y este flag no aplicará.

Si Infisical cae completamente, todo sigue funcionando con `.env`.
Si Infisical se desincroniza (como pasó 2 veces), el `.env` rescata.
