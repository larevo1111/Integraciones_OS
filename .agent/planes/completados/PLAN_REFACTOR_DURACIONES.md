# Plan: Refactor 5S del modelo de duraciones de tareas

**Fecha**: 2026-04-08
**Autor**: Santi + Claude (sesión)
**Estado**: Pendiente OK final de Santi

## Por qué

El modelo actual de tiempos en `g_tareas` está fragmentado: `tiempo_real_min` (en minutos), `crono_acumulado_seg` (en segundos), `crono_inicio` (timestamp), más campos calculados ad-hoc en queries y frontend. Hay queries que aún tocan la tabla legacy `g_tarea_tiempo` y devuelven 0/NULL siempre. El componente `CronoDisplay.vue` decide visibilidad por reglas inconsistentes y los caminos de "cambiar a En Progreso" están duplicados (3 funciones distintas más un parche legacy en `TareasPage.vue` líneas 1500-1508 que sobrescribe la tarea con campos viejos).

Esto genera bugs visibles intermitentes (caso real: tarea de Deivy "Producción chocolate granulado" no mostraba el cronómetro corriendo aunque estaba En Progreso).

**Solución 5S**: una sola unidad (segundos), un solo formato (HH:MM:SS), una función por acción, un componente para mostrar el cronómetro.

---

## Modelo final

### Backend / BD — `g_tareas`

3 columnas para duración, todas en segundos (INT):

| Columna | Qué guarda |
|---|---|
| `duracion_usuario_seg` | Lo que el usuario confirmó en el modal al completar. En tareas En Progreso, siempre igual a `duracion_cronometro_seg`. |
| `duracion_cronometro_seg` | Lo que cuenta el cronómetro (acumulado real). Se actualiza en cada pausa o cambio de estado. |
| `duracion_sistema_seg` | `fecha_fin_real - fecha_inicio_real`, en segundos. Calculado y guardado al completar/cancelar. |

Más un timestamp interno (no es duración):

| Columna | Qué guarda |
|---|---|
| `crono_inicio` (DATETIME) | Cuándo arrancó el contador en curso. NULL cuando está pausado o la tarea no está En Progreso. |

**Eliminar** las columnas viejas:
- `tiempo_real_min` (se renombra a `duracion_usuario_seg` y se multiplica por 60)
- `crono_acumulado_seg` (se renombra a `duracion_cronometro_seg`)

**No tocar**:
- `fecha_inicio_real`, `fecha_fin_real` (siguen siendo timestamps de auditoría)

### Reglas de oro

1. **En tareas En Progreso**: `duracion_usuario_seg = duracion_cronometro_seg` SIEMPRE. Cualquier UPDATE actualiza ambas.
2. **Al pasar a Pendiente**: las 3 duraciones a 0, `crono_inicio = NULL`.
3. **Al pasar a En Progreso**: `crono_inicio = NOW()`. Las duraciones quedan como estaban (si vienen de Pendiente, en 0; si vienen de pausa, con su valor).
4. **Al pausar**: `crono_inicio = NULL`, se vuelca el delta a `duracion_cronometro_seg`, `duracion_usuario_seg = duracion_cronometro_seg`. **NO cambia el estado** — la tarea sigue En Progreso.
5. **Al pasar a Completada**: modal obligatorio. Usuario confirma `duracion_usuario_seg` (puede ser distinta del crono). Se calcula `duracion_sistema_seg = fecha_fin_real - fecha_inicio_real`. `crono_inicio = NULL`.
6. **Al pasar a Cancelada**: `duracion_usuario_seg` queda con su valor actual (ya era igual al crono). `duracion_sistema_seg` se calcula. `crono_inicio = NULL`.

---

## Endpoints (backend)

Una función por acción. Eliminar los endpoints legacy `/iniciar`, `/detener`, `/reiniciar-tiempo` y reemplazar por:

