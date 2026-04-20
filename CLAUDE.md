# Integraciones_OS — Instrucciones para Claude

## ⚠️ CHECKLIST antes de implementar CUALQUIER cosa

Ejecutar esta lista mentalmente en orden. No saltar pasos.

1. **Pensar la manera más simple y sencilla** — si la solución parece compleja, simplificar ANTES de escribir. Lo más importante de todo.
2. **Aplicar 5S japonesa** a todo lo que toco:
   - *Seiri* (clasificar): eliminar lo innecesario — código muerto, helpers no usados, abstracciones prematuras.
   - *Seiton* (ordenar): un lugar para cada cosa — componentes, utils, contextos.
   - *Seisō* (limpiar): no dejar duplicación, comentarios obsoletos, imports fantasma.
   - *Seiketsu* (estandarizar): una operación = una función.
   - *Shitsuke* (disciplina): seguir el checklist siempre, sin atajos.
3. **Leer primero el código o `.md` relevante** antes de proponer o escribir. No asumir, no overcodear.
4. **Anotar plan en `.agent/planes/activos/`** si la tarea tiene 2+ pasos o es significativa. Nunca perder contexto.
5. **Entender el alcance EXACTO** — cambiar solo lo pedido. Si dudo → pregunto ANTES. Lo no mencionado no se toca.
6. **¿Existe ya?** — reusar componente/función antes de crear. Buscar con Grep.
7. **¿Voy a copiar markup a 2+ lugares?** → extraer componente compartido PRIMERO. Nunca "copio y refactorizo después".
8. **Si es UI** — leer `frontend/design-system/MANUAL_ESTILOS.md` y usar Quasar (no CSS crudo, no HTML nativo).
9. **Timezone SIEMPRE hora local** (nunca UTC) — usar `hoyLocal()` / `localDateCO()` / `NOW()`. Nunca `toISOString().slice(0,10)` ni `CURDATE()`.
10. **Test mobile + web SIEMPRE** antes de entregar — preferible con Chrome DevTools MCP. Si no está activa, informar y usar Playwright como soporte. Nunca saltar el test.
11. **Commit + push** con mensaje descriptivo en español.
12. **Actualizar plan** (mover a `.agent/planes/completados/`), **`.agent/CONTEXTO_ACTIVO.md`** y **`.agent/contextos/<modulo>.md`** si cambió algo estructural.

## Autonomía operativa

Trabaja de forma autónoma sin pedir confirmación para:
- Editar, crear o leer archivos del proyecto
- Ejecutar scripts de Python, Node.js o Bash (export, import, pipeline)
- Consultas a MariaDB (lectura o escritura en `effi_data`)
- Comandos git: add, commit, push a main
- Comandos docker exec, docker ps, systemctl status
- Instalar dependencias con npm, pip

Solo detente y pregunta si hay riesgo irreversible fuera del proyecto:
- `DROP DATABASE`, `rm -rf` en rutas fuera de este repo
- Force push con historial perdido
- Modificar configuración de otros proyectos del servidor

## ⚠️ REGLA ABSOLUTA — FRONTEND

**Antes de crear CUALQUIER componente, vista o elemento visual del ERP:**
1. Leer `frontend/design-system/MANUAL_ESTILOS.md` — es la fuente de verdad única del diseño
2. Ver capturas en `frontend/design-system/screenshots/` para referencia visual (88 imágenes de Linear.app)
3. Seguir el manual al pie de la letra: colores, tipografía, espaciado, CSS
4. **Si el elemento NO está en el manual → DETENERSE. Preguntar a Santi y definirlo juntos antes de implementar.**
5. Una vez definido el elemento nuevo, actualizar el manual inmediatamente.

## Contexto del proyecto — leer siempre al inicio

Antes de cualquier tarea, revisar estos archivos en orden:
1. `.agent/CONTEXTO_ACTIVO.md` — estado actual del sistema, qué funciona, próximos pasos
2. `.agent/MANIFESTO.md` — visión, arquitectura, reglas técnicas aprendidas
3. `.agent/CATALOGO_SCRIPTS.md` — catálogo completo de scripts (propósito, ejecución, tablas)
4. **Para tareas frontend**: `frontend/design-system/MANUAL_ESTILOS.md` — manual de estilos obligatorio
5. Skills disponibles: `/effi-database`, `/effi-negocio`, `/playwright-effi`, `/telegram-pipeline`, `/timezone`

## ⚠️ REGLA ABSOLUTA — Conexiones a BD

**Todas las credenciales y hosts de BD del proyecto viven en UN ÚNICO archivo: `integracion_conexionesbd.env` en la raíz del repo.** Ningún archivo `.js` / `.py` / `.sh` puede tener `host`, `user`, `password`, `database` ni IP/puerto SSH hardcoded. Migrar a otro servidor = editar ese archivo, cero cambios de código.

