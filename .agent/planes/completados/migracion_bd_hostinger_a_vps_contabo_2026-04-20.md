# Plan — Migración BD Hostinger → VPS Contabo

**Creado**: 2026-04-20
**Responsable**: Claude Code
**Estado**: Preparación completada. **Pendiente: Santi da la orden de corte.**

---

## 1. Alcance

### Qué SÍ se migra

Las dos BDs que hoy viven en Hostinger y son nuestras:

| BD origen (Hostinger) | BD destino (VPS) |
|---|---|
| `u768061575_os_integracion` | `os_integracion` |
| `u768061575_os_gestion` | `os_gestion` |

### Qué NO se migra

- **BDs locales (servidor de casa)** — se quedan donde están:
  - `effi_data` — staging pipeline
  - `ia_service_os` — servicio IA
  - `espocrm` — CRM
  - `os_inventario` — inventario físico
  - `os_whatsapp` — WA Bridge
  - `nextcloud`, `nocodb_meta`, `sos_erp_local`, `ia_local` — otros
- **`u768061575_os_comunidad`** — ERP real de Effi en Hostinger. **Prohibición absoluta. NO tocar.** Sigue en Hostinger y los procesos que la consulten seguirán haciendo SSH tunnel a Hostinger solo para esa BD.

### Qué NO se toca en esta migración

- Los servicios (sistema_gestion, erp-frontend, pipeline, bot, etc.) siguen corriendo en el servidor local. Solo cambia **hacia dónde apuntan** sus conexiones a integracion + gestion.
- Cloudflare Tunnels, DNS, certificados — sin cambios.
- Las apps instaladas en el VPS (gestion-vps.oscomunidad.com) son clones/dev, no producción.

---

## 2. Servidores involucrados

| Servidor | Rol | Acceso |
|---|---|---|
| Servidor local (casa) | Corre todos los servicios (Gestión, ERP, IA, pipeline, bot, WA Bridge). Hoy es producción. | — |
| Hostinger MySQL | Host actual de `os_integracion`, `os_gestion` y `os_comunidad` | SSH `-i ~/.ssh/sos_erp -p 65002 u768061575@109.106.250.195` |
| VPS Contabo | Nuevo host de `os_integracion` y `os_gestion`. IP `94.72.115.156`, puerto 22 abierto | SSH `-i ~/.ssh/id_ed25519 osserver@94.72.115.156` (key autorizada 2026-04-20) |

---

## 3. Arquitectura posterior al corte

```
┌───────────────────────┐      ┌──────────────────────────────┐
│ Servidor LOCAL (casa) │      │        Hostinger              │
│                       │      │                                │
│ sistema_gestion       │──────┼──▶ os_comunidad (solo lectura  │
│ frontend ERP          │ SSH  │    sys_usuarios — queda ahí)   │
│ scripts Python        │ 65002│                                │
│ bot Telegram          │      └──────────────────────────────┘
│ WA Bridge             │
│ pipeline Effi         │      ┌──────────────────────────────┐
│                       │      │     VPS Contabo              │
│ BDs locales:          │      │                                │
│   effi_data           │──────┼──▶ os_integracion  (RW)       │
│   ia_service_os       │ SSH  │    os_gestion      (RW)       │
│   espocrm             │  22  │    effi_data      (dev/dup)   │
│   os_inventario       │      │    os_inventario  (dev/dup)   │
│   os_whatsapp         │      │    espocrm        (dev)       │
└───────────────────────┘      └──────────────────────────────┘
```

Cambio neto: `DB_INTEGRACION_*` y `DB_GESTION_*` en `integracion_conexionesbd.env` pasan a apuntar al VPS. Cero cambios de código (refactor previo lo permite).

---

## 4. Preparación ejecutada (2026-04-20, 16:45)

### 4.1 Centralización de conexiones (commit ece85a4)