| Endpoint | Acción | Body |
|---|---|---|
| `POST /api/gestion/tareas/:id/iniciar` | Pone estado=`En Progreso`, `crono_inicio=NOW()` (idempotente). Si la tarea estaba en Pendiente, también `fecha_inicio_real=NOW()`. | — |
| `POST /api/gestion/tareas/:id/pausar` | Vuelca delta a `duracion_cronometro_seg` y `duracion_usuario_seg`. `crono_inicio=NULL`. **Estado no cambia.** | — |
| `POST /api/gestion/tareas/:id/cancelar` | Estado=`Cancelada`. `fecha_fin_real=NOW()`. Vuelca crono. `duracion_sistema_seg = (fin - inicio)`. `crono_inicio=NULL`. | — |
| `POST /api/gestion/tareas/:id/completar` | Estado=`Completada`. `fecha_fin_real=NOW()`. Recibe `duracion_usuario_seg` del modal. `duracion_cronometro_seg += delta`. `duracion_sistema_seg = (fin - inicio)`. `crono_inicio=NULL`. | `{ duracion_usuario_seg }` |
| `POST /api/gestion/tareas/:id/revertir` | Vuelve a Pendiente. Las 3 duraciones a 0. `fecha_inicio_real=NULL`, `fecha_fin_real=NULL`, `crono_inicio=NULL`. | — |
| `PUT /api/gestion/tareas/:id` | Edición de campos no relacionados con estado/cronómetro: titulo, prioridad, categoría, responsables, etiquetas, fechas estimadas, notas. **Si llega `estado` en el body, se ignora con warning.** | normales |

**Cambios en `PUT /api/gestion/tareas/:id`**:
- Quitar el bloque `if (estado === 'En Progreso')`, `if (estado === 'Completada')`, etc. Esa lógica ahora vive en los endpoints específicos.
- El PUT solo edita campos directos.
- Si recibe `estado`, log warning y no procesa (compatibilidad temporal).

**Eliminar**:
- Las queries que usan `g_tarea_tiempo` (líneas ~596 y ~680 de `server.js`) — esa tabla está vacía y devuelve 0/NULL siempre. Reemplazar por `(t.crono_inicio IS NOT NULL) AS cronometro_activo`, `t.crono_inicio AS cronometro_inicio` directamente.

---

## Frontend

### Funciones únicas

En `src/services/crono.js`:

```js
// La única función de formato. Todo HH:MM:SS.
export function formatHHMMSS(seg) {
  if (!seg || seg < 0) seg = 0
  const h = Math.floor(seg / 3600)
  const m = Math.floor((seg % 3600) / 60)
  const s = seg % 60
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}

// Para tareas En Progreso, calcula la duración usuario en vivo (= duración cronómetro)
export function calcDuracionUsuarioVivo(tarea) {
  if (!tarea) return 0
  let total = tarea.duracion_cronometro_seg || 0
  if (tarea.crono_inicio) {
    const ini = parseInicio(tarea.crono_inicio)
    if (ini) total += Math.max(0, Math.floor((Date.now() - ini.getTime()) / 1000))
  }
  return total
}

// Para Más campos: duración sistema en vivo (NOW - fecha_inicio_real) si en progreso,
// o el valor guardado si completada/cancelada
export function calcDuracionSistema(tarea) {
  if (!tarea) return 0
  if (tarea.duracion_sistema_seg) return tarea.duracion_sistema_seg
  if (!tarea.fecha_inicio_real) return 0
  const ini = parseInicio(tarea.fecha_inicio_real)
  return Math.max(0, Math.floor((Date.now() - ini.getTime()) / 1000))
}
```

### Componente `CronoDisplay.vue`

**Reescritura completa, ultra simple**:

```vue
<template>
  <span v-if="visible" class="crono-display" :class="{ pausado: !tarea.crono_inicio }">
    <span v-if="tarea.crono_inicio" class="crono-display-dot" />
    {{ texto }}
  </span>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { formatHHMMSS, calcDuracionUsuarioVivo } from 'src/services/crono'

const props = defineProps({ tarea: { type: Object, required: true } })

// Una sola regla: visible si la tarea NO es Pendiente
const visible = computed(() => {
  return props.tarea && props.tarea.estado !== 'Pendiente'
})

// Una sola regla: muestra duracion_usuario_seg
// (en En Progreso se calcula en vivo desde crono, en Completada/Cancelada usa el valor guardado)
const segundos = ref(0)
function actualizar() {
  const t = props.tarea
  if (t.estado === 'En Progreso') {
    segundos.value = calcDuracionUsuarioVivo(t)
  } else {
    segundos.value = t.duracion_usuario_seg || 0
  }
}
const texto = computed(() => formatHHMMSS(segundos.value))

let interval = null
function start() { stop(); actualizar(); interval = setInterval(actualizar, 1000) }
function stop() { if (interval) { clearInterval(interval); interval = null } }

onMounted(() => {
  actualizar()
  if (props.tarea.estado === 'En Progreso' && props.tarea.crono_inicio) start()
})
onUnmounted(stop)

watch(() => [props.tarea.estado, props.tarea.crono_inicio, props.tarea.duracion_usuario_seg], () => {
  actualizar()
  if (props.tarea.estado === 'En Progreso' && props.tarea.crono_inicio) start()
  else stop()
})
</script>
```

