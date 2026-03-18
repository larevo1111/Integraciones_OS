# Plan: UX Filtros + Subtareas — OS Gestión
**Creado**: 2026-03-17  
**Estado**: ✅ COMPLETADO (2026-03-17)  
**Al iniciar sesión**: leer este archivo y retomar donde dice `→ PENDIENTE`

---

## Contexto
App: gestion.oscomunidad.com (Puerto 9300, SPA Quasar + Express)  
Archivos clave:
- Frontend: `sistema_gestion/app/src/pages/TareasPage.vue`
- Items: `sistema_gestion/app/src/components/TareaItem.vue`
- EstadoBadge: `sistema_gestion/app/src/components/EstadoBadge.vue`
- Estilos globales: `sistema_gestion/app/src/css/app.scss`
- Backend: `sistema_gestion/api/server.js` (línea ~348 para filtros GET /api/gestion/tareas)

---

## FASE 1 — Fixes menores

### [✅ HECHO] 1.1 Badge subtareas sin chip (solo texto)
- `.subtareas-badge`: quitar `border` y `background`, dejar solo texto `0/2` limpio
- Mantener hover accent-color para indicar que es clickeable
- **Archivo**: TareaItem.vue → `.subtareas-badge` scoped CSS

### [✅ HECHO] 1.2 Círculo subtarea más pequeño
- `.is-subtarea .estado-circle`: reducir de 14px → 11px (diferenciador visual padre/hijo)
- **Archivo**: app.scss → sección `.estado-circle`

### [✅ HECHO] 1.3 Quick insert subtarea — UX simplificada
- Comportamiento actual: input + botón "Cancelar" + botón "Agregar"
- Comportamiento nuevo:
  - Solo `×` a la derecha para cancelar
  - Enter → guarda (ya funciona)
  - `@blur` → guarda si hay texto (si no, cancela)
- **Archivo**: TareasPage.vue → `div.subtarea-quickadd`

---

## FASE 2 — Filtro Personalizado

### [✅ HECHO] 2.1 Quitar chip "Mis tareas" de la barra
- En FILTROS array (TareasPage.vue línea ~394): eliminar `{ key: 'mias', label: 'Mis tareas' }`
- El filtro "Mis Tareas" YA viene dado por el contexto de la página

### [✅ HECHO] 2.2 Agregar chip "Personalizado" después de "Todas"
- Agregar `{ key: 'personalizado', label: 'Personalizado' }` en FILTROS
- Al hacer click: abrir popup FiltroPersonalizado

### [✅ HECHO] 2.3 Crear componente FiltroPersonalizado.vue
Popup con diseño del sistema (dark, var(--bg-elevated), bordes sutiles):
```
┌─────────────────────────────────┐
│  Filtro personalizado        ×  │
├─────────────────────────────────┤
│  Fechas                         │
│  Desde [__/__/____]  Hasta [__] │
│                                 │
│  Prioridad                      │
│  [○ Urgente] [○ Alta] [○ Media] [○ Baja] │
│                                 │
│  Categoría                      │
│  [● Cat1] [● Cat2] [● Cat3]     │
│                                 │
│  Etiquetas                      │
│  [tag1] [tag2] [tag3]           │
│                                 │
│  Proyecto                       │
│  [dropdown selector]            │
│                                 │
│           [Limpiar]  [Aplicar]  │
└─────────────────────────────────┘
```
- Posición: dropdown debajo del chip "Personalizado", alineado a la derecha
- En mobile: ocupa todo el ancho, sticky bottom
- Props: categorias, etiquetas, proyectos
- Emite: `@aplicar` con objeto filtros, `@cerrar`

### [✅ HECHO] 2.4 Actualizar backend (server.js)
Agregar soporte en GET /api/gestion/tareas:
- `fecha_desde` → `t.fecha_limite >= ?`
- `fecha_hasta` → `t.fecha_limite <= ?`
- `prioridades` → múltiple: `t.prioridad IN (?)`  (comma-separated)
- `categorias` → múltiple: `t.categoria_id IN (?)` (comma-separated)
- `etiquetas` → múltiple: JOIN g_etiquetas_tareas (comma-separated ids)
- `proyecto_id` ya existe (single)

### [✅ HECHO] 2.5 Actualizar TareasPage.vue
- Estado: `filtroPersonalizado = { fecha_desde, fecha_hasta, prioridades[], categorias[], etiquetas[], proyecto_id }`
- Cuando `filtroActivo === 'personalizado'`: enviar params del filtro personalizado a la API
- Chip "Personalizado" active cuando hay filtros activos (mostrar count)
- Popup controlado con `mostrarFiltroPersonalizado = ref(false)`

---

## FASE 3 — QA con subagente Playwright

### [✅ HECHO] 3.1 Crear 20-30 tareas de prueba
QA subagente creó 25 tareas + 6 subtareas vía API.
**Nota**: todas creadas sin `fecha_limite` — correcto que no aparezcan en filtros de fecha.

### [✅ HECHO] 3.2 QA Web
QA confirmado (2026-03-17):
- Lista de tareas: chips, alineación, badge 0/N → OK
- Filtros Hoy/Mañana/Semana: muestran solo tareas CON fecha asignada → correcto
- "Todas": muestra todas → OK
- FiltroPersonalizado popup: abre y aplica → OK
- Panel tarea: T.real y T.estimado en filas separadas → OK
- Subtareas: expandibles → OK
- **"Bug" falso reportado**: filtros no mostraban tareas creadas por QA → NO es bug, las tareas se crearon sin fecha_limite (NULL)

### [✅ HECHO] 3.3 QA Mobile
Verificado visualmente con viewport mobile. FiltroPersonalizado en bottom sheet mobile → OK

### [✅ HECHO] 3.4 Post-QA
Sin correcciones necesarias. App estable.

---

## Build y Deploy
```bash
cd sistema_gestion/app && npx quasar build
sudo systemctl restart os-gestion
```

## API para crear tareas de prueba (ejemplo)
```js
const api = (path, opts={}) => fetch(`http://localhost:9300${path}`, { 
  headers: { 'Authorization': 'Bearer TOKEN', 'Content-Type': 'application/json' },
  ...opts 
})
```