- Todas las credenciales de BD viven en `integracion_conexionesbd.env` (gitignored).
- Helpers `lib/db_conn.js` (Node) y `scripts/lib/db_conn.py` (Python).
- 35 archivos refactorizados. Cero `host/user/password/database` hardcoded en código.
- 7 servicios validados corriendo contra Hostinger vía el helper nuevo.

### 4.2 Configuración del VPS

1. **Puerto TCP 22** abierto en panel Contabo (Santi, 2026-04-20).
2. **Timezone nativo MariaDB**: agregado `default-time-zone = "-05:00"` a `/etc/mysql/mariadb.conf.d/50-server.cnf` y `systemctl restart mariadb`.
   - Verificado: `SELECT @@global.time_zone, NOW();` → `-05:00` / hora Colombia.
3. **BDs creadas** en MariaDB VPS:
   ```sql
   CREATE DATABASE os_integracion CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE DATABASE os_gestion     CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
4. **Usuarios MySQL creados** (password `Epist2487.`, mismos grants en `127.0.0.1` y `localhost`):
   - `os_integracion` → ALL PRIVILEGES en `os_integracion`
   - `os_gestion` → ALL PRIVILEGES en `os_gestion`
5. **SSH osserver autorizado**: `~/.ssh/id_ed25519.pub` del servidor local añadido a `/home/osserver/.ssh/authorized_keys` del VPS.

### 4.3 Volcado y restauración

1. **Dumps desde Hostinger** (via SSH shell + mysqldump):
   - `/home/osserver/Proyectos_Antigravity/backups/u768061575_os_integracion/2026-04-20_164537.sql.gz` — 4.9 MB
   - `/home/osserver/Proyectos_Antigravity/backups/u768061575_os_gestion/2026-04-20_164537.sql.gz` — 36 KB
   - Comando usado:
     ```bash
     ssh -i ~/.ssh/sos_erp -p 65002 u768061575@109.106.250.195 \
       "mysqldump --single-transaction --quick --no-tablespaces \
         -u <user> -p<pass> <db>" | gzip > <ruta_backup>
     ```

2. **Import al VPS** (pipe SSH directo, sin archivo intermedio en el VPS):
   ```bash
   zcat <ruta_backup> | ssh root@94.72.115.156 "mysql <db_destino>"
   ```

### 4.4 Integridad verificada (COUNT(*) exacto, 10/10 OK)

| Tabla | Hostinger | VPS | OK |
|---|---|---|---|
| `zeffi_facturas_venta_encabezados` | 943 | 943 | ✅ |
| `zeffi_remisiones_venta_encabezados` | 2335 | 2335 | ✅ |
| `zeffi_clientes` | 498 | 498 | ✅ |
| `zeffi_trazabilidad` | 67509 | 67509 | ✅ |
| `resumen_ventas_facturas_mes` | 16 | 16 | ✅ |
| `g_tareas` | 472 | 472 | ✅ |
| `g_jornadas` | 35 | 35 | ✅ |
| `g_proyectos` | 31 | 31 | ✅ |
| `g_categorias` | 16 | 16 | ✅ |
| `g_etiquetas` | 5 | 5 | ✅ |

Dump total importado al VPS:
- `os_integracion`: 54 tablas, 66.2 MB
- `os_gestion`: 20 tablas, 1.0 MB

### 4.5 Conectividad verificada desde servidor local al VPS

```bash
ssh -i ~/.ssh/id_ed25519 -L 3399:127.0.0.1:3306 osserver@94.72.115.156
mysql --skip-ssl -h 127.0.0.1 -P 3399 -u os_integracion -pEpist2487. -D os_integracion \
  -e "SELECT NOW(), COUNT(*) FROM zeffi_facturas_venta_encabezados"