### Componente `Cronometro.vue` (botones play/pausa)

**Cambios**:
- Solo visible si `tarea.estado === 'En Progreso'`
- Botón play (play_arrow): aparece cuando `crono_inicio === null` (pausado). Click → llama `iniciarTarea` (que también es idempotente, solo reanuda el contador).
- Botón pausa (pause): aparece cuando `crono_inicio !== null`. Click → llama `pausarTarea`. NO cambia estado.
- Botón reset (restart_alt): se mantiene como está, solo en Modo edición/admin si querés conservarlo. (Default: ocultar).

```vue
<template>
  <div v-if="visible" class="crono-controls">
    <button class="crono-btn" :class="{ activo }" @click="toggle"
      :title="activo ? 'Pausar contador' : 'Reanudar contador'">
      <span class="material-icons" style="font-size:12px">{{ activo ? 'pause' : 'play_arrow' }}</span>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({ tareaId: Number, tarea: Object })
const emit = defineEmits(['update'])

const visible = computed(() => props.tarea?.estado === 'En Progreso')
const activo = computed(() => !!props.tarea?.crono_inicio)

async function toggle() {
  const endpoint = activo.value ? 'pausar' : 'iniciar'
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/${endpoint}`, { method: 'POST' })
    emit('update', data.tarea)
  } catch (e) { console.error(e) }
}
</script>
```

### `TareasPage.vue` y `TareaItem.vue`

**Cambios**:
- **Eliminar las líneas 1500-1508** (el código legacy que sobrescribe la tarea con `cronometro_activo`/`cronometro_inicio` → ese era el bug de Deivy).
- Una sola función `cambiarEstado(tarea, nuevoEstado)`:
  - Si `nuevoEstado === 'Completada'` → abre modal
  - Si no → llama al endpoint correspondiente: `iniciarTarea`, `cancelarTarea`, `revertirAPendiente`
  - El check de la lista, el chip del panel, el `EstadoBadge` y el multiselect llaman a esta misma función.

### `TareaPanel.vue` — sección "Más campos"

Agregar **siempre** (no condicional al estado):

```
Duración usuario:    HH:MM:SS
Duración cronómetro: HH:MM:SS
Duración sistema:    HH:MM:SS
```

En Pendiente las 3 son `00:00:00`. En Progreso usuario y cronómetro son iguales. En Completada/Cancelada pueden divergir.

### `MultiActionBar.vue`

Filtrar las opciones del menú "Estado" para que solo muestre:
- Pendiente
- En Progreso
- Cancelada

**No** muestra `Completada` (porque exige modal individual).

---

## Migración SQL

**Backup primero**:
```bash
ssh -i ~/.ssh/sos_erp -p 65002 u768061575@109.106.250.195 \
  "mysqldump -u u768061575_os_gestion -pEpist2487. u768061575_os_gestion g_tareas" \
  > /home/osserver/Proyectos_Antigravity/backups/u768061575_os_gestion/$(date +%Y-%m-%d_%H%M%S)_g_tareas_pre_refactor.sql
```

**Migración**:
```sql
-- 1. Agregar nuevas columnas (con valores temporales)
ALTER TABLE g_tareas
  ADD COLUMN duracion_usuario_seg    INT NOT NULL DEFAULT 0 AFTER tiempo_real_min,
  ADD COLUMN duracion_cronometro_seg INT NOT NULL DEFAULT 0 AFTER duracion_usuario_seg,
  ADD COLUMN duracion_sistema_seg    INT NOT NULL DEFAULT 0 AFTER duracion_cronometro_seg;

