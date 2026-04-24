# MANIFESTO — Integraciones_OS

> **Este es el documento constitución del proyecto.** Contiene reglas que aplican globalmente y cambian poco.
> Para el estado actual del sistema → `CONTEXTO_ACTIVO.md`
> Para orientación general y mapa del repo → `MEMORY.md` (memoria Claude)
> Para saber cómo mantener la documentación → `MANUAL_DOCUMENTACION.md`

## Índice de secciones

- [Reglas críticas de frontend](#reglas-críticas-de-frontend)
- [1. Roles, delegación y equipo](#1-roles-delegación-y-equipo)
- [2. Filosofía del sistema IA](#2-filosofía-del-sistema-ia--principio-fundamental)
- [3. Memoria externa, documentación y contextos](#3-memoria-externa-documentación-y-contextos)
- [4. Tono y comunicación](#4-tono-y-comunicación)
- [5. Autonomía de ejecución](#5-autonomía-de-ejecución--dos-fases)
- [5B. Filosofía 5S japonesa](#5b-filosofía-5s-japonesa--simplicidad-al-máximo)
- [7. Flujo de trabajo obligatorio](#7-flujo-de-trabajo-obligatorio)
- [8. Regla transversal de entornos](#8-regla-transversal-de-entornos)
- [8B. Conexiones a BD — centralización obligatoria](#8b-conexiones-a-bd--centralización-obligatoria)
- [9. Contexto y estructura del proyecto](#9-contexto-y-estructura-del-proyecto)
- [10. Reglas técnicas aprendidas](#10-reglas-técnicas-aprendidas)
- [12. Manual de estilos frontend](#12-manual-de-estilos--frontend-erp)
- [13. Estándar de navegación drill-down](#13-estándar-de-navegación-drill-down--erp)
- [14. Diccionario de negocio](#14-diccionario-de-negocio)
- [15. Gestión de screenshots](#15-gestión-de-screenshots-temporales-y-ui)
- [17. Protocolo de QA y testing](#17-protocolo-de-qa-y-testing)
- [19. Super Agente Claude Code](#19-super-agente-claude-code--modo-paralelo-en-el-bot-de-telegram)
- [20. Reglas de documentación](#20-reglas-de-documentación)

---

## ⚠️ REGLAS CRÍTICAS DE FRONTEND (leer antes de cualquier tarea de UI)

### Referentes UX obligatorios

Toda decisión de UI/UX debe basarse en estos referentes, en este orden:

1. **Nielsen Norman Group** (nngroup.com) — reglas de usabilidad, navegación, patrones
2. **Linear.app** — referente principal de diseño (sidebar, paneles, tareas, dark mode)
3. **HubSpot / Kommo** — referente de sidebar colapsada (submenu flotante, no acordeón)

**Principio:** cuando hay duda sobre cómo hacer algo en la UI, buscar cómo lo hace Linear primero. Si Linear no aplica, buscar en Nielsen Norman Group.

### Antes de crear cualquier componente visual:

1. **Leer el manual**: `frontend/design-system/MANUAL_ESTILOS.md`
2. **Consultar capturas de referencia**: `frontend/design-system/screenshots/` (88 imágenes de Linear.app) + `INDEX.md`
3. **Seguir el manual al pie de la letra**: colores, tipografía, espaciado, componentes — todo definido ahí.
4. **Si el elemento NO está en el manual**: DETENERSE. Preguntar a Santi y definir juntos antes de implementar. Luego actualizar el manual.

### ⚠️ TABLA OFICIAL DEL PROYECTO: OsDataTable

**`OsDataTable.vue` es LA ÚNICA tabla del proyecto. Tanto ERP como Sistema Gestión la usan.**

- **Ruta canónica**: `frontend/app/src/components/OsDataTable.vue`
- **Copia en Sistema Gestión**: `sistema_gestion/app/src/components/OsDataTable.vue`
- **Documentación**: `.claude/skills/tabla-vista/SKILL.md`

**Features built-in** (NO reimplementar ninguna, TODAS siempre visibles):
- Título de la tabla + badge de conteo
- Badges de filtros y subtotales activos
- **Botón "Campos"** — SIEMPRE visible (mostrar/ocultar columnas)
- **Botón "Exportar"** — SIEMPRE visible (CSV / Excel / PDF). Si no hay `recurso` backend, exporta client-side
- Filtros por columna (popup, NO modal): Igual a, Contiene, Mayor que, Menor que, Mayor/menor o igual, Entre
- Subtotales por columna: Suma, Promedio, Máximo, Mínimo (solo numéricas)
- Ordenamiento por columna (asc/desc)
- Skeleton loading
- Footer con total de filas
- Formato automático: `_min`/`_seg` → "Xh Ym", `fin_`/`ventas`/`ticket` → "$1.234", `_pct`/`_margen` → "45%"

**TODOS los elementos del toolbar son SIEMPRE visibles sin excepción.** Está prohibido usar props tipo `exportable`, `hideExport`, `showFields: false` o cualquier mecanismo que oculte funcionalidad del toolbar.

**Uso**:
```vue
<OsDataTable
  title="Resumen por mes"
  :rows="datos"
  :columns="[{ key: 'mes', label: 'Mes', visible: true }, ...]"
  :loading="cargando"
/>
```

**PROHIBIDO**:
- Crear componentes tabla nuevos (`MiTabla.vue`, `CustomTable.vue`, `GestionTable.vue`, etc.)
- Usar `<q-table>` cuando aplicaría OsDataTable
- Duplicar lógica de filtros/ordenamiento/subtotales en componentes locales
- Modificar solo la copia local en vez del canónico (si es una mejora, va al original primero)
- **Ocultar botón Exportar o Campos con props, v-if, o cualquier otra forma**
- Pasar props tipo `exportable=false`, `hideExport`, etc. — no existen, todos los elementos son obligatorios

**⚠️ VERIFICACIÓN OBLIGATORIA ANTES DE MARCAR CUALQUIER TAREA FRONTEND COMO LISTA:**
1. Verificar que TODAS las variables CSS usadas existen en `frontend/app/src/css/app.scss` — si no existen, agregarlas o usar variable equivalente
2. Verificar que el endpoint API devuelve los datos correctos con `curl` o query directa
3. Hacer el build y confirmar que compila sin errores
4. **Verificar visualmente con Chrome DevTools MCP** (navegar a la URL real y tomar screenshot)
5. NO declarar una tarea como completada sin haber verificado los puntos anteriores

### Verificación visual rápida con Chrome DevTools MCP

Para autenticarse en `gestion.oscomunidad.com` / `ia.oscomunidad.com` sin OAuth:

1. Generar JWT: `scripts/gen_jwt_dev.sh` (token válido 7 días para SYSOP / empresa OS)
2. Inyectar en localStorage con `mcp__chrome-devtools__evaluate_script`
3. Navegar a la ruta: `mcp__chrome-devtools__navigate_page`
4. Verificar: `mcp__chrome-devtools__take_screenshot` o `take_snapshot`

Ver detalle completo en `memory/feedback_chrome_devtools_jwt.md`. Esto reemplaza los scripts de Playwright para verificación interactiva. Playwright queda solo para tests automatizados sin supervisión.

**⚠️ BUILD OBLIGATORIO:** Después de cualquier modificación Vue/Quasar, los fuentes NO se sirven directamente. El servidor sirve `dist/spa/` compilado. Sin rebuild = cambios invisibles en producción.

### Cómo hacer el build correctamente

**IMPORTANTE: El build corre en el HOST, NO en Docker. Nunca usar `docker exec`.**

**App ERP (`menu.oscomunidad.com`):**
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/frontend/app
npx quasar build
# Output: frontend/app/dist/spa/
```

**App IA Admin (`ia.oscomunidad.com`):**
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/ia-admin/app
npx quasar build
# Output: ia-admin/app/dist/spa/
```

**Reglas del build:**
1. Esperar a que termine completamente — puede tardar 30–60 segundos. No interrumpir.
2. El build es exitoso cuando aparece `Output folder...` al final, sin errores en rojo.
3. Si hay errores de TypeScript/lint, corregirlos antes de continuar — un build con errores NO actualiza `dist/`.
4. No es necesario reiniciar ningún servidor después del build (Node/Express sirve los archivos estáticos directamente desde `dist/spa/`).
5. No usar `npm run build` — usar siempre `npx quasar build` (es la forma correcta para Quasar).
6. Si el build se cuelga sin output por más de 2 minutos: `Ctrl+C`, luego `rm -rf node_modules/.vite` y volver a intentar.

**Verificar que el build aplicó:**
- Abrir la URL en el browser
- Hard refresh: `Ctrl+Shift+R` (o `Cmd+Shift+R` en Mac) para limpiar caché
- Revisar DevTools → Console para errores JS

---

## 1. ROLES, DELEGACIÓN Y EQUIPO

### 1.1 Jerarquía de roles

**Santi (Santiago)** — Director Estratégico y Dueño.
Su visión es el norte y su aprobación es la ÚNICA llave para ejecutar cambios en producción o estructura. Santi NO codea — dirige, decide y orquesta agentes.

**Claude Code** — Arquitecto Senior + Constructor Principal + Operador de Infraestructura.
Es el cerebro técnico del proyecto. Diseña la estructura de módulos, planifica cambios cross-file, ejecuta refactors profundos, accede a MySQL y servidores por terminal directo. Toma decisiones de arquitectura del ERP. Recibe el **70% del trabajo pesado**: diseño, implementación compleja, consultas de DB, debugging profundo y análisis de arquitectura.

**Antigravity (Google Labs)** — Constructor Secundario Ocasional.
Plataforma agentic de Google Labs (lanzada Nov 2025). IDE agent-first basado en Gemini 3.1 Pro con **contexto de 1 millón de tokens**. **Su uso es ocasional y por demanda explícita de Santi** — cuando el contexto necesario supera ampliamente lo que cabe en Claude Code. Claude Code ya puede navegar la web, leer codebase completo con subagentes, y hacer QA funcional — Antigravity **no es necesario para esas tareas**. Ver perfil completo: `.agent/docs/ANTIGRAVITY_GOOGLE_LABS.md`.

**Subagentes Claude** — Ejecutores Paralelos de Claude Code.
Instancias de Claude lanzadas por Claude Code con la herramienta `Agent`. Mismas capacidades que Claude Code (Bash, Playwright, Read, Write, DB) pero corren en paralelo sin consumir tokens del contexto principal. Recibe el **máximo posible de trabajo secundario**: construcción de módulos, QA, exploración de codebase, diagnósticos de BD, documentación. **Regla: si una tarea no requiere razonamiento arquitectónico profundo → va al subagente.** NO confundir con Antigravity Google Labs — son conceptos distintos.

> ⚠️ **REGLA ANTI-CONFUSIÓN**: Cuando este documento (o cualquier conversación) mencione "Antigravity" sin calificador, se refiere a **Antigravity de Google Labs** (el agente externo). Los subagentes de Claude se llaman "subagentes Claude" o "subagente".

### 1.2 Asignación de tareas

| Tipo de tarea | Asignar a | Motivo |
|---|---|---|
| Diseño de arquitectura / estructura de módulos | Claude Code | Razonamiento profundo, visión cross-file |
| Implementación de features completas | Claude Code | Multi-archivo, PR-ready |
| Consultas MySQL / acceso a servidores | Claude Code | Terminal directo, sin intermediarios |
| Refactors complejos cross-module | Claude Code | Planificación + ejecución coordinada |
| Revisión de arquitectura con contexto masivo (>200K tokens) | Antigravity Google Labs | Solo si el contexto supera lo que Claude Code puede procesar con subagentes |
| QA visual / browser testing | Subagente Claude | Playwright, screenshots, verificación funcional |
| Exploración de repos grandes | Subagente Claude o Claude Code | Subagentes corren en paralelo sin bloquear |
| Construcción secundaria (módulos, CRUD) | Subagente Claude | Paralelo, sin consumir contexto principal |
| Tareas paralelas simultáneas | Subagente Claude | Multi-agente sin bloquear la conversación |
| QA funcional (endpoints, BD, logs) | Subagente Claude | Ejecución autónoma de checks |

### 1.3 Qué retiene Claude Code (nunca delegar)

- Diseño arquitectural y decisiones técnicas críticas
- Features con lógica de negocio compleja
- Coordinación entre múltiples partes del sistema
- Decisiones que necesitan aprobación de Santi
- Tareas que requieren contexto acumulado de la conversación

### 1.4 Qué puede hacer Antigravity (ocasional, por demanda)

Solo cuando el contexto supera lo que Claude Code puede procesar con subagentes (>200K tokens):
- Segunda opinión arquitectural con el codebase completo
- Análisis masivo de logs o datos históricos que no caben en contexto normal

Todo lo demás (QA, exploración, construcción secundaria) → **Subagentes Claude**.

### 1.5 Protocolo de delegación

Antes de hacer cualquier exploración, búsqueda o tarea secundaria directamente:
1. **¿Puedo delegarlo?** → Si toma >3 lecturas de archivo o >3 comandos bash → **delegarlo**.
2. **Lanzar con prompt detallado** — incluir todo el contexto: rutas, schemas, objetivo, formato de resultado esperado.
3. **En segundo plano si es posible** → `run_in_background: true` para no bloquear la conversación.
4. **Informar a Santi** qué se delegó y en qué directorio quedará el resultado.

### 1.6 Regla de los planes y delegación

Cada plan puede incluir una sección opcional de tareas delegables:
- **"Tareas para Subagentes Claude"** — trabajo secundario/paralelo que Claude Code puede delegar a instancias `Agent`
- **"Tareas para Antigravity"** — solo si el contexto del análisis supera lo que Claude Code puede procesar con subagentes (>200K tokens); no es obligatorio

### 1.7 Archivos de resultados de subagentes

- **QA/Testing:** `.agent/QA_REGISTRO.md` — registro vivo de bugs y checklists
- **Screenshots temporales:** `screenshots_temporales/<modulo>_<desc>_<timestamp>.png`
- **Diagnósticos:** `.agent/docs/DIAG_<tema>_<fecha>.md`
- **Reportes del entrenador IA:** `/tmp/reporte_mejoras_<fecha>.md`

---

## 2. FILOSOFÍA DEL SISTEMA IA — PRINCIPIO FUNDAMENTAL

> **Aplicable a ia_service_os, al bot de Telegram y a cualquier componente de IA del proyecto.**

### Enseñar a razonar, no a memorizar

**El objetivo es construir una IA que encuentre las respuestas de forma autónoma.**

Esto significa que NO hay que llenar el sistema de reglas específicas para cada pregunta posible. Si la IA falla en una consulta concreta y se le inyecta la respuesta correcta directamente en el prompt, la próxima vez la responderá bien — pero eso no es inteligencia: es memorización. El próximo usuario que haga la misma pregunta de otra forma volverá a fallar.

**No nos ganamos nada afinando el prompt para responder una pregunta específica que falló.** Lo que nos ganamos es mejorar el contexto general para que la IA razone mejor en todos los casos similares.

### Cuándo sí agregar reglas

Solo cuando representan información que el modelo NO puede inferir con el contexto disponible:
- Gotchas técnicos de la BD (ej: `id_cliente` en facturas tiene prefijo `'CC '`)
- Semántica no obvia de campos (ej: `precio_neto_total` INCLUYE IVA)
- Comportamientos contraintuitivos del negocio (ej: `vigencia='Vigente'` para consignación activa)

Estas cosas el modelo no puede deducirlas. Pero cómo calcular "ventas del lunes" sí puede razonarlo desde los patrones de fecha que ya tiene en el prompt.

### Cómo refinar correctamente

Cuando la IA falla en una consulta:
1. **Diagnosticar**: ¿Le falta contexto general? ¿O es un gotcha técnico que no puede inferir?
2. **Falta contexto general** → mejorar el system prompt con el principio, no el caso puntual
3. **Gotcha técnico** → sí agregar la regla, es legítimo
4. **Error de razonamiento** → agregar un ejemplo representativo en `ia_ejemplos_sql` que demuestre el patrón (no hardcodear la respuesta, sino el razonamiento)

### En la práctica

```
❌ MAL: La IA falló con "ventas del miércoles" → agregar en el prompt:
   "Si el usuario pregunta por el miércoles, usa DATE_SUB(CURDATE(), INTERVAL (WEEKDAY(CURDATE())-2) DAY)"

✅ BIEN: La IA falló con "ventas del miércoles" → revisar si los patrones de WEEKDAY
   ya están en <reglas_sql>. Si no están → agregar la REGLA GENERAL de días de la semana.
   No el caso del miércoles. Todos los días.

❌ MAL: La IA no supo qué tabla usar para consignación → agregar:
   "Cuando pregunten por consignación, usar zeffi_ordenes_venta_encabezados"

✅ BIEN: → verificar que la descripción de esa tabla en <tablas_disponibles> dice
   claramente "Usar para: consignación activa (filtrar vigencia='Vigente')". Si no lo dice → corregirlo.
```

---

## 3. MEMORIA EXTERNA, DOCUMENTACIÓN Y CONTEXTOS

**Principio:** No confiar en la memoria del chat. La verdad reside en los archivos del repositorio. Resolver sin documentar es resolver a medias.

### 3.1 Qué leer al iniciar sesión

**Leer SIEMPRE en este orden:**
1. `.agent/MANIFESTO.md` — Reglas globales, arquitectura vigente. Fuente de verdad #1.
2. `.agent/CONTEXTO_ACTIVO.md` — Estado actual del sistema y próximos pasos.
3. `.agent/CATALOGO_SCRIPTS.md` — Catálogo completo de scripts. Verificar si ya existe algo antes de crear.
4. `.agent/skills/` — Skills individuales: documentan CÓMO hacer algo que ya se aprendió.

**Para tareas frontend además:** `frontend/design-system/MANUAL_ESTILOS.md`

**Para CUALQUIER tarea que involucre código Python:**
- **OBLIGATORIO leer primero:** `.agent/skills/desarrollo_python.md` — límites de líneas, reglas de modularidad, checklist pre-commit. **Este manual existe porque `servicio.py` llegó a 1,756 líneas y requirió refactor mayor. No repetir.**

**Para tareas del Servicio IA (`scripts/ia_service/` o `scripts/telegram_bot/`):**
- Cargar skill `/ia-service` — contexto completo con BD, agentes, flujos, latencias, troubleshooting
- Manual detallado: `.agent/manuales/ia_service_manual.md` (24 secciones, v2.8)
- **Benchmark de agentes**: `.agent/docs/BENCHMARK_AGENTES.md` — tabla maestra de rendimiento (cloud + locales), config actual, hallazgos
- Detalle cloud (2026-03-20): `.agent/docs/COMPARACION_AGENTES_IA.md`
- Detalle Ollama (2026-03-29): `.agent/informes/benchmark_ollama_2026-03-29.md`

**Regla de conexiones a BD:**
Las instrucciones de conexión están documentadas como skills. Si no existe la skill, Claude Code puede explorar — pero tiene la **obligación de documentar lo aprendido como skill nueva** antes de dar la tarea por terminada. El conocimiento no queda en el chat: se institucionaliza.

### 3.2 Estructura de directorios .agent/

```
.agent/
├── MANIFESTO.md              ← Reglas globales, arquitectura, gotchas técnicos (este archivo)
├── CONTEXTO_ACTIVO.md        ← Índice de 1 página: módulos activos y qué se está haciendo
├── contextos/                ← Un archivo por módulo con su estado detallado
│   ├── ia_service.md         ← Servicio IA, bot Telegram, aprendizaje, agentes
│   ├── pipeline_effi.md      ← Pipeline Effi→MariaDB→Hostinger, 18 pasos
│   ├── erp_frontend.md       ← ERP Vue/Quasar, módulo Ventas, design system
│   ├── sistema_gestion.md    ← Módulo Tareas, auth, gestion.oscomunidad.com
│   └── espocrm.md            ← Integración bidireccional, campos custom
├── planes/
│   ├── actuales/             ← Planes en ejecución (PLAN_NOMBRE_YYYY-MM-DD.md)
│   └── completados/          ← Planes terminados (no se borran)
├── skills/                   ← Cómo hacer cosas específicas (por dominio)
├── manuales/                 ← Guías detalladas de referencia
└── docs/                     ← Informes, perfiles, documentación externa
```

**Por qué múltiples contextos:** El proyecto tiene varios módulos activos en paralelo con ciclos independientes. Al trabajar en un módulo no es necesario leer el estado de los demás.

### 3.3 Catálogo de archivos .agent/

- `.agent/MANIFESTO.md` — Visión, roles, reglas y aprendizajes técnicos. (este archivo)
- `.agent/CONTEXTO_ACTIVO.md` — Estado actual y próximos pasos.
- `.agent/CATALOGO_SCRIPTS.md` — Catálogo completo de scripts ejecutables (Python/JS). **Actualizar obligatoriamente al crear o modificar cualquier script.**
- `.agent/CATALOGO_AGENTES.md` — Catálogo de todos los agentes IA del ecosistema OS (cloud + locales Ollama). Incluye: modelo, proveedor, costo, capacidades, credenciales, notas. **Actualizar al agregar, modificar o desactivar cualquier agente.**
- `.agent/CATALOGO_APIS.md` — Catálogo de todas las APIs HTTP internas del ecosistema OS. Incluye: base URL, proceso systemd, BD, endpoints, ejemplos de llamada desde Python/JS. **Actualizar al crear o modificar cualquier endpoint de cualquier servicio.**
- `.agent/catalogo-skills.md` — Catálogo de conocimientos fundacionales. Índice de cómo se hacen las cosas.
- `.agent/CATALOGO_REFERENCIAS.md` — Fuentes externas e internas que informan decisiones técnicas y de IA. Incluye: guías de Anthropic/Google, papers de text-to-SQL, referencias de Antigravity, patrones de prompting, pendientes de investigar. **Actualizar al adoptar cualquier técnica externa o al encontrar una referencia relevante.**
- `.agent/skills/` — Skills individuales con conocimiento especializado.
- `.agent/planes/` — Especificaciones de construcción técnica para las features.
- `.agent/docs/` — Informes y documentación externa.
- `.agent/docs/MANUAL_EFFI_PRODUCCION_INVENTARIOS.md` — Manual completo de producción e inventarios en Effi. Tablas, campos, estados de OPs, trazabilidad, lógica de signos, relaciones entre tablas, reconstrucción de stock a fecha, ajuste por OPs generadas.
- `.agent/contextos/inventario_fisico.md` — Contexto del subproyecto de inventario físico vs teórico.
- `inventario/POLITICAS_ACCESO.md` — Políticas de acceso y seguridad del módulo de inventario.
- `inventario/politicas.json` — Config de permisos por acción y nivel de usuario.

#### Sistema de Inventario Físico (actualizado 2026-04-06)
App independiente para conteo de inventario. Separada de sistema_gestion.
- **Manual completo**: `.agent/manuales/inventario_fisico_manual.md` — **21 secciones, v2.0**
- **App**: `inv.oscomunidad.com` — Vue 3 + Vite frontend, FastAPI backend (puerto 9401)
- **BD**: `os_inventario` — 4 tablas: `inv_conteos`, `inv_rangos`, `inv_auditorias`, `inv_teorico`
- **Catálogo**: `inv_catalogo_articulos` (effi_data local + Hostinger) — artículos con unidad y grupo precalculados, sync cada 1h + botón Sync Effi
- **Scripts inventario**: `depurar_inventario.py`, `calcular_rangos.py`, `calcular_inventario_teorico.py`, `api.py`
- **Scripts sync/ajuste**: `sync_inventario_catalogo.py` (paso 6e pipeline), `import_ajuste_inventario.js` (Playwright, crea ajustes en Effi)
- **Auth**: Google OAuth, JWT compartido con sistema_gestion
- **Grupos**: MP, PP, PT, INS, DS, DES, NM — detectados automáticamente
- **Funcionalidades clave**: conteo físico, asignación artículos NM→Effi, sync catálogo, ajustes inventario Effi, validación unidades, auditoría completa
- **Systemd**: `os-inventario-api.service`, cloudflared `inv.oscomunidad.com`

### 3.4 Jerarquía de dónde registrar

| Dónde | Qué va ahí |
|---|---|
| **MANIFESTO.md** | Reglas generales, gotchas críticos de BD, decisiones arquitecturales permanentes |
| **Skills** (`.agent/skills/` o `.claude/commands/`) | Patrones técnicos específicos reutilizables, procedimientos por dominio |
| **Manuales** (`MANUAL_*.md`, `INSTRUCCIONES_*.md`) | Guías de referencia detalladas para humanos y agentes |
| **CONTEXTO_ACTIVO.md** | Estado actual del sistema, qué funciona, próximos pasos |
| **CATALOGO_SCRIPTS.md** | Scripts ejecutables con comando exacto y parámetros |

### 3.5 Protocolo de registro — OBLIGATORIO al terminar cualquier tarea

Antes de dar una tarea por terminada, responder estas preguntas:

1. ¿Corregí un bug o encontré un comportamiento inesperado de la BD/Effi/API? → **MANIFESTO §10 + skill del dominio**
2. ¿Cambié arquitectura o estructura de datos? → **CONTEXTO_ACTIVO**
3. ¿Creé o modifiqué un script? → **CATALOGO_SCRIPTS**
4. ¿Aprendí algo sobre Effi, la BD o el frontend que no estaba documentado? → **Skill del dominio correspondiente**
5. ¿Definí un patrón nuevo reutilizable? → **Crear/actualizar skill + entrada en catálogo**
6. ¿Adopté una técnica de una fuente externa (paper, guía, librería)? → **CATALOGO_REFERENCIAS** con URL, relevancia y dónde se aplicó
7. ¿Algún archivo Python supera 400 líneas o alguna función supera 80 líneas? → **Refactorizar ANTES de hacer commit** (ver `.agent/skills/desarrollo_python.md`)

**Regla absoluta: ningún problema resuelto queda sin registrar. Si se descubrió en esta sesión, se documenta en esta sesión.**

`.agent/catalogo-skills.md` lista **todas** las skills Y manuales disponibles. Toda skill o manual nuevo → entrada en el catálogo antes de terminar.

### 3.6 Protocolo de trabajo por módulo

**Al empezar a trabajar en un módulo:**
1. Leer `CONTEXTO_ACTIVO.md` para ver qué está activo
2. Leer el contexto del módulo: `.agent/contextos/<modulo>.md`
3. Verificar si hay plan activo en `.agent/planes/actuales/`

**Al terminar una tarea significativa:**
1. Actualizar `.agent/contextos/<modulo>.md` con el nuevo estado
2. Actualizar `CONTEXTO_ACTIVO.md` si cambió la prioridad o estado del módulo
3. La memoria de Claude (`MEMORY.md`) siempre refleja el contexto activo más reciente

### 3.7 Convención de backups de BD

Todos los backups SQL del servidor se guardan en `/home/osserver/Proyectos_Antigravity/backups/{nombre_bd}/{YYYY-MM-DD_HHMMSS}.sql`.
- Esta carpeta vive **fuera de cualquier repo git** del proyecto — sirve a todas las BDs del servidor (effi_data, os_inventario, ia_service_os, os_whatsapp, espocrm, etc.)
- Comando estándar: `mysqldump -u osadmin -pEpist2487. --single-transaction --routines --triggers {bd} > {backup_dir}/$(date +%Y-%m-%d_%H%M%S).sql`
- **Cuándo crear backup**: antes de cambios destructivos (DROP, TRUNCATE), antes de migraciones de schema, cuando Santi lo pida, antes de cerrar definitivamente un inventario.
- Detalle completo: `feedback_backups_bd.md` en la memoria de Claude.

### 3.8 Protocolo de documentación de scripts

Al crear un script nuevo, agregar entrada en `CATALOGO_SCRIPTS.md` con:
- Propósito (1 línea)
- Comando de ejecución manual exacto
- Archivos que genera / tablas que modifica
- Dependencias (otros scripts, credenciales, servicios)
- Comportamientos especiales o errores conocidos

---

## 4. TONO Y COMUNICACIÓN

- **Claridad Quirúrgica**: Profesional, directa y empática.
- **NUNCA suponer, SIEMPRE preguntar.** Admitir ignorancia es una virtud; suponer es un error crítico.
- **Un paso a la vez**: Divide, planifica y conquista.
- **100% en Español** — toda comunicación visible para Santi.
- **Comunicar cambios**: Antes de hacer cambios importantes, comunicarlos. Si surge un cambio durante una tarea grande, explicar a Santi de manera clara y simple (sin tecnicismos innecesarios) qué cambió.
- **Resumen obligatorio al finalizar**: Al terminar cualquier tarea significativa, entregar un resumen claro de qué se hizo, qué cambió y qué hay que saber. Santi dirige — necesita entender el resultado, no la implementación técnica.

---

## 5. AUTONOMÍA DE EJECUCIÓN — DOS FASES

**Esta distinción es fundamental para trabajar eficientemente.**

**Fase de planificación** → NUNCA suponer, SIEMPRE preguntar.
Antes de ejecutar, confirmar el enfoque, aclarar dudas y obtener la aprobación de Santi. No se empieza sin un plan claro y acordado.

**Fase de ejecución** (plan acordado) → Ejecutar sin pedir aprobación por cada sub-paso.
Una vez que Santi dio la orden, no interrumpir para pedir permiso en cada comando, consulta SQL, lectura de archivo o commit de git. Esas aprobaciones intermedias generan fricción innecesaria. Solo detener si surge algo inesperado que cambia el alcance.

"Listo, adelante" o "Ejecutá el plan" = señal de arranque para ejecución autónoma.

---

## 5B. FILOSOFÍA 5S JAPONESA — SIMPLICIDAD AL MÁXIMO

**Regla cardinal del proyecto. Aplica a TODO: frontend, backend, endpoints, modales, componentes, variables.**

### Principio de Código Mínimo Suficiente

> **El código correcto es el mínimo que resuelve el problema real — ni más, ni menos.**

Antes de escribir cualquier línea, preguntarse: *¿es necesaria para que esto funcione hoy?*
Si la respuesta no es un "sí" claro → no va.

No agregar: abstracciones para un solo uso, error handling para escenarios imposibles, parámetros opcionales que nadie usa, validaciones en código interno ya garantizado por el flujo, logs de debug que quedan en producción.

Sí agregar cuando realmente se necesita: lógica de negocio real, validación en bordes del sistema (entrada de usuario, APIs externas), manejo de errores que sí pueden ocurrir.

*Tres líneas similares son mejores que una abstracción prematura.*
*Un bug arreglado en el lugar correcto es mejor que un parche encima.*

### Principio anti-duplicación (5S)
Una operación = una función. Un modal = un modal. Una variable = una variable. Si hay dos caminos para hacer lo mismo, es un bug esperando a nacer. **Antes de crear algo, verificar que no exista.**

### Checklist obligatorio antes de crear CUALQUIER cosa

1. **¿Ya existe una función que haga esto?** → Úsala. Si le falta algo, extiéndela.
2. **¿Ya existe un modal/componente para esta interacción?** → Emite un evento al padre para que abra el que ya existe. NUNCA crear un segundo modal.
3. **¿Estoy creando una nueva variable de estado para algo que ya se controla en otro lugar?** → Elimínala. Usa la misma ref.
4. **¿Hay dos endpoints que hacen variaciones de lo mismo?** → Unifica en uno con parámetros.
5. **¿Tengo que arreglar algo en dos sitios?** → STOP. Primero refactoriza para que exista en un solo sitio, luego arregla.

### Caso real (lección aprendida v2.3.0→v2.3.3)

Existían dos modales para "completar tarea":
- TareasPage: input de minutos, sus propias variables `tiempoInput`, función `confirmarTiempoModal`
- TareaPanel: popover h+m, sus propias variables `tiempoFinalH/M`, función `confirmarCompletar`

Al encontrar un bug de pre-fill, hubo que arreglarlo en **los dos lugares**. Al cambiar la precisión a HH:MM:SS, habría que cambiarlo en **los dos**.

**Solución 5S**: TareaPanel emite `completar-tarea`, TareasPage abre SU modal. Un solo modal, un solo pre-fill, un solo confirm. El cambio a HH:MM:SS se hizo en un solo sitio y cubrió automáticamente los dos caminos. Resultado: −46 líneas de código, 0 duplicación, 0 bugs de divergencia.

---

## 7. FLUJO DE TRABAJO OBLIGATORIO

### ⚠️ REGLA ABSOLUTA: LEER ANTES DE ESCRIBIR

**NUNCA escribir código sin leer primero el código existente del archivo que se va a modificar.**

Antes de CADA edición:
1. Leer el archivo o la sección relevante
2. Entender cómo funciona actualmente
3. Verificar si ya existe solución
4. Solo entonces escribir el cambio

**Por qué existe:** Claude ha causado bugs al escribir código sin entender el contexto — duplicando lógica, rompiendo funcionalidad existente, agregando código que contradice lo implementado.

**Orden de construcción (INVIOLABLE):**
```
LEER CÓDIGO EXISTENTE → VISIÓN → BASE DE DATOS (estructura) → IMPLEMENTACIÓN
```
No se puede construir sin entender qué quiere Santi. No se debe generar código sin que la base de datos esté estructurada primero. Siempre partir del estado de la BD, sus campos y reglas.

### ⚠️ REGLA ABSOLUTA: NINGUNA TAREA SIN PLAN

**Por qué existe esta regla:** El contexto del chat se pierde. Si no hay un plan escrito en el repo, cuando el contexto se llena la tarea queda a medias — nadie puede saber qué faltó. Un plan en MD es la garantía de continuidad entre sesiones.

**Antes de iniciar CUALQUIER tarea no trivial (más de 1 archivo o 1 endpoint):**

1. Crear un archivo de plan en `.agent/planes/actuales/PLAN_NOMBRE_YYYY-MM-DD.md` con:
   - Objetivo y decisiones de diseño
   - Checklist de tareas (`- [ ] Tarea`) — marcar `[x]` con fecha al completar
   - Schema SQL si aplica
   - Sección "Tareas para Subagentes" si hay trabajo paralelizable (opcional)
2. Mostrar el plan a Santi y esperar confirmación
3. Solo entonces ejecutar — ir tildando `[x]` a medida que se completa cada paso
4. Al terminar: mover el archivo a `.agent/planes/completados/` y actualizar el contexto del módulo

**⚠️ REGLA SOBRE PLANES — NUNCA BORRAR:**
Los planes NUNCA se eliminan. Un plan completado es un registro histórico.
- `.agent/planes/actuales/` → plan activo en ejecución
- `.agent/planes/completados/` → plan finalizado (mover aquí, agregar `**Estado**: ✅ Completado — YYYY-MM-DD`)
- `/home/osserver/.claude/plans/` → planes del sistema Claude Code (EnterPlanMode). Al completarse: actualizar `**Estado**` a `Completado — fecha`. NUNCA eliminar.

**Consecuencias si no se cumple:**
- Tareas quedan a medias sin registro de qué faltó
- En la siguiente sesión no hay forma de saber el estado real
- Santi debe repetir el contexto completo desde cero (pérdida de tiempo)

**Esta regla aplica a todos los agentes**: Claude Code, subagentes Claude, y cualquier otro. Ningún agente puede iniciar implementación sin que exista un plan aprobado en `.agent/planes/actuales/`.

**Al iniciar sesión:** leer `.agent/planes/actuales/` — si existe un plan, continuar desde donde quedó antes de hacer cualquier otra cosa.

**Antes de cualquier tarea:**
1. Leer manifiesto y contexto activo
2. Verificar si existe plan activo en `.agent/planes/actuales/`
3. Verificar si existe skill relevante en el catálogo
4. Confirmar con Santi si hay dudas
5. Crear plan → aprobación → ejecutar

**Al asignar tareas a agentes:**
- Siempre referenciar el archivo de plan activo
- Ser totalmente específico: qué hacer, en qué archivos, qué pasos del plan
- Referenciar archivos de contexto relevantes
- Indicar explícitamente cuándo el plan está aprobado para ejecución autónoma

---

## 8. REGLA TRANSVERSAL DE ENTORNOS

**NUNCA conectarse ni alterar las bases de datos o servidores de Producción de manera directa para desarrollo.**

Todo trabajo, pruebas y cambios estructurales de BD se hacen en entorno local/staging. Para llevar cambios a producción se usa el pipeline de despliegue aprobado.

Un agente que toque Producción manualmente comete una falta crítica.

### Mapa real de BDs (actualizado 2026-04-24)

| BD | Ubicación física | Rol |
|---|---|---|
| `effi_data` | MariaDB **local** (servidor casa) | **Intermediaria de tránsito del pipeline. SOLO el orquestador puede leer/escribir.** Ningún otro script o app debe consultarla. |
| `os_integracion` | MariaDB **VPS Contabo** (94.72.115.156) | **Fuente de verdad consolidada** (41 tablas zeffi_* + resumen_ventas_* + crm_contactos + catalogo_articulos + inv_catalogo_articulos). Toda app/script de inventario, producción, gestión, ERP la consulta acá. |
| `os_gestion` | MariaDB **VPS Contabo** | Sistema Gestión OS (jornadas, tareas, etiquetas) |
| `inventario_produccion_effi` | MariaDB **VPS Contabo** | Solicitudes (`prod_solicitudes`), grupos (`prod_grupos`), recetas (`prod_recetas*`), logs (`prod_logs`), inventario físico (`inv_*`). NO contiene tablas zeffi_* (las consulta desde os_integracion). |
| `ia_service_os` | MariaDB **local** | Servicio Central de IA (reglas, ejemplos, agentes, prompts) |
| `os_whatsapp` | MariaDB **local** | WA Bridge (config, contactos, mensajes) |
| `espocrm` | MariaDB **local** | CRM (488 contactos, vía Docker) |
| `u768061575_os_comunidad` | **Hostinger** | ERP en producción (`menu.oscomunidad.com`) — **NUNCA tocar — PROHIBICIÓN ABSOLUTA** |

> **Hostinger ya NO se usa para `os_integracion` ni `os_gestion`.** Esas BDs se migraron al VPS Contabo el 2026-04-20. **Hostinger queda exclusivamente para `os_comunidad`** (el ERP real, intocable).

### Regla absoluta: `effi_data` = intermediaria, no fuente de verdad

**`effi_data` (local) es una BD de tránsito**. El orquestador del pipeline (`scripts/orquestador.py`) la usa para:
1. Recibir lo que descarga de Effi.com.co (vía exports Playwright)
2. Calcular tablas resumen
3. Propagarlo todo a `os_integracion` en el VPS (`scripts/sync_hostinger.py` — nombre legacy, ya apunta al VPS)

**Después de cada corrida del pipeline, los datos quedan idénticos en local y VPS.** Pero solo el VPS es la fuente de verdad. Si una app necesita datos de Effi (OPs, materiales, artículos, recetas, costos), **debe consultar `os_integracion` en el VPS, NUNCA `effi_data` local**.

#### Por qué esta regla
- `effi_data` puede tener datos parciales mientras corre el pipeline → race conditions
- Si en algún momento queremos apagar el servidor de casa, las apps no se rompen porque ya leen del VPS
- Coherencia: una sola fuente de verdad para todo el ecosistema

#### Cómo conectarse a `os_integracion` desde código
```python
# Python
from lib import integracion
with integracion(dict_cursor=True) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM zeffi_produccion_encabezados WHERE ...")
```
```js
// Node
const db = require('./lib/db_conn')
const pool = await db.integracion()
const [rows] = await pool.query("SELECT * FROM zeffi_produccion_encabezados WHERE ...")
```

#### Excepción única
El **orquestador y sus scripts hijos** (`scripts/sync_*.py`, `calcular_resumen_*.py`, `import_all.js`, `export_*.js`, etc.) sí escriben en `effi_data` local — ese es su trabajo. Cualquier otro código no.

### Tablas analíticas — viven en `os_integracion` (VPS)
Las tablas `resumen_ventas_*` (resumen_ventas_facturas_mes, resumen_ventas_remisiones_canal_mes, etc) tienen como única fuente de verdad `os_integracion` en el VPS. El pipeline las calcula en local (staging temporal) y las propaga al VPS. **NO leer la versión local entre corridas.**

---

## 8B. CONEXIONES A BD — CENTRALIZACIÓN OBLIGATORIA

> **Regla activa desde 2026-04-20** (commit `ece85a4`). Aplica a TODO agente que toque el repo: Claude Code, subagentes, Antigravity Google Labs, y cualquier script autónomo (`claude -p`, crons, trainers).

**Todas las credenciales y hosts de BD viven en UN SOLO archivo: `integracion_conexionesbd.env` en la raíz del repo.** Ningún archivo de código (`.js`, `.py`, `.sh`) puede contener host, puerto, usuario, password, nombre de BD, ni ruta SSH hardcoded. Migrar entre servidores = editar ese archivo, cero cambios de código.

### Artefactos del sistema
| Archivo | Propósito |
|---|---|
| [integracion_conexionesbd.env](../integracion_conexionesbd.env) | Creds reales (gitignored) |
| [integracion_conexionesbd.env.example](../integracion_conexionesbd.env.example) | Plantilla versionada |
| [lib/db_conn.js](../lib/db_conn.js) | Helper Node — pools mysql2 + SSH tunnel ssh2 |
| [scripts/lib/db_conn.py](../scripts/lib/db_conn.py) | Helper Python — context managers pymysql + sshtunnel |
| [package.json](../package.json) | Deps compartidas (mysql2 + ssh2) de la raíz |

### Prefijos de conexión disponibles
- `DB_LOCAL_*` — MariaDB local (cubre `effi_data`, `ia_service_os`, `os_whatsapp`, `os_inventario`, `espocrm`, `ia_local`, `nextcloud`, `nocodb_meta`).
- `DB_INTEGRACION_*` — BD `os_integracion` (hoy Hostinger vía SSH, mañana VPS).
- `DB_GESTION_*` — BD `os_gestion` (hoy Hostinger, mañana VPS).
- `DB_COMUNIDAD_*` — BD `os_comunidad` (Hostinger permanente, ERP real Effi — solo lectura).

Cada prefijo remoto incluye su propio `*_SSH_HOST`, `*_SSH_PORT`, `*_SSH_USER`, `*_SSH_KEY`, `*_LOCAL_PORT` (puerto local del tunnel), `*_NAME`, `*_USER`, `*_PASS`.

### API obligatoria

**Node** — `const db = require('<repo>/lib/db_conn')`:
- `await db.local(nombreBD)` — pool a BD local cualquiera.
- `await db.integracion()` / `db.gestion()` / `db.comunidad()` — pools remotos (abren SSH tunnel la primera vez, con reconexión automática).
- Timezone Colombia (`-05:00`) aplicado automáticamente en cada conexión.

**Python** — dos modos:
```python
# Modo moderno (context manager)
from lib import local, integracion, gestion, comunidad
with local('effi_data') as conn: ...
with integracion(dict_cursor=True) as conn: ...

# Modo legado (dict raw para pymysql.connect(**DB))
from lib import cfg_local, cfg_remota_ssh, cfg_remota_db
DB_EFFI = dict(**cfg_local(), database='effi_data')
_ssh = cfg_remota_ssh('INTEGRACION')   # host/port/user/key/remote_host/remote_port
_db  = cfg_remota_db('INTEGRACION')    # user/password/database/charset
```

Para agregar `scripts/lib/` al `sys.path` desde cualquier script, usar el snippet canónico:
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))            # scripts/foo.py
# ó parent-parent desde scripts/sub/foo.py
```

**Bash**:
```bash
set -a; . /home/osserver/Proyectos_Antigravity/Integraciones_OS/integracion_conexionesbd.env; set +a
mysql -u "$DB_LOCAL_USER" -p"$DB_LOCAL_PASS" -h "$DB_LOCAL_HOST" effi_data -e "..."
```

### PROHIBIDO (falta crítica — equivale a tocar producción sin autorización)
- Literales `'Epist2487.'`, `'osadmin'`, `'109.106.250.195'`, `'65002'`, `'u768061575_*'`, `'/home/osserver/.ssh/sos_erp'` en cualquier archivo del repo.
- Dict inline tipo `dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='X')`.
- Llamar a `SSHTunnelForwarder((SSH_HOST, SSH_PORT), ssh_username='u768061575', ...)` con valores literales.
- Reimplementar la lógica de tunnel/pool en vez de reusar los helpers.
- Fallbacks de tipo `os.getenv('DB_PASS', 'Epist2487.')` — si el `.env` no carga, FALLAR explícito.

### OBLIGATORIO al crear código que toque BD
1. Importar del helper central (una de las formas arriba).
2. Verificar con `grep -n "Epist2487\|osadmin\|u768061575" <archivo>`: cero hits.
3. Si el script corre en un entorno nuevo, confirmar que `integracion_conexionesbd.env` existe (en producción siempre; en nuevo checkout, crear desde `.example`).

### Añadir un nuevo destino remoto
1. Agregar bloque `DB_<NOMBRE>_*` al `.env` real y al `.example`.
2. Node: agregar entrada en `_remotas` de `lib/db_conn.js` y método `nombre()`.
3. Python: agregar `def nombre(...)` en `scripts/lib/db_conn.py` delegando a `remota('NOMBRE')`.

### Migración entre servidores (referencia)
Para mover `os_integracion` y/o `os_gestion` a otro servidor (ej: Hostinger → VPS Contabo):
1. Dump + import en el servidor destino.
2. Editar los bloques `DB_INTEGRACION_SSH_*` / `DB_GESTION_SSH_*` en `integracion_conexionesbd.env` (host, puerto SSH, usuario, key, nombre BD, usuario/pass MySQL).
3. Reiniciar servicios afectados (`os-gestion`, `os-erp-frontend`, `ia-service`, `wa-bridge` si aplica).
4. Rollback si falla = revertir ese archivo, restart.

### Registro histórico
- Commit `ece85a4` (2026-04-20): refactorización de 35 archivos (5 servicios Node + 30 scripts Python) al patrón centralizado.
- Plan completo archivado: `.agent/planes/completados/migracion_bd_env_centralizado_2026-04-20.md`.
- Feedback permanente: `memory/feedback_conexiones_bd_env.md` (en memoria Claude).

---

## 9. CONTEXTO Y ESTRUCTURA DEL PROYECTO

- **Propósito**: Centralizar y automatizar datos de Effi, EspoCRM y otras fuentes en MariaDB para análisis y gestión operativa.
- **Persistencia**: MariaDB local — BD `effi_data` (Effi), `espocrm` (CRM), `nocodb_meta` (NocoDB).
- **Visualización operativa**: NocoDB (tablas externas + vistas SQL de MariaDB).
- **Fuentes**: Effi (vía Playwright) y EspoCRM.
- **Infraestructura**: Docker — NocoDB, n8n, EspoCRM, Nextcloud, Gitea, MinIO, Grafana, Portainer, phpMyAdmin.
- **Acceso público**: Cloudflare Tunnel → dominios `*.oscomunidad.com`.

### Orquestador Python (effi-pipeline)
- **Script**: `scripts/orquestador.py` — corre export + import cada 1h (Lun–Sab, 06:00–20:00).
- **Credenciales**: `scripts/.env` — **NUNCA subir a Git.**
- **Notificaciones**: email siempre + Telegram solo en error → usa `@os_notificaciones_sys_bot` (`TELEGRAM_NOTIF_BOT_TOKEN`). Bot de IA (`TELEGRAM_BOT_TOKEN`) es solo para conversaciones.
- **Systemd**: `systemd/effi-pipeline.service` + `.timer`
  - Test manual: `python3 scripts/orquestador.py --forzar`
  - Log: `journalctl -u effi-pipeline -f` o `logs/pipeline.log`

### 9.1 Estructura del repo

Cada módulo o herramienta independiente **debe tener su propio directorio en la raíz del repo**.

```
Integraciones_OS/
├── scripts/          ← pipeline Effi (exports, imports, sync, orquestador, ia_service, telegram_bot)
├── frontend/         ← ERP web (menu.oscomunidad.com) — Quasar + Node API
├── ia-admin/         ← Panel admin del servicio IA (ia.oscomunidad.com) — Quasar + Node API
├── wa_bridge/        ← WhatsApp HTTP Bridge (Baileys) — puerto 3100, BD os_whatsapp
├── espocrm-custom/   ← Customizaciones EspoCRM (PHP + JS)
├── docs/             ← Documentos de negocio (PDFs, DOCX, PPTX, XLSXs)
├── logs/             ← Logs de todos los servicios
├── systemd/          ← Unit files de systemd
└── .agent/           ← Contexto y documentación interna para Claude
```

**Regla para módulos nuevos:**
- Cualquier módulo nuevo → **directorio propio en raíz**, NO dentro de `scripts/`
- `scripts/` es exclusivo del pipeline Effi y sus servicios asociados (ia_service, telegram_bot)
- Cada módulo debe tener su propio `README.md` o entrada en `.agent/`

**Nota:** `ia_service/` y `telegram_bot/` viven dentro de `scripts/` por razones históricas. En el futuro, si crecen mucho, se pueden migrar a raíz — no es urgente.

---

## 10. REGLAS TÉCNICAS APRENDIDAS

### ⚠️ REGLA ARQUITECTURAL: EMPRESA Y AUDITORÍA EN TODA TABLA

**Patrón multi-tenant** (igual que SOS_ERP — ver `.agent/docs/MANUAL_EMPRESAS_USUARIOS.md`):

**TODA tabla de datos (no solo config global) DEBE tener:**
```sql
empresa               VARCHAR(50) NOT NULL DEFAULT 'ori_sil_2'  -- filtro principal
usuario_creacion      VARCHAR(150)  -- email del creador (inyectado del JWT)
usuario_ult_mod       VARCHAR(150)  -- email del último modificador (inyectado del JWT)
created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

**Excepción**: Tablas de configuración global que apliquen a todo el sistema (ej: `ia_agentes`).

**Reglas de seguridad — no negociables:**
1. `empresa` NUNCA viene del body del request → siempre se inyecta del JWT en el backend
2. Todo SELECT/UPDATE/DELETE en tablas por-empresa → `WHERE empresa = :empresa`
3. INSERT → inyectar empresa + usuario_creacion + usuario_ult_mod desde JWT
4. Si `empresa_activa` falta en JWT → rechazar con 403

**Tablas de empresa y acceso:**
- `ia_empresas` — catálogo de empresas del sistema
- `ia_usuarios_empresas` — qué empresas puede ver cada usuario y con qué rol
- Plan de migración: `.agent/planes/completados/PLAN_MULTITENANT_IA.md`



### ⚠️ REGLA ABSOLUTA: FUENTE DE VERDAD DE USUARIOS Y EMPRESAS

**`sys_usuarios` y `sys_empresa` en `u768061575_os_comunidad` (Hostinger) son la ÚNICA fuente de verdad para datos de usuarios y empresas.**

- Nombres, emails, teléfonos, estado → siempre de `sys_usuarios`
- Empresas → siempre de `sys_empresa`
- Relación usuario↔empresa → `sys_usuarios_empresas`
- **NUNCA consultar `ia_usuarios` (ia_service_os) para datos de usuarios** — esa tabla es solo para config del servicio IA (telegram_id, agente preferido, etc.)
- Columnas clave de `sys_usuarios`: `Email` (E mayúscula), `Nombre_Usuario`, `telefono`, `estado` ('Activo')

**Aplica a:** scripts Python, endpoints Node.js, cualquier servicio que necesite datos de usuarios.

### ⚠️ REGLA ABSOLUTA: VERIFICAR CREDENCIALES Y COLUMNAS ANTES DE IMPLEMENTAR

**Esta regla nació de 4+ errores consecutivos en la misma sesión (2026-03-16).**

**Para credenciales MySQL en Hostinger:**
1. **NUNCA asumir usuario MySQL** — Hostinger NO permite compartir el mismo usuario entre 2 BDs distintas.
2. Verificar en cPanel (Hostinger) → MySQL Databases → Database Users qué usuario tiene acceso a cada BD.
3. Credenciales verificadas (fuente de verdad en MEMORY.md):
   - `u768061575_os_comunidad` → user: `u768061575_ssierra047`, pass: `Epist2487.`
   - `u768061575_os_integracion` → user: `u768061575_osserver`, pass: `Epist2487.`
   - `u768061575_os_gestion` → user: `u768061575_os_gestion`, pass: `Epist2487.`

**Para columnas SQL:**
1. **NUNCA inventar nombres de columnas** — siempre verificar con `DESCRIBE <tabla>` antes de escribir el query.
2. `sys_usuarios`: columnas reales son `Nombre_Usuario`, `Nivel_Acceso`, `estado` (minúsculas en nombre), `Email` (mayúscula).
3. `sys_empresa`: `nombre_empresa` (no `nombre`), `estado='Activa'` (femenino, no 'Activo').
4. `sys_usuarios_empresas`: relación usa `rol` (no `perfil`).
5. Las tablas del ERP SOS tienen convenciones distintas al estándar snake_case — siempre verificar.

**Para JOINs cross-database en Hostinger:**
- Cada usuario MySQL solo tiene acceso a su propia BD. JOIN entre BDs distintas = Access Denied.
- Si necesitas datos de 2 BDs en un query → hacer 2 queries separados en Node y combinar en JS.
- Alternativa: subquery dentro de la misma BD (no funciona cross-DB de todas formas).

---

### ⚠️ REGLA: UTC_TIMESTAMP EN HOSTINGER — NUNCA NOW()

**Descubierto 2026-03-26: desfase de 5 horas entre header y tabla de jornadas.**

El servidor MySQL de Hostinger corre en `UTC+5` (zona de Bogotá), pero los datos se almacenan como UTC.
- `NOW()` devuelve hora local del servidor MySQL (UTC+5) → **5 horas adelantada** respecto a UTC
- `UTC_TIMESTAMP()` devuelve siempre UTC → correcto

**Regla**: En TODA query hacia Hostinger que calcule diferencias de tiempo (TIMESTAMPDIFF, comparación con fecha actual, etc.), usar `UTC_TIMESTAMP()` en lugar de `NOW()`.

### ⚠️ REGLA: SSH TUNNEL — ARQUITECTURA AUTO-RECONNECT

**Descubierto 2026-03-26: servicio caía tras ~16h de inactividad (ECONNRESET).**

`sistema_gestion/api/db.js` implementa auto-reconnect:
1. TCP server se crea UNA VEZ y permanece (nunca se recrea)
2. sshClient se recrea al detectar evento `close`
3. El callback del TCP server lee `sshClient` en runtime (no closure) → usa el cliente reconectado automáticamente
4. Pools MySQL se destruyen y recrean al reconectar
5. Retry: 5s primer intento, 15s si falla

### Gotchas críticos — zeffi_facturas_venta_detalle
- **`precio_neto_total` INCLUYE IVA**: usar `precio_bruto_total - descuento_total` para "ventas sin IVA". Nombre engañoso — nunca asumir.
- **Número de factura**: en detalle se llama `id_numeracion`.
- **Canal**: campo `marketing_cliente` — NULL/vacío se normaliza como `'Sin canal'`.
- **`vigencia_factura = 'Vigente'`**: filtro obligatorio en detalle para excluir anuladas.
- **id_cliente en facturas/remisiones**: formato "CC 74084937" (con prefijo tipo doc). `zeffi_clientes.numero_de_identificacion` = "74084937" (sin prefijo). Para JOIN: `SUBSTRING_INDEX(d.id_cliente, ' ', -1)`.

### Gotchas críticos — zeffi_clientes
- **Duplicados por `numero_de_identificacion`**: la tabla puede tener múltiples filas con el mismo NIT/CC (al menos 3 casos confirmados: `39440347`, `90173460334`, `9999999`). Un JOIN directo multiplica las filas de la tabla que se une, inflando sumas y conteos.
- **Regla obligatoria**: SIEMPRE deduplicar `zeffi_clientes` antes de hacer JOIN:
  ```sql
  LEFT JOIN (
    SELECT numero_de_identificacion, MAX(forma_de_pago) AS forma_de_pago
    FROM zeffi_clientes GROUP BY numero_de_identificacion
  ) c ON c.numero_de_identificacion = SUBSTRING_INDEX(f.id_cliente, ' ', -1)
  ```
- **Campos numéricos como texto**: `pdte_de_cobro`, `total_neto`, `cupo_de_credito_cxc` usan coma decimal → castear siempre: `CAST(REPLACE(COALESCE(campo,'0'),',','.') AS DECIMAL(15,2))`

### Verificación obligatoria de scripts analíticos
Al crear o modificar cualquier script de resumen, ejecutar los checks de integridad documentados en **`.agent/skills/integridad_datos.md`** antes de dar la tarea por terminada. Ningún script analítico se considera completo sin haber pasado esas verificaciones.

### NocoDB
- Tablas externas son solo lectura — relaciones entre tablas externas NO funcionan. Usar vistas SQL en MariaDB para JOINs.
- Conexión a MariaDB: usar IP `172.18.0.1` (gateway Docker), NO `host.docker.internal`.
- `osadmin@%` no funciona desde Docker — crear grants para `osadmin@172.18.0.%`.

### Cloudflare Tunnel
- Configuración en `/etc/cloudflared/config.yml`. Agregar hostname + reiniciar servicio + CNAME en Cloudflare DNS.

### 10.1 PREMISA CRÍTICA DE IA (Cero Alucinaciones)
**Regla absoluta para cualquier Bot o Agente IA que consuma datos del ERP:**
Para que la IA no invente respuestas o datos financieros, el flujo técnico obligado y el System Prompt de TODO agente debe seguir siempre estos 3 pasos (nunca intentar saltárselos):
1. **Generar código:** El Agente lee la pregunta + esquema y devuelve SÓLO una consulta SQL válida (o script equivalente).
2. **Ejecutar código:** El sistema/orquestador ejecuta el query ciegamente contra la BD MariaDB real y captura las filas retornadas.
3. **Responder usando ese resultado:** El sistema entrega los datos crudos de vuelta al Agente IA, quien redacta la respuesta usando única y exclusivamente la información del paso 2.

### 10.2 FLUJO CON IMÁGENES (Visión Multimodal)
Cuando el usuario envía una foto (desde Telegram u otro canal), el flujo tiene un paso previo:
```
Foto + texto (opcional)
      ↓
[Visión — agente con capacidad 'vision'] extrae texto estructurado de la imagen
      ↓
Texto extraído se inyecta como contexto en la pregunta
      ↓
[Flujo normal: Enrutador → SQL → Ejecutar → Redactar]
```
- El agente de visión se selecciona dinámicamente desde `ia_agentes.capacidades` (JSON `{"vision": true}`)
- Hoy es `gemini-flash` — puede cambiar sin tocar código, solo actualizar BD
- Si la imagen está en blanco o sin contenido, responde directo sin pasar por el enrutador
- Funciona con: capturas de pantalla, remisiones en papel, facturas físicas, etiquetas, conteos escritos

### 10.3 CAPACIDADES POR AGENTE
Cada agente declara sus capacidades en `ia_agentes.capacidades` (JSON). Capacidades definidas:
`vision` | `sql` | `codigo` | `razonamiento` | `documentos` | `contexto_largo` | `enrutamiento` | `imagen_generacion`
El servicio consulta esto para elegir el agente correcto por capacidad, sin hardcoding.

---

### 10.4 BOT TELEGRAM — PRESENTACIÓN DE DATOS

**Regla absoluta (2026-03-22):** Si una consulta devuelve **más de 2 registros**, el bot SIEMPRE debe mostrar el botón "Ver tabla completa" con la mini app visual. Sin excepción, sin importar número de columnas.

- `tabla.py` → `MAX_FILAS_INLINE = 2`. Solo 1-2 filas van inline. >2 = botón siempre.
- El LLM NUNCA debe formatear datos como tabla markdown (pipes `|`) en su texto. El system prompt de `_construir_prompt_respuesta()` lo prohíbe explícitamente.
- `_limpiar_tablas_texto()` elimina pipes del texto del LLM como red de seguridad.
- Gotcha del depurador viejo: el depurador de `ia_logica_negocio` hacía `SET activo=0 WHERE empresa=%s` (mataba TODAS las reglas incluyendo las recién aprendidas). Corregido: ahora solo comprime las consolidaciones (`creado_por='depurador-auto'`), nunca toca reglas individuales.

### ⚠️ REGLA: ALMACENAMIENTO DE ARCHIVOS SUBIDOS — DIRECTORIO UNIFICADO

**Ruta raíz:** `/home/osserver/subidos/`

Todo archivo subido por usuarios (imágenes, documentos, audio, etc.) va aquí. Cada módulo tiene su subdirectorio.

```
/home/osserver/subidos/
├── gestion/          ← Sistema Gestión (proyectos, dificultades, tareas)
├── inventario/       ← Fotos de inventario físico (futuro — migrar desde inventario/fotos/)
├── ia/               ← Archivos procesados por IA (audio, imágenes generadas)
└── erp/              ← ERP web (futuro)
```

**Política de nombres (obligatoria):**

```
{modulo}/{tipo}/{id}_{slug}/{YYYYMMDD}-{HHMMSS}_{hash6}.{ext}
```

| Segmento | Ejemplo | Regla |
|---|---|---|
| `modulo` | `gestion` | Nombre del módulo |
| `tipo` | `proyecto`, `dificultad`, `tarea` | Tipo de entidad |
| `id_slug` | `42_problema-proveedor` | ID numérico + nombre slugificado (max 40 chars, sin tildes, lowercase, guiones) |
| `timestamp` | `20260331-152045` | Fecha-hora Colombia al momento de subir |
| `hash6` | `a3f1b2` | 6 chars aleatorios (evita colisión si suben 2 archivos en el mismo segundo) |
| `ext` | `jpg`, `png`, `webp`, `pdf` | Extensión original del archivo |

**Ejemplo real completo:**
```
/home/osserver/subidos/gestion/dificultad/42_problema-proveedor/20260331-152045_a3f1b2.jpg
```

**Reglas de implementación:**
1. **BD guarda solo la ruta relativa** desde `/home/osserver/subidos/` → `gestion/dificultad/42_problema-proveedor/20260331-152045_a3f1b2.jpg`
2. **Nunca guardar la ruta absoluta** en BD — si cambia el servidor, solo se actualiza la raíz
3. **El servidor sirve los archivos** como estáticos vía Express (o Nginx si se necesita más rendimiento)
4. **Límite de tamaño:** 10 MB por archivo (imágenes). Validar en backend antes de guardar.
5. **Formatos permitidos:** jpg, jpeg, png, webp, gif, pdf. Validar MIME type, no solo extensión.
6. **Crear directorio del item** al subir el primer archivo (`mkdir -p` en el endpoint)
7. **Futuro:** cuando el ERP nuevo entre en producción, migrar a Cloudflare R2 siguiendo la skill `OS_ERP_INTEGRADO/.agent/skills/multimedia_r2.md`. La ruta relativa en BD no cambia — solo cambia dónde se almacena físicamente.

---

## 12. MANUAL DE ESTILOS — Frontend ERP

| Archivo | Contenido |
|---|---|
| `frontend/design-system/MANUAL_ESTILOS.md` | Manual completo — CSS, variables, reglas, componentes |
| `frontend/design-system/screenshots/INDEX.md` | Índice de las 88 capturas de referencia (Linear.app) |
| `frontend/design-system/screenshots/*.png` | 88 capturas reales organizadas por elemento |

- El manual define: colores exactos, tipografía, espaciado, todos los componentes.
- Elemento no documentado = **preguntar a Santi** antes de inventar.
- Al definir un elemento nuevo con Santi, actualizar el manual inmediatamente.

---

## 13. ESTÁNDAR DE NAVEGACIÓN DRILL-DOWN — ERP

### Regla universal: toda tabla tiene drill-down

**En este ERP, CUALQUIER fila de CUALQUIER tabla es clickeable y navega al siguiente nivel.**
No existe tabla decorativa. Si hay filas, hay drill-down.

### Patrón obligatorio de 3 niveles

```
Nivel 1 — Resumen agrupado        (1 fila = 1 cliente / 1 mes / 1 canal)
  └─ click → Nivel 2 — Lista de documentos    (facturas, órdenes, remisiones del agrupador)
                └─ click → Nivel 3 — Detalle del documento   (ítems, campos completos)
```

**Regla crítica:** el Nivel 3 siempre reutiliza la vista de detalle canónica del tipo de documento.
- Factura → siempre `/ventas/detalle-factura/:id_interno/:id_numeracion` (DetalleFacturaPage)
- Orden de venta → siempre `/ventas/consignacion-orden/:id_orden` (DetalleConsignacionPage)
- Remisión → (pendiente) cuando se construya, su propia vista canónica

**NUNCA crear una vista de detalle ad-hoc para el mismo tipo de documento.** Reutilizar la existente.

### Catálogo de vistas — referencia obligatoria

Ver `.agent/CATALOGO_VISTAS.md` — **leer antes de crear cualquier página nueva**.
Contiene todas las vistas existentes, sus rutas, propósito y jerarquía de navegación.

### Nomenclatura de rutas drill-down

```
/ventas/{modulo}                          → Nivel 1: resumen
/ventas/{modulo}-cliente/:id_cliente      → Nivel 2: documentos del cliente
/ventas/{modulo}-orden/:id_orden          → Nivel 3: detalle documento (si aplica)
```
O para módulos con mes:
```
/ventas/{modulo}/:mes                     → Nivel 1: por mes
/ventas/{modulo}/:mes/:id_cliente         → Nivel 2: por cliente en ese mes
```

---

## 14. DICCIONARIO DE NEGOCIO

- Nomenclatura en Español (coherente con ERP Effi).
- Clientes Effi → `tipo_de_persona` distingue empresa/persona natural.
- Campo de enlace clave: `clientes.numero_de_identificacion` ↔ `facturas_venta_encabezados.id_cliente` (gotcha: prefijo tipo doc en facturas).

---

## 15. GESTIÓN DE SCREENSHOTS TEMPORALES Y UI

Claude Code (o un subagente) documenta bugs de UI almacenando capturas en `screenshots_temporales/`.
1. **Lectura:** Usar estas imágenes para entender el estado real de la UI al hacer debug de componentes Vue (alineación, tablas vacías, etc).
2. **Ciclo de Vida:** Cuando el bug se cierre, **borrar las capturas asociadas** — no contaminar el repo.
3. **Excepción:** Si una captura representa un patrón de diseño importante → moverla a `frontend/design-system/screenshots/` y actualizar su `INDEX.md`.

---

## 17. PROTOCOLO DE QA Y TESTING

### Archivos clave
- `.agent/INSTRUCCIONES_TESTING.md` — **política y protocolo completo de QA** (leer antes de cualquier sesión de testing)
- `.agent/QA_REGISTRO.md` — **registro vivo de bugs** — se actualiza en cada sesión de QA

### Reglas fundamentales
1. **Claude Code** (o un subagente) hace el QA funcional de cada feature antes de declararla terminada.
2. Los bugs se documentan en `QA_REGISTRO.md` con estado 🔴/🟡/🟢.
3. Los screenshots de bugs abiertos viven en `screenshots_temporales/`. **Al cerrarse, se borran.**
4. Claude Code no puede marcar una tarea como terminada si hay bugs 🔴 abiertos relacionados.
5. Santi da el visto bueno final.
6. Antigravity puede hacer QA visual si Santi lo decide, pero no es requerido ni bloqueante.

### Flujo mínimo de QA por feature
```
Claude Code implementa + build + restart
  → Subagente o Claude Code: curl endpoints → verificar datos
  → Subagente o Claude Code: Playwright → navegar UI → screenshots si aplica
  → Documentar bugs en QA_REGISTRO.md
  → Claude Code: corrige bugs reportados
  → Re-verificar → cerrar bugs
  → Screenshots de bugs resueltos → borrar
```

---

## 19. SUPER AGENTE CLAUDE CODE — Modo paralelo en el Bot de Telegram

Claude Code corre como **Super Agente** en el bot de Telegram, en paralelo al `ia_service` existente. NO es otro proveedor LLM dentro de ia_service — es el mismo Claude Code CLI con acceso total al sistema, corriendo como proceso independiente.

**⚠️ IMPORTANTE: Si estás leyendo esto como instancia de Claude Code invocada por el bot (claude -p), seguí las reglas de esta sección al pie de la letra.**

### Acceso
- Nivel 5+ → puede usar el Super Agente para consultas
- Nivel 7 (Santi) → puede aprobar cambios de código/estructurales

### Arquitectura
```
Bot Telegram
├── Modo normal → ia_service Flask (gemini, groq, cerebras, etc.)
└── Modo Super Agente → claude -p con --resume (bypass ia_service completo)
```

### Sesiones persistentes (--resume)
- Cada usuario tiene conversaciones con sesiones persistentes de Claude Code.
- Primera vez: `claude -p "PROMPT SISTEMA" --output-format json` → obtiene session_id → `claude -p "PREGUNTA" --resume SESSION_ID --output-format json`
- Siguientes mensajes: `claude -p "PREGUNTA" --resume SESSION_ID --output-format json`
- Claude mantiene el historial internamente — NO se pasa historial en el prompt.
- El prompt sistema se envía UNA vez al crear la sesión, no en cada mensaje.
- Las sesiones se guardan como archivos `.jsonl` en `~/.claude/projects/-home-osserver-Proyectos-Antigravity-Integraciones-OS/`

### Protocolo de nombres de conversación
- Nombre generado automáticamente: **`"SA - " + primeras palabras de la pregunta`** (máx 40 chars, corte en último espacio)
- Se inyecta al inicio del primer prompt: `f'{nombre}\n\n{prompt_sistema}'` → Claude nombra el `.jsonl` con ese texto
- `sa_sesiones.nombre` = mismo nombre → BD y filesystem sincronizados
- El usuario puede renombrar desde `[📋 Conversaciones]` → `[✏️ Renombrar]`

### Menú del Super Agente en Telegram
```
[📝 Nueva] [📋 Conversaciones] [⚙️ Ajustes]
```
- **📝 Nueva**: crea conversación nueva (nuevo session_id)
- **📋 Conversaciones**: lista inline → tap para ver opciones (🔄 Cambiar / ✏️ Renombrar / 🗑️ Borrar)
- **⚙️ Ajustes**: vuelve al menú normal del bot (cambiar agente, etc.)

### Tablas en ia_service_os (prefijo sa_)
- `sa_sesiones` — conversaciones por usuario: `id`, `empresa`, `usuario_id`, `claude_session_id` (UUID), `nombre`, `activa` (1=activa, 0=inactiva), `created_at`, `updated_at`
- `sa_config` — `prompt_sistema` editable por empresa (desde ia.oscomunidad.com → Super Agente)
- `sa_cambios` — registro detallado de TODA corrección autónoma en BD

### Formato de respuesta (definido en el prompt sistema)
El prompt le indica al Super Agente 3 formatos:
1. **Tabla** → JSON puro: `{"tipo":"tabla","texto":"desc","titulo":"T","columnas":[...],"filas":[[...]]}`
   - filas = arrays de strings, NO objetos
   - El bot renderiza: ≤2 filas ASCII inline, >2 filas botón "Ver tabla completa"
2. **Texto** → texto plano directo
3. **Aprobación** → JSON: `{"tipo":"aprobacion","mensaje_usuario":"...","descripcion":"...","causa_raiz":"...","cambio_propuesto":"..."}`
   - El bot envía mensaje a todos los usuarios nivel 7 con botones ✅/❌

### Reglas de corrección — REGISTRO OBLIGATORIO
- **Correcciones automáticas (sin aprobación)**: tablas `ia_logica_negocio`, `ia_ejemplos_sql`, `ia_tipos_consulta`
  - **ANTES de cada cambio**: registrar en `sa_cambios` con: `tabla_afectada`, `campo`, `valor_anterior`, `valor_nuevo`, `razon`, `usuario_id`
  - Si no se registra en `sa_cambios`, el cambio NO está autorizado
- **Cambios que requieren aprobación nivel 7**: archivos Python/JS/config, ALTER/DROP/CREATE TABLE, systemd, Docker, Cloudflare
  - Devolver JSON tipo `aprobacion` — el bot notifica a Santi
- **PROHIBIDO siempre**: parches superficiales, hardcoding, try/catch vacíos/genéricos
  - Si no hay causa raíz → solo documentar, NUNCA "arreglar" el síntoma

### Archivos clave
- `scripts/telegram_bot/superagente.py` — sesiones + `_ejecutar_claude()` con --resume + procesamiento de respuesta
- `scripts/telegram_bot/handlers_sa.py` — handlers Telegram: menú, conversaciones, callbacks
- `scripts/telegram_bot/bot.py` — routing: si agente='superagente' → handlers_sa (NO ia_service)

---

## 20. REGLAS DE DOCUMENTACIÓN

> Detalle completo en `.agent/MANUAL_DOCUMENTACION.md` — este es el resumen ejecutivo.

### La jerarquía

```
MEMORY.md (Claude)     → Mapa del repo. Primera lectura. < 200 líneas. Solo índices.
MANIFESTO.md           → Constitución. Reglas globales. Este archivo.
CONTEXTO_ACTIVO.md     → Estado actual. Se actualiza cada sesión.
contextos/<módulo>.md  → Contexto profundo. Leer solo al trabajar en ese módulo.
CATALOGO_*.md          → Catálogos de referencia. Actualizar al agregar recursos.
Skills (.claude/)      → Guías especializadas por dominio.
```

### Reglas básicas

1. **MEMORY.md es un mapa, no un dump.** Si supera 200 líneas, mover detalle a contextos/ o MANIFESTO.md y dejar solo el puntero.
2. **Un dato, un lugar.** Si algo aparece en dos archivos, hay duplicación. Elegir fuente canónica.
3. **Al terminar una tarea significativa**: actualizar `contextos/<módulo>.md`. Si cambió el estado global, actualizar `CONTEXTO_ACTIVO.md`.
4. **Planes nunca se borran.** Completados → `.agent/planes/completados/` con `Estado: Completado` al inicio.
5. **Ciclo de vida de módulos**: En desarrollo → Activo → Estable → Archivado. Módulos estables sin trabajo activo NO tienen prioridad Alta en CONTEXTO_ACTIVO.md.
