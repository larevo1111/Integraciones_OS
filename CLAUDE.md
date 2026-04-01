# Integraciones_OS — Instrucciones para Claude

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
5. Skills disponibles: `/effi-database`, `/effi-negocio`, `/playwright-effi`, `/telegram-pipeline`

## ⚠️ REGLA ABSOLUTA — TIMEZONE

**Todo el sistema opera en hora Colombia (UTC-5). NUNCA usar patrones UTC para obtener fechas.**

Patrones **PROHIBIDOS**:
- `new Date().toISOString().slice(0, 10)` — devuelve fecha UTC (después de 7pm COL = día siguiente)
- `CURDATE()` en queries a Hostinger — MySQL Hostinger = UTC puro
- `NOW()` en queries a Hostinger para comparar fechas

Patrones **CORRECTOS**:
- **Frontend JS**: `import { hoyLocal } from 'src/services/fecha'` → `hoyLocal()`
- **Backend Node (server.js)**: `localDateCO()` (ya definida, usa `timeZone: 'America/Bogota'`)
- **Python**: `date.today()` (server local = Colombia)
- **SQL timestamps**: `UTC_TIMESTAMP()` para registrar momentos (se almacenan en UTC)

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