-- 2. Migrar datos
UPDATE g_tareas SET
  duracion_usuario_seg    = COALESCE(tiempo_real_min, 0) * 60,
  duracion_cronometro_seg = COALESCE(crono_acumulado_seg, 0),
  duracion_sistema_seg    = CASE
    WHEN fecha_inicio_real IS NOT NULL AND fecha_fin_real IS NOT NULL
      THEN TIMESTAMPDIFF(SECOND, fecha_inicio_real, fecha_fin_real)
    ELSE 0
  END;

-- 3. Eliminar columnas viejas
ALTER TABLE g_tareas
  DROP COLUMN tiempo_real_min,
  DROP COLUMN crono_acumulado_seg;
```

**Riesgo**: el backend en producción no debe estar tocando `tiempo_real_min` ni `crono_acumulado_seg` mientras se hace la migración. Estrategia: deploy del nuevo backend + restart del servicio + migración SQL en ese mismo momento (downtime de ~30 segundos).

---

## Verificación con Chrome DevTools MCP

Antes del commit, probar en móvil (414x800) y desktop (1366x768):

1. Tarea Pendiente → cronómetro NO se ve, botones play/pausa NO se ven ✓
2. Click en check → pasa a En Progreso → arranca contador → muestra `00:00:00` que crece ✓
3. Verificar mismo valor en lista y en panel (al lado del play) ✓
4. Pausar → contador se congela, botón cambia a play ✓
5. Reanudar → contador sigue desde donde estaba ✓
6. Abrir Más campos → ver las 3 duraciones (usuario y crono iguales, sistema = NOW - inicio) ✓
7. Click en check → modal de tiempo → confirmar valor → tarea pasa a Completada ✓
8. En Completada: cronómetro visible con valor del modal, botones play/pausa NO visibles ✓
9. Más campos en Completada: ver las 3 (puede ser que usuario ≠ crono si modificó en modal; sistema = fin - inicio) ✓
10. Multiselect → elegir 2 tareas → menú Estado → verificar que NO aparece "Completada", SÍ aparece "Cancelada" ✓
11. Cancelar masivamente → tareas pasan a Cancelada con su valor actual ✓
12. Revertir tarea Completada a Pendiente → las 3 duraciones a 0, todo limpio ✓

---

## Pasos de ejecución

1. **Backup** de `g_tareas` en Hostinger
2. **Migración SQL** (las 3 sentencias ALTER + UPDATE)
3. **Backend** (`server.js`):
   - Nuevos endpoints `/iniciar`, `/pausar`, `/cancelar`, `/completar`, `/revertir`
   - Eliminar lógica de estado en `PUT /tareas/:id`
   - Eliminar queries con `g_tarea_tiempo`
   - Cambiar SELECTs de `tiempo_real_min` y `crono_acumulado_seg` por las nuevas
4. **Frontend**:
   - `crono.js`: nueva función `formatHHMMSS`, `calcDuracionUsuarioVivo`, `calcDuracionSistema`
   - `CronoDisplay.vue`: reescrito según el modelo
   - `Cronometro.vue`: simplificado, visible solo en En Progreso
   - `TareasPage.vue`: eliminar líneas 1500-1508 (el bug de Deivy), unificar `cambiarEstado`
   - `TareaItem.vue`: cambia el `cambiarEstado` para llamar a la función única
   - `TareaPanel.vue`: agregar las 3 duraciones en "Más campos"
   - `MultiActionBar.vue`: filtrar opciones de Estado
5. **Build, deploy, restart** del servicio
6. **Verificar** los 12 puntos del checklist con Chrome DevTools MCP
7. **Commit único** con mensaje claro
8. **Mover este plan a `.agent/planes/completados/`** al terminar

---

## Lo que NO se toca

- `crono_inicio` (DATETIME) sigue existiendo como timestamp interno
- `fecha_inicio_real`, `fecha_fin_real` sin cambios
- Tabla `g_tarea_tiempo` queda en BD pero ya no se consulta (eventualmente se puede DROPear)
- Endpoints sin relación con duraciones (`/tareas`, `/tareas/:id` GET, `/etiquetas`, etc.)

---

## Estimación de impacto

- **Líneas afectadas**: ~300-400 entre backend y frontend
- **Commits**: 1 solo (los cambios son interdependientes, dividir rompe consistencia)
- **Downtime**: ~30 segundos durante el restart del servicio + migración
- **Riesgo de pérdida de datos**: bajo si se hace el backup primero
- **Reversibilidad**: alta — el backup permite restaurar la tabla, el código se revierte con git