# → 2026-04-20 16:47:33 | 943 ✅
```

### 4.6 Borrador del `.env` del corte

Archivo listo: [`integracion_conexionesbd.vps.env`](../../../integracion_conexionesbd.vps.env) (gitignored por `*.env` pattern).

Diff vs el `.env` actual: solo cambian los bloques `DB_INTEGRACION_*` y `DB_GESTION_*` (valores del VPS). `DB_LOCAL_*` y `DB_COMUNIDAD_*` intactos.

---

## 5. Procedimiento de corte (EJECUTAR cuando Santi dé la orden)

### 5.1 Ventana recomendada

- Fuera del horario operativo del pipeline (L-S 06:00-20:00). **Domingo o fuera de 06-20h** reduce escrituras concurrentes.
- Aviso al equipo 15 min antes (opcional — Santi decide).

### 5.2 Pasos

```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS

# 1) Freeze: parar todo lo que escribe a integracion o gestion
sudo systemctl stop effi-pipeline.timer
sudo systemctl stop os-gestion.service
sudo systemctl stop os-erp-frontend.service
sudo systemctl stop os-ia-admin.service
sudo systemctl stop wa-bridge.service
sudo systemctl stop ia-service.service
sudo systemctl stop os-inventario-api.service
sudo systemctl stop os-telegram-bot.service   # por si acaso
# ia-local puede seguir corriendo (solo usa ia_local local, no afecta)

# 2) Dump delta final — captura cualquier escritura entre el dump inicial y ahora
TS=$(date +%Y-%m-%d_%H%M%S)
BDIR=/home/osserver/Proyectos_Antigravity/backups
ssh -i ~/.ssh/sos_erp -p 65002 u768061575@109.106.250.195 \
  "mysqldump --single-transaction --quick --no-tablespaces \
    -u u768061575_osserver -pEpist2487. u768061575_os_integracion" \
  | gzip > "$BDIR/u768061575_os_integracion/${TS}_corte.sql.gz"
ssh -i ~/.ssh/sos_erp -p 65002 u768061575@109.106.250.195 \
  "mysqldump --single-transaction --quick --no-tablespaces \
    -u u768061575_os_gestion -pEpist2487. u768061575_os_gestion" \
  | gzip > "$BDIR/u768061575_os_gestion/${TS}_corte.sql.gz"

# 3) Re-import en VPS (DROP + CREATE + restore limpio, asegura consistencia)
ssh root@94.72.115.156 "mysql -e 'DROP DATABASE os_integracion; CREATE DATABASE os_integracion CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'"
zcat "$BDIR/u768061575_os_integracion/${TS}_corte.sql.gz" \
  | ssh root@94.72.115.156 "mysql os_integracion"

ssh root@94.72.115.156 "mysql -e 'DROP DATABASE os_gestion; CREATE DATABASE os_gestion CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'"
zcat "$BDIR/u768061575_os_gestion/${TS}_corte.sql.gz" \
  | ssh root@94.72.115.156 "mysql os_gestion"

# 4) Re-grant (DROP DATABASE borra grants, hay que recrearlos)
ssh root@94.72.115.156 "mysql <<'SQL'
GRANT ALL PRIVILEGES ON os_integracion.* TO 'os_integracion'@'127.0.0.1';
GRANT ALL PRIVILEGES ON os_integracion.* TO 'os_integracion'@'localhost';
GRANT ALL PRIVILEGES ON os_gestion.*     TO 'os_gestion'@'127.0.0.1';
GRANT ALL PRIVILEGES ON os_gestion.*     TO 'os_gestion'@'localhost';
FLUSH PRIVILEGES;
SQL"

# 5) Verificar conteos pre-switch
ssh root@94.72.115.156 "mysql -N -e \"
  SELECT 'os_integracion', (SELECT COUNT(*) FROM os_integracion.zeffi_facturas_venta_encabezados);
  SELECT 'os_gestion',     (SELECT COUNT(*) FROM os_gestion.g_tareas);
\""

# 6) SWITCH: aplicar el .env del VPS
cp integracion_conexionesbd.env integracion_conexionesbd.env.prev   # respaldo
cp integracion_conexionesbd.vps.env integracion_conexionesbd.env

