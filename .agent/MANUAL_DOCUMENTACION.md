# Manual de Contexto y Documentación — Integraciones OS

> **Propósito**: define cómo se organiza, mantiene y evoluciona toda la documentación del proyecto. Cualquier agente o desarrollador que lea este manual debe poder orientarse solo sin pedir explicaciones.

---

## La metáfora: Constitución + Mapa + Contextos

El sistema de documentación funciona en capas:

```
MEMORY.md          ← Mapa del repo. Primera lectura en cada sesión.
                       Orientación global en < 200 líneas.

MANIFESTO.md       ← Constitución del proyecto. Reglas que no cambian:
                       roles, frontend, arquitectura, gotchas técnicos.

CONTEXTO_ACTIVO.md ← Estado actual del sistema. Se actualiza cada sesión.
                       Responde: ¿qué está activo? ¿en qué estamos?

contextos/*.md     ← Contexto profundo por módulo. Se lee solo cuando
                       se trabaja en ese módulo.

CATALOGO_*.md      ← Catálogos de referencia (scripts, APIs, tablas,
                       agentes, vistas). Se consultan según necesidad.

Skills (.claude/)  ← Guías especializadas para trabajar en un dominio
                       (effi-database, ia-service, erp-frontend, etc.)

docs/ + manuales/  ← Documentación profunda y permanente.
                       No cambia frecuentemente.

planes/            ← Historial de decisiones de implementación.
```

---

## MEMORY.md — el mapa

**Regla fundamental**: MEMORY.md es un **índice navegable**, no un dump de información.

### Qué va en MEMORY.md
- ✅ Descripción del proyecto en 2–3 líneas
- ✅ Tabla de módulos activos con links a sus contextos y skills
- ✅ Mapa de todos los documentos (dónde está cada cosa)
- ✅ Reglas críticas (solo el link al archivo, sin el detalle inline)
- ✅ Tabla de BDs (rol de cada una, credenciales en 2 líneas)
- ✅ Tabla de apps web con URLs y puertos
- ✅ Roles del equipo (3 líneas)

### Qué NO va en MEMORY.md
- ❌ Detalle técnico de módulos (eso va en contextos/)
- ❌ Gotchas específicos de Effi, SQL, EspoCRM (eso va en skills)
- ❌ Listas de campos de BD (eso va en CATALOGO_TABLAS)
- ❌ Pasos del pipeline (eso va en contextos/pipeline_effi.md)
- ❌ Stack de agentes IA (eso va en CATALOGO_AGENTES.md)
- ❌ Historial de cambios o decisiones (eso va en contextos o MANIFESTO)

### Regla de tamaño
**MEMORY.md no debe superar 200 líneas.** El sistema de Claude Code carga solo las primeras 200. Si crece, hay que mover contenido a archivos topic en `memory/` y dejar solo el puntero en MEMORY.md.

---

## MANIFESTO.md — la constitución

Contiene reglas que cambian poco y aplican al proyecto completo:
- Reglas de frontend (build, manual de estilos, verificaciones obligatorias)
- Roles y gobernanza (Santi, Claude Code, Antigravity, Subagentes)
- Arquitectura general (BDs, servicios, infraestructura)
- Reglas técnicas aprendidas (timezone, gotchas Effi, EspoCRM, etc.)
- Reglas del super agente y modo autónomo
- Convenciones de código

**Cuándo actualizar**: cuando se aprende algo nuevo que aplica a todo el proyecto (nuevo gotcha técnico, nueva regla de diseño, nueva convención). No actualizar por cada tarea.

**El MANIFESTO tiene un índice** en las primeras 15 líneas. Mantenerlo actualizado cuando se agrega una sección nueva.

---

## CONTEXTO_ACTIVO.md — el estado del sistema

Responde siempre: ¿qué está corriendo? ¿en qué trabajamos esta semana?

**Cuándo actualizar**: al terminar cualquier tarea significativa en cualquier módulo. Este es el archivo que más cambia.

**Estructura que debe mantener**:
1. Tabla de módulos activos (estado + prioridad)
2. Trabajo activo esta semana
3. Tabla de BDs (no cambia seguido)
4. Tabla de servicios (no cambia seguido)
5. Archivos clave globales

---

## contextos/*.md — contexto por módulo

Cada módulo activo tiene su archivo en `.agent/contextos/`. Se lee **solo** cuando se trabaja en ese módulo.

**Cuándo actualizar**: al terminar trabajo en el módulo. El contexto refleja el estado ACTUAL — no es un historial.

**Qué contiene**:
- Descripción del módulo y URL de acceso
- BD(s) que usa y tablas clave
- Scripts y endpoints relacionados
- Features implementadas y pendientes
- Gotchas específicos del módulo
- Bugs conocidos

### Ciclo de vida de un módulo

```
EN DESARROLLO → ACTIVO → ESTABLE → ARCHIVADO
```

