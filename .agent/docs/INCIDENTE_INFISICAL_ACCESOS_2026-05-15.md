# Incidente: Accesos a Infisical desde sesiones interactivas + desfase de pass MariaDB local

**Descubrimiento**: 2026-05-15
**Estado**: ✅ Resuelto 2026-05-18 — Hallazgo 2 corregido. Hallazgo 1 pendiente (Machine Identity nueva)
**Pendiente**: definir solución arquitectural con agente de seguridad y aplicar
**Documentos relacionados**:
- [.agent/contextos/seguridad.md §18.7 + §18.7.1](../contextos/seguridad.md)
- [.agent/POLITICA_SEGURIDAD.md](../POLITICA_SEGURIDAD.md)
- [.agent/planes/activos/saneamiento_credenciales_2026-05-13.md](../planes/activos/saneamiento_credenciales_2026-05-13.md)

---

## Resumen ejecutivo

Mientras se trabajaba en la creación de la receta del cod 639 (variación SL del 320), se descubrieron **dos problemas independientes** vinculados al cómo las distintas formas de ejecución (apps systemd, sesiones interactivas, scripts ad-hoc, cron) acceden a Infisical y a los secrets que contiene:

1. **Sesiones Claude (y cualquier ejecución no-systemd) no hacen bootstrap a Infisical** → fallan al conectar a BD con la pass `Pepe2467.` que ya está rotada y muerta.
2. **La pass de `osadmin@MariaDB local` que está en Infisical NO coincide con la real del MariaDB local** → aunque una sesión logre cargar Infisical, sigue fallando contra la BD local. La BD del VPS sí está sincronizada.

El segundo problema es independiente del primero: incluso con bootstrap funcionando, la BD local no se puede usar. Quien sí funciona ahora mismo es: las apps en local que toman pass de Infisical (porque Infisical y MariaDB local NO coinciden, esas apps tampoco deberían funcionar — habría que verificar caso a caso, pueden estar en degradación silenciosa).

---

## Hallazgo 1 — Sesiones Claude / scripts ad-hoc no se autentican contra Infisical

### Contexto
Desde la migración a Infisical (2026-05-11) y la rotación de credenciales (2026-05-12), las apps systemd (con `EnvironmentFile=/home/osserver/tempoclv/.infisical_admin_bootstrap.env`) hacen bootstrap automático y leen la pass nueva. **Las sesiones interactivas del usuario osserver (terminal, Claude Code, scripts manuales, cron sin EnvironmentFile) NO heredan esos vars de entorno** y caen al fallback `.env` que tiene la pass vieja `Pepe2467.` (muerta desde el 12-may).

### Síntoma
```python
from lib import local
with local('effi_data') as conn:  # ❌ Access denied for user 'osadmin'@'localhost'
    ...
```

### Causa raíz
El helper `lib/db_conn.py` intenta hacer bootstrap a Infisical pero requiere `INFISICAL_HOST + INFISICAL_PROJECT_ID + INFISICAL_CLIENT_ID + INFISICAL_CLIENT_SECRET` en `process.env`. Sin esos vars, `_infisical_get_many('/shared')` falla silenciosamente y queda con la pass del `.env` vieja.

### Workaround temporal (efímero, solo sesión actual)
```bash
set -a; source /home/osserver/tempoclv/.infisical_admin_bootstrap.env; set +a
# Ahora todos los scripts python dentro de esta sesión sí cargan Infisical
```

Aplicado durante la sesión 2026-05-15. Se pierde al cerrar la terminal.

### Es paralelo al §18.4 de seguridad.md
El §18.4 documenta exactamente el mismo bug pero del lado de las apps del VPS (sus units systemd no declaran `EnvironmentFile=`, así que también caen al `.env` viejo). Ambos casos comparten la causa: el bootstrap a Infisical depende de variables de entorno inyectadas explícitamente, y cualquier ejecución que no las tenga falla.

