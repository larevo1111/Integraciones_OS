# Plan — Centralización de conexiones BD en `.env` único + Migración a VPS

**Creado**: 2026-04-20
**Responsable**: Claude Code
**Prerequisito migración VPS**: abrir TCP 22 en panel Contabo (pendiente Santi)

## Objetivo

Toda conexión a BD (local o remota) del proyecto debe leer sus credenciales desde **un único archivo**: `integracion_conexionesbd.env` en la raíz. Ningún `.js` ni `.py` puede contener host/user/password/database hardcoded.

**Beneficio**: migrar `os_integracion` y `os_gestion` de Hostinger al VPS Contabo (y cualquier futura migración) se reduce a editar ese único archivo.

## Archivo central

Ruta: `integracion_conexionesbd.env` (raíz del repo, gitignored).
Plantilla dummy versionada: `integracion_conexionesbd.env.example`.

### Bloques de variables

- `DB_LOCAL_*` — MariaDB local del servidor (usuario admin para todas las BDs locales)
- `DB_INTEGRACION_*` — BD `os_integracion` (hoy Hostinger, mañana VPS)
- `DB_GESTION_*` — BD `os_gestion` (hoy Hostinger, mañana VPS)
- `DB_COMUNIDAD_*` — BD `os_comunidad` (se queda en Hostinger)

Cada bloque remoto incluye `*_SSH_HOST`, `*_SSH_PORT`, `*_SSH_USER`, `*_SSH_KEY`, `*_USER`, `*_PASS`, `*_NAME`.

## Helpers compartidos

1. `lib/db_conn.js` (Node) — expone `conectarLocal(nombreBD)`, `conectarIntegracion()`, `conectarGestion()`, `conectarComunidad()`. Cada función maneja su propio túnel SSH (si aplica) y devuelve pool mysql2.
2. `scripts/lib/db_conn.py` (Python) — expone funciones equivalentes con context managers (`with local('effi_data') as conn:`).

Ambos cargan el `.env` central buscando en la raíz del repo.

## Archivos a refactorizar (35)

### Node (5)
- `sistema_gestion/api/db.js` — usa 3 pools (comunidad, gestion, integracion)
- `frontend/api/db.js` — usa integracion
- `ia-admin/api/server.js` líneas 113-116 — usa ia_service_os (local)
- `ialocal/server.js` líneas 41-48 — usa ia_local (local)
- `wa_bridge/index.js` líneas 35-41 — usa os_whatsapp (local)

### Python — IA Service (2)
- `scripts/ia_service/config.py` — ia_service_os local + integracion Hostinger (ya usa dotenv parcial)
- `scripts/telegram_bot/db.py` — wrapper de config.py (1 línea de cambio)

### Python — Pipeline Effi y resúmenes (10)
- `scripts/calcular_resumen_ventas.py`
- `scripts/calcular_resumen_ventas_canal.py`
- `scripts/calcular_resumen_ventas_cliente.py`
- `scripts/calcular_resumen_ventas_producto.py`
- `scripts/calcular_resumen_ventas_remisiones_mes.py`
- `scripts/calcular_resumen_ventas_remisiones_canal_mes.py`
- `scripts/calcular_resumen_ventas_remisiones_cliente_mes.py`
- `scripts/calcular_resumen_ventas_remisiones_producto_mes.py`
- `scripts/sync_catalogo_articulos.py`
- `scripts/asignar_grupo_producto.py`

### Python — Sync cross-servidor (5)
- `scripts/sync_hostinger.py` — effi_data → integracion
- `scripts/sync_espocrm_to_hostinger.py` — espocrm → integracion
- `scripts/sync_inventario_catalogo.py` — effi_data → integracion
- `scripts/sync_espocrm_contactos.py` — espocrm local
- `scripts/sync_espocrm_marketing.py` — espocrm local

### Python — Notificaciones / cron (4)
- `scripts/notif_jornadas_abiertas.py` — gestion + comunidad
- `scripts/notif_jornada_no_iniciada.py` — gestion + comunidad
- `scripts/importar_tareas_nextcloud.py` — nextcloud local + gestion Hostinger
- `scripts/diagnostico_diario.py`

### Python — Utilidades (4)
- `scripts/checks_sistema.py` — ia_service_os local
- `scripts/benchmark_agentes.py` — ia_service_os local
- `scripts/generar_plantilla_import_effi.py` — espocrm local
- `scripts/clasificar_contactos.py` — espocrm local
- `scripts/bootstrap_ciudades_espocrm.py` — espocrm local

### Python — Inventario (6)
- `scripts/inventario/api.py` — os_inventario + effi_data
- `scripts/inventario/generar_informe.py` — os_inventario
- `scripts/inventario/depurar_inventario.py` — effi_data + os_inventario
- `scripts/inventario/calcular_inventario_teorico.py` — effi_data + os_inventario
- `scripts/inventario/calcular_rangos.py` — effi_data + os_inventario
- `scripts/inventario/analisis_inconsistencias.py` — effi_data + os_inventario

## Orden de ejecución (fases)

### Fase A — Artefactos base (SIN refactor)
1. Crear `integracion_conexionesbd.env` con creds actuales (todo apuntando a Hostinger + local)
2. Crear `integracion_conexionesbd.env.example` con valores dummy
3. Agregar línea al `.gitignore`
4. Crear `lib/db_conn.js`
5. Crear `scripts/lib/db_conn.py`
6. Probar helpers con un script de smoke test

### Fase B — Refactor Node (5 módulos)
Cada uno: edit → reiniciar servicio → verificar con `curl` o login.

### Fase C — Refactor Python (30 archivos)
En grupos lógicos. Al final de cada grupo: ejecutar 1 script representativo en dry-run o forzado.

### Fase D — Validación integral
- Reiniciar todos los servicios
- Correr pipeline manual: `python3 scripts/orquestador.py --forzar`
- Login Gestión + crear tarea
- Abrir ERP Frontend
- Consulta al bot IA
- Tail logs 5 minutos sin errores nuevos

### Fase E — Commit + push + docs
- Commit único con bump de versión en MainLayout.vue
- Actualizar `.agent/CONTEXTO_ACTIVO.md`, `.agent/contextos/*.md`, `MEMORY.md`

### Fase F — (FUTURO, cuando Santi dé orden) Migración VPS
1. Abrir TCP 22 en Contabo
2. Crear BDs `os_integracion` y `os_gestion` en MariaDB VPS, usuarios, timezone nativo `-05:00`
3. Dump Hostinger → import VPS
4. Verificar `CHECKSUM TABLE` por cada tabla
5. Ventana de corte: stop servicios → sync delta final → editar `integracion_conexionesbd.env` → start servicios
6. Validar golden paths
7. Revocar GRANT en Hostinger para integracion/gestion (comunidad intacto)
8. Dejar Hostinger como backup 7 días

## Rollback

En cualquier momento: `git revert <commit>` del refactor o `cp integracion_conexionesbd.env.prev integracion_conexionesbd.env` + restart. Rollback real en <1 min.

## Riesgos conocidos

- **Auto-tunnel SSH**: si se cae el enlace al VPS/Hostinger, los helpers deben reconectar. El patrón actual de `sistema_gestion/api/db.js` (SSH2 con reconect) se mantiene.
- **Dos tuneles simultáneos**: tras migrar, los scripts de notificaciones y `sistema_gestion/api/db.js` abren dos túneles (VPS + Hostinger). Testear que el helper maneja esto sin colisión de puertos locales (usar puertos distintos por destino).
- **Pipeline corriendo durante refactor**: refactorizar en horario no-operativo o hacer freeze de timer.
