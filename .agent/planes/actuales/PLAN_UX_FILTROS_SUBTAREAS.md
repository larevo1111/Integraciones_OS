# Plan: UX Filtros + Subtareas — OS Gestión
**Creado**: 2026-03-17  
**Estado**: EN EJECUCIÓN  
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

### [→ PENDIENTE] 3.1 Crear 20-30 tareas de prueba variadas
Script Node.js directo a la API local para crear:
- 5 tareas "Hoy" diferentes categorías y prioridades
- 5 tareas "Mañana" 
- 5 tareas "Esta semana" con etiquetas
- 3 tareas con subtareas (2-3 subtareas cada una)
- 5 tareas sin fecha
- 3 tareas completadas
- Proyectos: al menos 2 con tareas
- Descripción variada para tener datos realistas

### [→ PENDIENTE] 3.2 QA Web — screenshot completo
Subagente Playwright verifica:
- [ ] Lista de tareas: chips, alineación, badge 0/N
- [ ] Filtros: Hoy, Mañana, Ayer, Semana, Todas, Personalizado
- [ ] Filtro personalizado: abrir, seleccionar, aplicar, limpiar
- [ ] Panel tarea: todos los campos, cronómetro, tiempos
- [ ] Subtareas: expandir, agregar (quick insert)
- [ ] QuickAdd desktop: agregar tarea con categoría y proyecto
- [ ] Completar tarea: popover tiempo

### [→ PENDIENTE] 3.3 QA Mobile — emular iPhone 375px
Subagente verifica:
- [ ] Lista: filas correctas, chips visibles
- [ ] Bottom sheet panel tarea
- [ ] FAB + TareaForm mobile
- [ ] Filtros: scroll horizontal
- [ ] Subtareas en mobile

### [→ PENDIENTE] 3.4 Correcciones post-QA
Si se detectan fallos → corregirlos sin romper lo que funciona

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