# 7) Arrancar servicios
sudo systemctl start ia-service.service
sudo systemctl start wa-bridge.service
sudo systemctl start os-ia-admin.service
sudo systemctl start os-erp-frontend.service
sudo systemctl start os-gestion.service
sudo systemctl start os-inventario-api.service
sudo systemctl start os-telegram-bot.service
sudo systemctl start effi-pipeline.timer   # arrancarlo al final para que no dispare mientras todo se asienta

# 8) Tail logs 30 segundos
for s in os-gestion os-erp-frontend os-ia-admin wa-bridge ia-service os-inventario-api; do
  echo "=== $s ==="
  sudo journalctl -u $s -n 10 --no-pager
done
```

### 5.3 Smoke tests post-switch

1. **Login Gestión**: abrir `gestion.oscomunidad.com`, autenticar con Google, verificar que aparece la empresa.
2. **Crear tarea**: bottom sheet o QuickAdd, categoría, guardar. Confirmar que aparece en la lista.
3. **ERP Frontend**: abrir `menu.oscomunidad.com`, verificar módulo Ventas (resumen por mes, drill-down por cliente).
4. **Bot IA / Super Agente**: una consulta analítica (`¿Cuánto vendimos este mes?`).
5. **Pipeline manual**:
   ```bash
   python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/orquestador.py --forzar
   ```
   Debe terminar con `✅ ... tablas importadas`.
6. **Diagnóstico manual** (opcional):
   ```bash
   python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/diagnostico_diario.py
   ```

### 5.4 Post-validación (si todo OK por 48 h)

1. Revocar grants de escritura en Hostinger para evitar divergencia accidental:
   ```bash
   ssh -i ~/.ssh/sos_erp -p 65002 u768061575@109.106.250.195
   # En Hostinger — NO tengo permiso root de MySQL (solo del user).
   # Alternativa: bajar los privilegios del user via panel hPanel:
   #   - u768061575_osserver → solo SELECT en u768061575_os_integracion
   #   - u768061575_os_gestion → solo SELECT en u768061575_os_gestion
   ```
   Así quedan como lectura emergencia 7 días.
2. Al día 7 sin incidentes: desde panel Hostinger, eliminar las 2 BDs. `u768061575_os_comunidad` se queda intacta.
3. Actualizar docs: `.agent/CONTEXTO_ACTIVO.md`, `.agent/MEMORY.md`, `.agent/CATALOGO_TABLAS.md`, `.agent/docs/VPS_CONTABO.md`, `.agent/contextos/{sistema_gestion,pipeline_effi,ia_service,erp_frontend}.md`.
4. Commit final con bump de versión en MainLayout.vue.

---

## 6. Plan de rollback (si algo falla)

### 6.1 Detección

Síntomas que disparan rollback:
- Sistema Gestión no loguea (`SSH error` o `pool null` persistente en logs)
- ERP Frontend 500 en cualquier endpoint
- Pipeline falla con error de conexión
- Bot IA no responde
- Discrepancia de datos visible al usuario

### 6.2 Rollback inmediato (< 1 min)

```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS
cp integracion_conexionesbd.env.prev integracion_conexionesbd.env
sudo systemctl restart os-gestion os-erp-frontend os-ia-admin wa-bridge ia-service os-inventario-api os-telegram-bot
sudo systemctl start effi-pipeline.timer
```

Resultado: servicios vuelven a leer de Hostinger, igual que antes del corte. Nada se perdió.

### 6.3 Si hubo escrituras post-corte al VPS (situación rara)

Durante el corte el VPS recibió escrituras y Hostinger no. Tras rollback, hay que sincronizar Hostinger con los cambios del VPS:

```bash
# Dump del VPS post-corte
ssh root@94.72.115.156 "mysqldump --single-transaction os_integracion" | gzip > /tmp/os_integracion_vps.sql.gz
ssh root@94.72.115.156 "mysqldump --single-transaction os_gestion"     | gzip > /tmp/os_gestion_vps.sql.gz