### 4 soluciones a evaluar (con agente de seguridad)
1. **Wrapper shell**: `~/.bashrc` o un script de inicio de sesión que `source` el bootstrap antes de cualquier comando interactivo. Simple pero scope amplio.
2. **Auto-bootstrap del helper Python/JS**: si `INFISICAL_CLIENT_SECRET` no está en env y el archivo de bootstrap existe con perms `600` osserver, leerlo. Cero fricción para scripts ad-hoc, sin cambios de comportamiento para apps systemd. **Pero usa el token admin-bootstrap (scope completo) que estaba marcado para revocar** → contradice política sin acción adicional.
3. **CLI de Infisical**: ejecutar todo via `infisical run -- python script.py`. Limpio pero requiere cambiar workflows.
4. **Machine Identity nueva con scope mínimo**: crear `claude-session-integraciones-os` con acceso solo a `/shared/`. Token guardado en `.env` del repo o `~/.config/claude-os.env` con perms `600`. Acorde a la política. **Recomendado por política.**

### Decisión esperada
Crear Machine Identity nueva (opción 4) — requiere acceso a UI de Infisical (`https://vps-contabo.tail44c420.ts.net`) que solo tiene Santi.

---

## Hallazgo 2 — Pass de MariaDB local desincronizada con Infisical

### Contexto
Durante la rotación del 2026-05-12 (§18.2 de seguridad.md), se generaron passes nuevas para 8 cuentas y se actualizaron tanto en los sistemas (Linux/MariaDB) como en Infisical. **La pass de `osadmin` en MariaDB local quedó desincronizada con la que se subió a Infisical**.

### Síntoma
```bash
# Pass de Infisical
$ python3 -c "from lib.infisical import get_many; print(get_many('/shared')['DB_LOCAL_PASS'])"
WeYBeOXXXXXX  # 12 chars random

# Pass real de MariaDB
$ mariadb -u osadmin -p"WeYBeOXXXXXX" -e "SELECT 1"
ERROR 1045 (28000): Access denied for user 'osadmin'@'localhost'

# Hash autenticación
$ sudo mariadb -e "SELECT user,host,authentication_string FROM mysql.user WHERE user='osadmin'"
osadmin  %             *83BB46459950B18338C9AE1B910CE612B4F98B33
osadmin  172.18.0.%    *83BB46459950B18338C9AE1B910CE612B4F98B33
```

El hash `*83BB...` NO corresponde al string `WeYBeOXXXXXX` que está en Infisical.

### Hipótesis del desfase
- **Hipótesis A (probable)**: la pass se subió a Infisical pero el `ALTER USER 'osadmin'@'%' IDENTIFIED BY '...'` en MariaDB local falló o se aplicó con un valor distinto (script que se cortó a la mitad, race condition, copia/paste mal).
- **Hipótesis B**: alguien ejecutó otro `ALTER USER` después y no actualizó Infisical.

### Consecuencia operativa
- **`sync_hostinger.py` falla** (escribe a `effi_data` local con `cfg_local()` → Infisical OK pero MariaDB rechaza). Resultado: cambios en Effi (catálogo, OPs, trazabilidad) NO se propagan al VPS desde el 12-may.
- **`sync_inventario_catalogo.py` falla** (lee/escribe `inv_catalogo_articulos` en local).
- **`import_all.js`** probablemente también, hay que verificar.
- **El cod 639 que Santi creó hoy 15-may en Effi.com.co no aparece en `os_integracion` VPS** (síntoma original que llevó al descubrimiento).

### Acción correctiva
1. Generar nueva pass random (32 chars limpios: `openssl rand -base64 48 | tr -d '/+=' | cut -c1-32`)
2. Aplicar simultáneamente con script atómico:
   - `ALTER USER 'osadmin'@'%' IDENTIFIED BY '<NUEVA>'; ALTER USER 'osadmin'@'172.18.0.%' IDENTIFIED BY '<NUEVA>'; FLUSH PRIVILEGES;`
   - `PATCH /api/v3/secrets/raw/DB_LOCAL_PASS` en Infisical con `<NUEVA>`