- **En desarrollo**: aparece en trabajo activo de CONTEXTO_ACTIVO.md con prioridad Alta
- **Activo**: en tabla de módulos de CONTEXTO_ACTIVO.md, prioridad Normal o Alta
- **Estable**: en tabla de módulos con estado "Estable — sin trabajo activo". Skill disponible pero no se prioriza.
- **Archivado**: contexto movido a `contextos/archivados/`, removido de tabla de módulos activos. Skill puede quedar como referencia.

---

## CATALOGO_*.md — catálogos de referencia

Catálogos que no cambian frecuentemente pero se consultan seguido:

| Catálogo | Contenido | Cuándo actualizar |
|---|---|---|
| `CATALOGO_SCRIPTS.md` | Todos los scripts con comando exacto y parámetros | Al agregar/modificar un script |
| `CATALOGO_APIS.md` | APIs HTTP internas con endpoints y ejemplos | Al agregar/modificar un endpoint |
| `CATALOGO_TABLAS.md` | Tablas de todas las BDs con descripción de campos | Al agregar tablas o campos importantes |
| `CATALOGO_AGENTES.md` | Agentes IA (cloud + local) con modelos y costos | Al agregar/cambiar configuración de agente |
| `CATALOGO_VISTAS.md` | Páginas del ERP frontend con rutas Vue | Al agregar una nueva vista |
| `CATALOGO_REFERENCIAS.md` | Fuentes externas e internas (docs, papers, links) | Al agregar nueva referencia relevante |
| `catalogo-skills.md` | Índice de skills y manuales disponibles | Al crear un nuevo skill |

**Fuente única de verdad**: Si un dato aparece en dos lugares, hay duplicación peligrosa. Elegir un lugar canónico y hacer referencia desde el otro.

---

## Skills — guías especializadas

Los skills viven en `.claude/commands/` (sistema global de Claude Code, fuera del repo).

**Cuándo crear un skill**: cuando hay suficiente contexto específico de un dominio que justifica una guía dedicada (mínimo ~100 líneas de información útil).

**Skills actuales**:
- `effi-database` — BD effi_data (tablas, gotchas, queries)
- `effi-negocio` — lógica de negocio Effi (vigencia, consignación, canales)
- `ia-service` — servicio IA centralizado
- `tabla-vista` — diseño de tablas OsDataTable
- `menu-erp` — sidebar de navegación ERP
- `playwright-effi` — scripts de exportación Playwright
- `erp-frontend` — stack Vue+Quasar+Express del ERP
- `telegram-pipeline` — notificaciones Telegram del pipeline
- `espocrm-integracion` — integración EspoCRM ↔ Effi (ref. estable)

**Skills pendientes de crear**:
- `sistema-gestion` — módulo Tareas + Jornadas (módulo más activo)
- `inventario-fisico` — app de inventario físico

---

## planes/ — historial de decisiones

Los planes documentan decisiones de implementación. Son el registro histórico de POR QUÉ se construyó algo de determinada manera.

**Regla absoluta**: Los planes **NUNCA se borran**.
- En construcción → `.agent/planes/actuales/`
- Completado → mover a `.agent/planes/completados/` y marcar `Estado: Completado` al inicio del archivo
- Formato de nombre: `PLAN_NOMBRE_YYYY-MM-DD.md`

---

## memory/ — archivos topic de Claude

Los archivos en `memory/` son cargados por Claude Code en cada sesión. Organizar por tipo:

| Prefijo | Tipo | Cuándo usar |
|---|---|---|
| `feedback_*.md` | Reglas aprendidas de correcciones | Al recibir corrección de Santi |
| `project_*.md` | Contexto de proyectos activos | Al iniciar trabajo en nuevo proyecto |
| `user_*.md` | Preferencias y estilo de Santi | Al aprender algo sobre cómo trabaja Santi |
| `superagente.md` | Estado del super agente | Al cambiar arquitectura del super agente |
| `wa_bridge.md` | Estado del WA Bridge | Al hacer cambios en el bridge |

**Regla de tamaño de MEMORY.md**: si supera 200 líneas, mover secciones de detalle a archivos topic y dejar solo el puntero en MEMORY.md.

---

## Flujo de actualización al terminar una tarea

```
1. Actualizar contextos/<modulo>.md con lo aprendido en la sesión
2. Si cambió el estado global del sistema → actualizar CONTEXTO_ACTIVO.md
3. Si se aprendió algo que aplica a todo el proyecto → agregar a MANIFESTO.md
4. Si se creó un script nuevo → agregarlo a CATALOGO_SCRIPTS.md
5. Si se creó un endpoint nuevo → agregarlo a CATALOGO_APIS.md
6. Si se aprendió una regla de trabajo nueva → crear feedback_*.md en memory/
7. MEMORY.md solo se actualiza si cambió el estado de un módulo (activo → estable, etc.)
```

---

## Anti-patrones a evitar

