# Reglas de Diseño — App Gestión OS

> Este documento es la ley de implementación. Antes de crear cualquier componente o campo, leer y aplicar.

---

## R01 — Consistencia de campos: cada tipo de campo siempre igual

**Regla**: El mismo tipo de campo debe implementarse con el mismo componente en toda la app. No hay dos formas de implementar lo mismo.

| Tipo de campo | Componente a usar | ¿Dónde está? |
|---|---|---|
| Selección de 1 proyecto | `<ProyectoSelector>` | `components/ProyectoSelector.vue` |
| Selección de etiquetas (multi) | `<EtiquetasSelector>` | `components/EtiquetasSelector.vue` |
| Selección de responsables (multi) | `<ResponsablesSelector>` | `components/ResponsablesSelector.vue` |
| Estado de tarea | `<EstadoBadge>` + click para ciclar, o `<select>` | `components/EstadoBadge.vue` |
| Prioridad | 4 chips pill (Urgente/Alta/Media/Baja) con color activo | Inline en cada form/panel |
| Fecha | `<input type="date">` con estilo `.input-field` | Global — ver R04 |

**Consecuencia**: si ya existe un componente para un campo, NUNCA reimplementarlo inline. Siempre importar y reutilizar.

---

## R02 — Dropdowns siempre con Teleport + posición fija

**Regla**: Todo dropdown que abra desde un elemento debe usar `<Teleport to="body">` con `position: fixed` calculado mediante `getBoundingClientRect()`.

**Motivo**: evitar clipping por `overflow: hidden` en contenedores padre.

**Patrón estándar** (ya en ProyectoSelector, EtiquetasSelector, ResponsablesSelector):
```javascript
function calcularPosicion() {
  const rect = wrapRef.value.getBoundingClientRect()
  const goUp = (window.innerHeight - rect.bottom) < 220 && rect.top > 220
  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 200)}px`,
    zIndex: 9999,
    ...(goUp ? { bottom: `${window.innerHeight - rect.top}px` } : { top: `${rect.bottom + 4}px` })
  }
}
```

---

## R03 — Dropdowns multi-select: patrón chips + botón agregar

**Regla**: Los campos de selección múltiple muestran:
1. Chips de los items seleccionados (con botón ×  para quitar)
2. Botón dashed "Agregar [cosa]" que abre el dropdown
3. Dropdown con búsqueda + lista scrollable + opción crear

**No usar**: `<select multiple>`, checkboxes en columna, o chips siempre visibles sin botón agregar.

---

## R04 — Icono de calendario en dark mode

**Regla**: Todo `<input type="date|time|datetime-local">` necesita que el ícono nativo sea visible en dark mode.

**Solución ya aplicada globalmente en `app.scss`** — no requiere CSS extra en componentes:
```css
input[type="date"]::-webkit-calendar-picker-indicator { filter: invert(0.7); opacity: 0.7; }
[data-theme="light"] input[type="date"]::-webkit-calendar-picker-indicator { filter: none; opacity: 0.6; }
```

---

## R05 — Prioridad siempre como chips, nunca como select

**Regla**: El campo prioridad se muestra como 4 chips pill horizontales: Urgente / Alta / Media / Baja.

**Colores fijos**:
| Prioridad | Color |
|---|---|
| Urgente | `#ef4444` |
| Alta | `#f59e0b` |
| Media | `#6b7280` |
| Baja | `#374151` |

**Chip activo**: `background: color+'22'`, `borderColor: color`, `color: color`.

---

## R06 — Proyectos activos en selectores de tareas

**Regla**: Al cargar proyectos para asociar a una tarea, solo traer proyectos con `estado = 'Activo'`. No mostrar proyectos archivados ni completados.

**Endpoint correcto**: `GET /api/gestion/proyectos?estado=Activo`

---

## R07 — Estados de proyecto

| Estado | Significado |
|---|---|
| `Activo` | En curso, aparece en listas y selectores |
| `Archivado` | Pausado, no aparece en selectores de tareas |
| `Completado` | Finalizado, guarda `fecha_finalizacion_real` |

La acción "Completar" en el menú ⋮ del proyecto establece `estado='Completado'` + `fecha_finalizacion_real = fecha actual`.

---

## R08 — Endpoints a usar (NO inventar)

| Recurso | Endpoint correcto |
|---|---|
| Usuarios de la empresa | `GET /api/gestion/usuarios` |
| Etiquetas | `GET /api/gestion/etiquetas` |
| Proyectos activos | `GET /api/gestion/proyectos?estado=Activo` |
| Tareas | `GET /api/gestion/tareas` |

**NUNCA usar** `/api/usuarios` (no existe) ni ningún endpoint sin el prefijo `/api/gestion/`.

---

## R09 — Acento de color

**El acento de esta app es verde**: `#00C853` — NO el violeta `#5E6AD2` del ERP de menú.oscomunidad.com.

Variable CSS: `--accent: #00C853`

---

## R10 — Dark mode primero

La app es dark-first. Variables CSS controladas por `data-theme="dark|light"` en el `<html>`.
Siempre probar el diseño en dark antes que en light.