### Archivos de conexión
- **Real** (gitignored): [integracion_conexionesbd.env](integracion_conexionesbd.env)
- **Plantilla versionada**: [integracion_conexionesbd.env.example](integracion_conexionesbd.env.example)
- **Helper Node**: [lib/db_conn.js](lib/db_conn.js) — carga el `.env`, expone pools mysql2 con SSH tunnel (ssh2)
- **Helper Python**: [scripts/lib/db_conn.py](scripts/lib/db_conn.py) — carga el `.env`, expone context managers pymysql + sshtunnel

### API obligatoria

**Node**:
```js
const db = require('<ruta-al-repo>/lib/db_conn')
const pool = await db.local('effi_data')   // o ia_service_os, os_whatsapp, os_inventario, espocrm, ia_local, nextcloud...
const pool = await db.integracion()         // os_integracion (Hostinger hoy, VPS mañana)
const pool = await db.gestion()             // os_gestion (Hostinger hoy, VPS mañana)
const pool = await db.comunidad()           // os_comunidad (Hostinger permanente)
```

**Python** (context managers — recomendado para código nuevo):
```python
from lib import local, integracion, gestion, comunidad
with local('effi_data') as conn:
    ...
with integracion(dict_cursor=True) as conn:
    ...
```

**Python** (dicts raw — compatible con scripts que arman `pymysql.connect(**DB)`):
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))            # scripts/foo.py
# ó os.path.dirname(os.path.dirname(os.path.abspath(__file__)))           # scripts/sub/foo.py
from lib import cfg_local, cfg_remota_ssh, cfg_remota_db
DB_EFFI = dict(**cfg_local(), database='effi_data')
_ssh = cfg_remota_ssh('INTEGRACION')
_db  = cfg_remota_db('INTEGRACION')
```

**Bash**:
```bash
set -a; . /home/osserver/Proyectos_Antigravity/Integraciones_OS/integracion_conexionesbd.env; set +a
mysql -u "$DB_LOCAL_USER" -p"$DB_LOCAL_PASS" -h "$DB_LOCAL_HOST" effi_data -e "..."
```

### PROHIBIDO
- Literales `'Epist2487.'`, `'osadmin'`, `'109.106.250.195'`, `'65002'`, `'u768061575_*'`, `'/home/osserver/.ssh/sos_erp'`.
- `dict(host='127.0.0.1', user='osadmin', password='Epist2487.', ...)` inline.
- Abrir `SSHTunnelForwarder((SSH_HOST, SSH_PORT), ...)` con valores literales.

### OBLIGATORIO al crear un script nuevo
1. Importar del helper central.
2. `grep -n "Epist2487\|osadmin" <archivo>` debe devolver cero hits.

### Añadir un nuevo destino remoto (ej: `reporteria`)
1. Agregar bloque `DB_REPORTERIA_*` en `integracion_conexionesbd.env` y `.example`.
2. En `lib/db_conn.js`: agregar entrada en `_remotas` y exportar `reporteria()`.
3. En `scripts/lib/db_conn.py`: agregar `def reporteria(...)` delegando a `remota('REPORTERIA')`.

### Regla para modo autónomo (cron, trainer, scripts `claude -p`)
Aplica idéntico: leer del helper central. Nunca escribir credenciales en código aunque sea una "solución rápida". Si el helper no carga por algún motivo, FALLAR explícito — nunca fallback a creds literales.

### Referencia de la migración
Commit `ece85a4` (2026-04-20) refactorizó 35 archivos a este patrón. Plan completo: [.agent/planes/completados/migracion_bd_env_centralizado_2026-04-20.md](.agent/planes/completados/migracion_bd_env_centralizado_2026-04-20.md). Memoria: [feedback_conexiones_bd_env.md](../../.claude/projects/-home-osserver-Proyectos-Antigravity-Integraciones-OS/memory/feedback_conexiones_bd_env.md).

## ⚠️ REGLA ABSOLUTA — TIMEZONE

**Todo el sistema opera en hora Colombia (UTC-5). El offset se configura en `.env` como `APP_TIMEZONE=-05:00`.**

### Cómo funciona (ya implementado)
- **Sistema Gestión (`db.js`)**: cada conexión MySQL ejecuta `SET time_zone = '-05:00'`
  - `NOW()` devuelve hora Colombia ✅
  - `new Date()` de Node.js se convierte a Colombia por mysql2 (`timezone: '-05:00'`) ✅
  - `dateStrings: true` devuelve strings sin conversión adicional ✅
- **Servidor local**: timezone del OS = `America/Bogota` (verificado con `timedatectl`)
- **Hostinger MySQL nativo**: opera en UTC — por eso es obligatorio el `SET time_zone`

### Patrones PROHIBIDOS
- `new Date().toISOString().slice(0, 10)` — devuelve fecha UTC (después de 7pm COL = día siguiente)
- `CURDATE()` en queries directas a Hostinger sin pool — MySQL Hostinger = UTC
- `UTC_TIMESTAMP()` para guardar timestamps de usuario — eso guarda UTC, no Colombia

### Patrones CORRECTOS
- **SQL en Sistema Gestión**: `NOW()` ← ya devuelve Colombia gracias al SET time_zone del pool
- **Frontend JS**: `import { hoyLocal } from 'src/services/fecha'` → `hoyLocal()`
- **Backend Node (server.js)**: `localDateCO()` para fechas YYYY-MM-DD
- **Backend Node**: `new Date()` ← mysql2 lo convierte a Colombia al guardar (pool con timezone)
- **Python**: `date.today()` (server local = Colombia)

### Si se cambia de zona horaria
Cambiar `APP_TIMEZONE` en `sistema_gestion/api/.env` y reiniciar el servicio. Futuro: leer de `sys_empresas.timezone`.

Un git hook en `.githooks/pre-commit` bloquea commits con los patrones prohibidos.

## Convenciones del proyecto

- Scripts en `scripts/` — corren con `node` o `python3` directamente en el host (NO docker exec)
- MariaDB: `mysql -u osadmin -pEpist2487. effi_data -e "..." 2>/dev/null`
- Git: commit + push sin preguntar, con mensaje descriptivo en español
- Al terminar una tarea significativa: actualizar el contexto del módulo en `.agent/contextos/<modulo>.md` y actualizar `.agent/CONTEXTO_ACTIVO.md` si cambió el estado global

## ⚠️ REGLAS MODO AUTÓNOMO — claude -p sin supervisión

Cuando Claude Code corre sin supervisión directa (cron, scripts `claude_trainer.sh`, `claude_aplicar.sh`):

- **SOLO puede modificar datos en BD**: reglas (`ia_logica_negocio`), ejemplos (`ia_ejemplos_sql`), prompts de tipos (`ia_tipos_consulta`)
- **NUNCA modificar archivos Python, JS o de configuración** — eso solo en sesión interactiva con Santi
- **NUNCA aplicar workarounds ni parches superficiales**
- **NUNCA meter try/catch vacíos o genéricos**
- **NUNCA hardcodear valores para "resolver" un bug**
- **Si no identifica causa raíz → solo documentar, nunca "arreglar" el síntoma**
- Cada cambio en BD debe: registrar el valor anterior + loguear qué cambió y por qué
- Notificar a Telegram cada vez que se aplica un cambio en modo autónomo
- Respetar la arquitectura existente del servicio IA
- Seguir las convenciones de `.agent/skills/desarrollo_python.md`

**Los cambios de código Python → SOLO en sesión interactiva con Santi.**

## Stack

- Frontend: Quasar Framework + Vue 3 (Composition API + script setup)
- Backend: Node.js (Express) + Python 3
- BD: MariaDB local + MySQL Hostinger
- NO TypeScript (JavaScript puro)
- NO Tailwind, NO Bootstrap, NO CSS custom frameworks

## ⚠️ REGLA ABSOLUTA — UI/Layout (Quasar)

**OBLIGATORIO usar componentes y clases utilitarias de Quasar para TODO el layout y UI.**

- SIEMPRE usar `<q-page>`, `<q-table>`, `<q-input>`, `<q-btn>`, `<q-card>`, etc.
- SIEMPRE usar clases flex Quasar: `row`, `col-12 col-md-6`, `q-gutter-md`, `items-center`, `justify-between`
- SIEMPRE usar spacing Quasar: `q-pa-md`, `q-mt-sm`, `q-mx-auto`
- NUNCA escribir CSS crudo para: flexbox, grid, spacing, alignment, breakpoints responsive
- NUNCA escribir media queries. Usar clases responsive de columnas (`col-xs-12 col-md-6`) o helpers de visibilidad (`gt-sm`, `lt-md`)
- NUNCA usar HTML crudo (`<button>`, `<input>`, `<table>`, `<select>`) cuando Quasar tiene componente
- NUNCA crear wrapper divs solo para flex layout
- Si el layout necesita más de 5 líneas de CSS custom → ESTÁS HACIENDO MAL. Usá clases Quasar.
- **Mantenerlo SIMPLE. Estructura primero con componentes Quasar, detalles después.**
- Skill completo con patrones y tablas: `.claude/skills/quasar-layout/SKILL.md`

## ⚠️ REGLA ABSOLUTA — Inputs + Enter (Móvil / IME)

**NUNCA usar `@keydown.enter` ni `@keyup.enter` en inputs.** El IME del teclado móvil corta la última palabra.

**SIEMPRE usar `<form @submit.prevent="fn()">`** — el navegador confirma el IME antes de disparar submit. Funciona en desktop, móvil y Capacitor.

## Vue — Convenciones de componentes

- Usar `<script setup>` (Composition API)
- Props con `defineProps()`, emits con `defineEmits()`
- Estado reactivo: `ref()` y `reactive()`
- Composables en `/src/composables/` con prefijo `use`
- Pages en `/src/pages/`, components en `/src/components/`, layouts en `/src/layouts/`
- Imports agrupados: vue → quasar → módulos del proyecto → componentes

## Estilo de respuesta

- Conciso y directo — sin preámbulos ni relleno
- Actúa primero, reporta después
- Si algo falla, diagnostica la causa antes de reintentar