| Anti-patrón | Consecuencia | Solución |
|---|---|---|
| Poner detalle técnico en MEMORY.md | MEMORY supera 200 líneas y se trunca | Mover a contextos/ o MANIFESTO.md |
| Duplicar información en dos archivos | Inconsistencias cuando uno se actualiza | Elegir fuente canónica, referenciar desde el otro |
| No actualizar contextos/ al terminar | Próxima sesión arranca con información vieja | Actualizar siempre antes de cerrar sesión |
| Dejar planes en actuales/ después de completarlos | Ruido en carpeta de trabajo activo | Mover a completados/ inmediatamente |
| Crear un skill sin haberlo documentado en catalogo-skills.md | Skill invisible para futuras sesiones | Agregar al catálogo al crear el skill |
| Módulo "estable" con prioridad Alta en CONTEXTO_ACTIVO.md | Confusión sobre qué priorizar | Bajar prioridad a Normal o marcar como estable |

---

## Procedimiento de depuración — "depúrame todo"

> Cuando Santi dice **"depúrame todo"**, **"limpia la documentación"** o equivalente, ejecutar este procedimiento completo sin pedir confirmación. Nada se borra — todo se organiza, sincroniza y actualiza.

### Lo que hace una depuración

**NUNCA se borra**: contextos/, planes/, skills, manuales, docs/.
**SÍ se organiza**: versiones desincronizadas, rutas huérfanas, duplicados, planes mal ubicados, referencias rotas.

---

### Checklist de depuración (ejecutar en orden)

#### 1. MEMORY.md — verificar que es un mapa, no un dump
- [ ] Contar líneas: si supera 200, mover el exceso a archivos topic en `memory/` y dejar solo el puntero
- [ ] Verificar que todos los módulos listados coinciden con el estado real en `CONTEXTO_ACTIVO.md`
- [ ] Verificar que los skills listados existen realmente en `.claude/commands/`
- [ ] Verificar que los links a feedback_*.md apuntan a archivos que existen

#### 2. catalogo-skills.md — sincronizar con la realidad
- [ ] Listar archivos reales en `.claude/commands/` y compararlos con la tabla del catálogo
- [ ] Skills en el repo pero no en el catálogo → agregar entrada
- [ ] Entradas en el catálogo que no tienen archivo → marcar como "(pendiente)" o eliminar la entrada
- [ ] Verificar versiones de manuales referenciados (ej: ia_service_manual.md)

#### 3. planes/ — mover completados a su lugar
- [ ] Revisar `.agent/planes/actuales/` — todo plan con `Estado: Completado` o `Estado: ✅` → mover a `completados/`
- [ ] Revisar `.agent/planes/completados/` — verificar que todos tienen `Estado: ✅ Completado` al inicio

#### 4. CATALOGO_SCRIPTS.md — verificar existencia de scripts
- [ ] Para cada script documentado en la sección de Orquestadores, verificar que el archivo existe en `scripts/`
- [ ] Si un script fue eliminado o renombrado → actualizar la entrada (no borrar, solo corregir)

#### 5. CATALOGO_VISTAS.md — verificar rutas activas
- [ ] Para cada ruta marcada como ✅, verificar que el componente Vue existe en el directorio correspondiente
- [ ] Rutas implementadas que no están en el catálogo → agregar

#### 6. contextos/*.md — actualizar fechas
- [ ] Para cada contexto, verificar que la fecha de actualización refleja el trabajo más reciente
- [ ] Si un módulo pasó de Activo a Estable (sin trabajo reciente >30 días) → proponer a Santi cambiar estado

#### 7. CONTEXTO_ACTIVO.md — limpiar trabajo pasado
- [ ] La sección "Trabajo activo esta semana" debe reflejar la semana real actual
- [ ] Trabajo completado hace más de 2 semanas → mover a la sección "Trabajo reciente" o eliminar de esa sección
- [ ] Verificar que todos los módulos de la tabla tienen su archivo de contexto

#### 8. docs/ — eliminar duplicados
- [ ] Verificar que no hay dos archivos con el mismo contenido (el diagnóstico de 2026-03-31 ya eliminó CATALOGO_AGENTES.md de docs/)
- [ ] Informes en `informes/` con más de 90 días → archivar en `informes/archivados/` (no borrar)

---

### Salida esperada al terminar una depuración

Al finalizar, reportar a Santi:

```
## Depuración completada — [fecha]

### Cambios realizados
- N planes movidos de actuales/ a completados/
- N entradas de catalogo-skills.md actualizadas
- N inconsistencias de MEMORY.md corregidas
- N rutas nuevas agregadas a CATALOGO_VISTAS.md
- ...

### Estado post-depuración
- MEMORY.md: N líneas (< 200 ✅ / > 200 ⚠️)
- planes/actuales/: N archivos activos
- Skills: N skills en .claude/commands/
- Sin duplicados detectados

### Sin cambios (todo OK)
- [lista de archivos que se revisaron y están bien]
```

---

### Qué NO hace la depuración

- No modifica archivos Python, JS ni de configuración del sistema
- No elimina ningún contexto, plan, skill ni manual
- No cambia el estado de módulos activos (solo propone si detecta inactividad >30 días)
- No toca `.env` ni credenciales
- No modifica el código fuente del proyecto