# Import a Hostinger (vía SSH + mysql remoto)
zcat /tmp/os_integracion_vps.sql.gz \
  | ssh -i ~/.ssh/sos_erp -p 65002 u768061575@109.106.250.195 \
    "mysql -u u768061575_osserver -pEpist2487. u768061575_os_integracion"
```

Solo hacer esto si la ventana de corte duró >5 min y hubo actividad real. Si el corte fue <2 min, probablemente no hay divergencia y no se necesita.

---

## 7. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Tunnel SSH al VPS se cae durante uso normal | Baja | Helpers tienen `programarReconexion()` (Node) y abren tunnel al primer uso (Python). Reintento automático. |
| Puerto 3311/3312/3313 ocupado por otro proceso | Muy baja | El helper detecta `EADDRINUSE` y reusa el tunnel existente. Solo pasa si se corre tests paralelos. |
| Discrepancia de datos tras corte | Baja | Dump delta justo antes del switch + DROP/CREATE + re-import asegura BD idéntica a Hostinger en ese instante. |
| Falla SSH key a VPS | Media | Key ya autorizada (2026-04-20 16:48). Verificar antes de corte con `ssh osserver@94.72.115.156 echo OK`. |
| Timezone incorrecto en VPS | Muy baja | Ya aplicado `default-time-zone=-05:00`. `NOW()` devuelve hora Colombia. |
| Passwords débiles/expuestas | Baja | Mismo patrón actual (`Epist2487.`) para consistencia. Si Santi quiere cambiar: editar `integracion_conexionesbd.env` + `ALTER USER ... IDENTIFIED BY 'nuevo'` en VPS. |
| Conexión a `os_comunidad` (Hostinger) falla post-corte | Baja | `DB_COMUNIDAD_*` no cambia en el `.env`. Sigue el mismo tunnel a Hostinger que hoy. |

---

## 8. Archivos y recursos clave

| Recurso | Ruta |
|---|---|
| `.env` activo (Hostinger) | `integracion_conexionesbd.env` |
| `.env` borrador del corte (VPS) | `integracion_conexionesbd.vps.env` |
| Helper Node | `lib/db_conn.js` |
| Helper Python | `scripts/lib/db_conn.py` |
| Dumps iniciales | `/home/osserver/Proyectos_Antigravity/backups/u768061575_os_{integracion,gestion}/2026-04-20_164537.sql.gz` |
| Plan anterior (centralización .env) | `.agent/planes/completados/migracion_bd_env_centralizado_2026-04-20.md` |
| Doc VPS Contabo | `.agent/docs/VPS_CONTABO.md` |

---

## 9. Checklist pre-corte (revisión antes de ejecutar)

- [ ] `ssh osserver@94.72.115.156 echo OK` responde
- [ ] `integracion_conexionesbd.vps.env` contiene exactamente lo que debería
- [ ] Backup inicial existe: `ls -lh /home/osserver/Proyectos_Antigravity/backups/u768061575_os_*/`
- [ ] Los 7 servicios están `active` antes del corte (baseline)
- [ ] Pipeline no está corriendo (`systemctl status effi-pipeline.service` → inactive)
- [ ] Santi dio la orden explícita

## 10. Checklist post-corte

- [ ] Los 7 servicios vuelven a `active` sin errores en 30s de logs
- [ ] Golden path funciona: login Gestión + crear tarea + abrir ERP + consultar bot
- [ ] `python3 scripts/orquestador.py --forzar` termina OK
- [ ] Monitor 48 h: `logs/pipeline.log`, `logs/telegram_bot.log`, `logs/diagnostico.log` sin errores nuevos
- [ ] Revocar grants en Hostinger (readonly)
- [ ] Actualizar docs (ver sección 5.4 #3)
- [ ] Commit + push
- [ ] Mover este plan a `.agent/planes/completados/migracion_bd_hostinger_a_vps_contabo_YYYY-MM-DD.md`