3. Verificar con `mariadb -u osadmin -p"<NUEVA>" -e "SELECT 1"`
4. Re-correr `sync_hostinger.py` y `sync_inventario_catalogo.py` para purgar el atraso de 3 días
5. Revisar `journalctl -u effi-pipeline.service --since "2026-05-12"` para evaluar daño acumulado

### Falta verificar (auditoría completa)
- Si las apps locales que también usan `/shared/DB_LOCAL_PASS` están funcionando (puede que haya una capa de cache o que tengan la pass vieja en `.env` por puro accidente y eso las salve hasta que reinicien).
- Verificar `/shared/MARIADB_PASS` (otra clave que también tiene la pass de osadmin según §18.2 — debe coincidir con `/shared/DB_LOCAL_PASS`).

---

## Por qué no se detectó antes

- **Apps systemd usan `lib/db_conn`**: leen Infisical → cae el bootstrap → leen `.env` viejo → fallan. **Pero**: la mayoría de apps locales se reiniciaron después del 12-may con el `.env` actualizado (workaround de §18.2), así que sus errores son intermitentes y no cantan en logs post-deploy.
- **Apps VPS** (que sí tenían `EnvironmentFile=` ya desde el deploy de Infisical): leen pass nueva de Infisical, conectan al MariaDB del VPS (cuyas passes sí coinciden) → funcionan OK. Por eso no se notó nada hasta tocar la BD local.
- **El sync_hostinger.py corre en cron** de la máquina local. Falla silenciosamente (los errores van a `journalctl` que nadie revisa diariamente).
- **El sistema "anda en general"** porque las apps web siguen funcionando contra la BD del VPS. Solo el pipeline local→VPS está roto.

---

## Acciones para el agente de seguridad

Cuando se aborden estos hallazgos:

1. **Aplicar acción correctiva del Hallazgo 2** (re-rotación pass MariaDB local + sync Infisical) — bloqueante para que el pipeline vuelva a funcionar.
2. **Decidir solución arquitectural del Hallazgo 1** (recomendada: Machine Identity nueva con scope `/shared/`).
3. **Sumar al plan de saneamiento (§Fase 5 — Validación final)**: incluir prueba quirúrgica para detectar desfases Infisical↔sistema. Idea: por cada secret en `/shared/DB_*_PASS`, intentar conectar al sistema target y verificar éxito. Cron mensual.
4. **Revisar §18.4 (apps VPS sin Infisical client)** — el problema sigue vigente (los workaround manuales no son sostenibles). Está en la lista de pendientes de §18.5 punto 1.
5. **Auditar logs del pipeline** desde 12-may para cuantificar atraso de datos en VPS.

---

## Historial

| Fecha | Cambio |
|---|---|
| 2026-05-15 | Versión inicial. Documentado durante creación de receta cod 639 (sesión Claude). Workaround temporal aplicado (source del bootstrap en sesión). Recetas SL pudieron crearse usando BD VPS (que sí está sincronizada con Infisical), pero el sync local→VPS sigue roto y los nuevos cods de Effi no llegarán al VPS hasta que se resuelva el Hallazgo 2. |
| 2026-05-18 | **Hallazgo 2 resuelto**: nueva password de 32 chars generada con `openssl rand`, `ALTER USER` aplicado en MariaDB local (`%` y `172.18.0.%`), `/shared/DB_LOCAL_PASS` y `/shared/MARIADB_PASS` actualizados en Infisical via API. Las 4 BDs locales (ia_service_os, effi_data, os_whatsapp, espocrm) conectan sin error. Servicios ia-service, os-telegram-bot, wa-bridge reiniciados. Pipeline relanzado para purgar 6 días de atraso. Fix colateral: `diagnostico_diario.py` corregido — sección HOSTINGER ahora usa `from lib import integracion` (SSH tunnel real) en lugar de TCP directo a VPS:3306. 10 procesos OpenCode atascados (desde 2026-05-03, ~1.8GB RAM) eliminados. **Hallazgo 1 pendiente**: sesiones Claude/scripts ad-hoc sin bootstrap Infisical → requiere Machine Identity nueva con scope `/shared/` (UI Infisical, sólo Santi). |
