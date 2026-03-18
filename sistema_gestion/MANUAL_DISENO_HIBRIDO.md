# Manual de Diseño — Aplicaciones Híbridas OS (Web + Mobile)

> **Versión**: 1.2 — Actualizado 2026-03-18 con CategoriaSelector, TareaPanel completo, Cronómetro fix, FiltroPersonalizado.
> **Versión**: 1.0 — Documentado 2026-03-16 desde la sesión de construcción del Sistema Gestión OS.
> **Base de referencia**: TickTick (aplicación de tareas) + Linear.app (design system del ERP OS).
> **Aplicable a**: Sistema Gestión OS (`gestion.oscomunidad.com`) y cualquier app híbrida futura OS.

---

## 0. Principios del sistema de diseño

### 0.1 Dark mode first
- El tema dark es el predeterminado. El toggle dark/light se guarda en `g_usuarios_config.tema`.
- Variables CSS de tema en `app.scss` — se cambian con `document.documentElement.setAttribute('data-theme', 'light')`.
- **Nunca** hardcodear colores hex en componentes — siempre usar variables CSS.

### 0.2 Acento verde OS (≠ ERP)
El ERP usa violeta `#5E6AD2`. El Sistema Gestión usa **verde OS** `#00C853`.

```css
/* Variables de acento — Sistema Gestión (diferentes al ERP) */
--accent:        #00C853;
--accent-hover:  #00E060;
--accent-active: #00B048;
--accent-muted:  rgba(0, 200, 83, 0.12);
--accent-border: rgba(0, 200, 83, 0.35);
--text-link:     #00C853;
--border-focus:  #00C853;
```

### 0.3 Densidad alta (TickTick-style)
- Texto base: 13–14px en app.
- Filas de lista: 44–48px de altura total.
- Formularios: inputs de 36px altura mínima, padding 7px 10px.
- Gaps entre elementos: 6–12px (nunca 16+).
- Sin fondos de color en filas normales — solo en hover/seleccionado.

### 0.4 Botón primario blanco (igual que Linear)
```css
.btn-primary {
  background: #fff;
  color: #111;
  font-weight: 600;
  /* Sin sombra, sin gradiente */
}
```

### 0.5 Fuente
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

---

## 1. Variables CSS — Referencia completa

Estas variables se definen en `app/src/css/app.scss` y deben cubrir ambos temas.

```css
/* ─── Fondos ─────────────────────────────────────────── */
--bg-base:       #0F0F10;   /* fondo raíz (más oscuro) */
--bg-surface:    #161618;   /* sidebar, cards */
--bg-modal:      #1C1C1E;   /* modales, dropdowns */
--bg-input:      #1E1E20;   /* inputs */
--bg-row-hover:  rgba(255,255,255,0.04);

/* ─── Texto ───────────────────────────────────────────── */
--text-primary:   rgba(255,255,255,0.92);
--text-secondary: rgba(255,255,255,0.55);
--text-tertiary:  rgba(255,255,255,0.32);

/* ─── Bordes ──────────────────────────────────────────── */
--border-subtle:  rgba(255,255,255,0.06);
--border-default: rgba(255,255,255,0.10);
--border-strong:  rgba(255,255,255,0.18);

/* ─── Acento verde OS ─────────────────────────────────── */
--accent:        #00C853;
--accent-hover:  #00E060;
--accent-active: #00B048;
--accent-muted:  rgba(0,200,83,0.12);
--accent-border: rgba(0,200,83,0.35);

/* ─── Sombras ─────────────────────────────────────────── */
--shadow-sm:  0 1px 3px rgba(0,0,0,0.5);
--shadow-md:  0 4px 12px rgba(0,0,0,0.4);
--shadow-lg:  0 8px 24px rgba(0,0,0,0.5);

/* ─── Radios ──────────────────────────────────────────── */
--radius-sm:  4px;
--radius-md:  6px;
--radius-lg:  10px;
--radius-xl:  14px;

/* ─── Tipografía ──────────────────────────────────────── */
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

---

## 2. Layout — Desktop vs Mobile

### 2.1 Desktop: sidebar fijo 240px

```
┌──────────────────────────────────────────────────────────────────┐
│ SIDEBAR 240px      │ TOPBAR + CONTENIDO PRINCIPAL                │
│ (position: fixed)  │                                              │
│                    │                                              │
│ ● Logo/App    [☀]  │ [Título de página]  [acciones]              │
│ ─────────────────  │ ─────────────────────────────────────────── │
│ Módulo 1           │ [Chips filtros scrolleables]                 │
│   ├─ Sub1          │ ─────────────────────────────────────────── │
│   └─ Sub2          │ [Contenido: lista / tabla / formulario]      │
│ Módulo 2           │                                              │
│                    │                                              │
│ [avatar] Usuario   │                                              │
└──────────────────────────────────────────────────────────────────┘
```

**CSS del sidebar:**
```css
.sidebar {
  position: fixed;
  top: 0; left: 0; bottom: 0;
  width: 240px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  z-index: 50;
}

.main-content {
  margin-left: 240px;
  min-height: 100vh;
  background: var(--bg-base);
}
```

### 2.2 Mobile: drawer + topbar hamburger

```
┌─────────────────────────────┐
│ ☰  Título de vista  [acciones] │  ← topbar fijo arriba
│ ─────────────────────────── │
│ [chip][chip][chip]>>>>>      │  ← chips scrolleables
│ ─────────────────────────── │
│ CONTENIDO                    │
│   lista / formulario         │
│                              │
│                         [+] │  ← FAB verde bottom-right
└─────────────────────────────┘
```

**CSS del topbar mobile:**
```css
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  height: 48px;
}
```

### 2.3 Detección desktop/mobile en Vue

```javascript
// En el setup() del componente
const isMobile = computed(() => window.innerWidth <= 768)
// O en el layout:
window.addEventListener('resize', () => { isDesktop.value = window.innerWidth > 768 })
```

---

## 3. Sidebar Desktop — Anatomía

```
┌────────────────────────────────┐
│ ● OS Gestión             [☀]  │  ← header: logo + toggle tema
│ ────────────────────────────  │
│ TAREAS                         │  ← grupo
│   📋 Mis tareas                │  ← item activo (accent left border)
│   👥 Equipo                    │
│ ────────────────────────────  │
│ CONOCIMIENTO                   │
│   ⚠  Dificultades              │
│   💡 Ideas                     │
│   ✓  Pendientes                │
│   📊 Informes                  │
│ ────────────────────────────  │
│ [foto] Santiago                │  ← footer: avatar + nombre usuario
│ ○ Origen Silvestre             │  ← empresa activa
└────────────────────────────────┘
```

**CSS items del sidebar:**
```css
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 16px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  margin-right: 8px;
  transition: background 80ms, color 80ms;
  border-left: 2px solid transparent;
}
.sidebar-item:hover {
  background: var(--bg-row-hover);
  color: var(--text-primary);
}
.sidebar-item.active {
  background: var(--accent-muted);
  color: var(--accent);
  border-left-color: var(--accent);
  font-weight: 500;
}
.sidebar-group-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 12px 16px 4px;
}
```

---

## 4. Lista de tareas — Estilo TickTick

### 4.1 Anatomía de una fila de tarea

```
[estado] [dot-cat] [título ......................] [prioridad] [responsable] [fecha]
  16px    8px        flex:1, truncado               ícono 14px   avatar 20px  texto 11px
```

**CSS de la fila:**
```css
.tarea-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 16px;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 60ms;
}
.tarea-row:hover { background: var(--bg-row-hover); }
.tarea-row.completada { opacity: 0.5; }
```

### 4.2 Estado (círculo Linear-style)

```css
.estado-circle {
  width: 16px; height: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--border-strong);
  flex-shrink: 0;
  cursor: pointer;
}
/* Pendiente: borde gris, fondo vacío */
/* En progreso: borde accent + relleno accent/4 */
/* Completada: fondo accent con checkmark */
/* Cancelada: X en rojo */
```

### 4.3 Dot de categoría (8px)

```css
.cat-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  /* background: color de la categoría (ej: #2979FF para Ventas) */
}
```

### 4.4 Grupo de categoría (header)

```css
.group-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 10px 16px 4px;
  border-left: 2px solid <color-categoria>;
  /* Solo el borde izquierdo tiene el color — nada más */
}
```

### 4.5 Badge de prioridad

```css
/* Solo ícono de barras, sin texto */
.priority-icon {
  font-size: 14px;
  flex-shrink: 0;
}
.priority-baja    { color: var(--text-tertiary); }
.priority-media   { color: #607D8B; }
.priority-alta    { color: #FF9800; }
.priority-urgente { color: #f44336; }
```

---

## 5. QuickAdd Inline — Desktop

Patrón TickTick: crear tarea directamente en la lista sin abrir modal.

### 5.1 Apariencia

```
┌────────────────────────────────────────────────────────┐
│ ○ [¿Qué hay que hacer?        ]  [cat▾][fecha▾][▲] [✓] │
│   categoría chip seleccionada                          │
└────────────────────────────────────────────────────────┘
```

### 5.2 Comportamiento
- Se activa al hacer clic en "+ Nueva tarea" en el topbar (desktop).
- Se inserta al inicio de la lista (por encima de los grupos).
- `Enter` → guarda la tarea y cierra el QuickAdd.
- `Escape` → cierra sin guardar.
- Al crear: la tarea aparece en la lista con animación fade-in.

### 5.3 Template Vue (simplificado)
```html
<div v-if="quickAddVisible" class="quick-add-row">
  <div class="estado-circle"></div>
  <input
    ref="quickRef"
    v-model="quickForm.titulo"
    class="quick-input"
    placeholder="¿Qué hay que hacer?"
    @keydown.enter.prevent="guardarQuick"
    @keydown.escape="cerrarQuick"
  />
  <!-- selector categoría chips -->
  <!-- selector fecha -->
  <!-- selector prioridad -->
  <button class="btn-quick-save" :disabled="!quickForm.titulo" @click="guardarQuick">
    <span class="material-icons">check</span>
  </button>
</div>
```

### 5.4 CSS
```css
.quick-add-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--bg-modal);
  border-bottom: 1px solid var(--border-default);
  animation: fadeIn 120ms ease;
}
.quick-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 14px;
  color: var(--text-primary);
  font-family: var(--font-sans);
}
.quick-input::placeholder { color: var(--text-tertiary); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; } }
```

---

## 6. TareaForm — Modal Desktop / Bottom Sheet Mobile

Mismo componente (`TareaForm.vue`) adapta su presentación según viewport.

### 6.1 Desktop: Modal centrado
```
┌────────────────────────────────────────────┐
│ Nueva tarea                            [✕] │  ← header
│ ──────────────────────────────────────── │
│ [Título de la tarea...               ]    │  ← input grande
│ ──────────────────────────────────────── │
│ Categoría                                 │
│ [● Ventas] [● Sistemas] [● Producción]... │  ← chips con dot de color
│ ──────────────────────────────────────── │
│ OP Effi (solo si es_produccion)           │
│ [🔧 Buscar OP o artículo...          ]    │  ← OpSelector
│ ──────────────────────────────────────── │
│ [📅 Fecha] [👤 Responsable] [↑ Prioridad] │  ← fila de 3
│ ──────────────────────────────────────── │
│ [Descripción (opcional)...]              │
│                                           │
│                     [Cancelar]  [Crear]  │  ← footer
└────────────────────────────────────────────┘
```

### 6.2 Mobile: Bottom Sheet
```
┌─────────────────────────────┐
│      ────────               │  ← handle bar (36px, border-radius)
│ Nueva tarea             [✕] │
│ ─────────────────────────── │
│ [Título...]                 │
│ [chips categoría]           │
│ [fecha][responsable][prio]  │
│ [descripción]               │
│ ─────────────────────────── │
│         [Cancelar] [Crear]  │
└─────────────────────────────┘
```

### 6.3 Implementación Teleport + Transition

```html
<Teleport to="body">
  <Transition :name="isMobile ? 'sheet' : 'modal'">
    <div v-if="modelValue" class="form-overlay" @click.self="cerrar">
      <div class="form-container" :class="isMobile ? 'is-sheet' : 'is-modal'">
        <div v-if="isMobile" class="sheet-handle"></div>
        <!-- contenido -->
      </div>
    </div>
  </Transition>
</Teleport>
```

### 6.4 CSS de transiciones

```css
/* Modal desktop */
.modal-enter-active, .modal-leave-active { transition: opacity 150ms; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .form-container { transition: transform 150ms, opacity 150ms; }
.modal-enter-from .form-container { transform: scale(0.97); opacity: 0; }

/* Bottom sheet mobile */
.sheet-enter-active, .sheet-leave-active { transition: opacity 200ms; }
.sheet-enter-from, .sheet-leave-to { opacity: 0; }
.sheet-enter-active .is-sheet { transition: transform 250ms cubic-bezier(0.32,0.72,0,1); }
.sheet-enter-from .is-sheet { transform: translateY(100%); }

/* Handle bar */
.sheet-handle {
  width: 36px; height: 4px;
  background: var(--border-strong);
  border-radius: 2px;
  margin: 10px auto 2px;
}

/* Bottom sheet — posicionamiento */
.is-sheet {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  border-radius: 16px 16px 0 0;
  max-height: 92vh;
  padding-bottom: env(safe-area-inset-bottom, 16px);
}
```

---

## 7. Category Chips — Selector de categoría

Patrón para seleccionar categoría en formularios. **No usar `<select>`** — usar chips visuales.

### 7.1 Apariencia

```
[● Ventas] [● Sistemas] [● Producción] [● Cartera]
              ↑ seleccionado (borde más oscuro, fondo sutil)
```

### 7.2 CSS

```css
.cat-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 20px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 80ms;
  font-family: var(--font-sans);
}
.cat-chip:hover {
  border-color: var(--border-default);
  color: var(--text-primary);
}
.cat-chip.selected {
  background: var(--bg-row-hover);
  border-color: var(--border-strong);
  color: var(--text-primary);
  font-weight: 500;
}
.cat-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  /* background: c.color (del objeto categoría) */
}
```

---

## 8. OpSelector — Autocomplete inteligente

Componente `OpSelector.vue` — busca OPs en Effi (zeffi_produccion_encabezados) con JOIN a artículos producidos.

### 8.1 Características
- Búsqueda con debounce 250ms por número de OP o nombre de artículo producido
- Solo muestra OPs `vigencia='Vigente' AND estado != 'Procesada'` (pendientes reales)
- Navegación por teclado: ↑↓ mueven foco, Enter selecciona, Escape cierra
- Al seleccionar: muestra "tag" (chip) con número OP + nombre artículo truncado
- Botón ✕ para limpiar la selección
- Click fuera → cierra el dropdown

### 8.2 Template simplificado

```html
<div class="op-selector" ref="wrapRef">
  <!-- Input trigger -->
  <div class="op-input-wrap" :class="{ abierto, 'tiene-valor': !!modelValue }">
    <span class="material-icons op-icon">precision_manufacturing</span>
    <input
      ref="inputRef"
      v-model="query"
      :placeholder="modelValue ? '' : 'Buscar OP o artículo...'"
      @focus="abrir"
      @input="buscar"
      @keydown.escape="cerrar"
      @keydown.down.prevent="moverFoco(1)"
      @keydown.up.prevent="moverFoco(-1)"
      @keydown.enter.prevent="seleccionar(resultados[focoIdx])"
    />
    <!-- Tag valor seleccionado -->
    <div v-if="modelValue && !abierto" class="op-tag">
      <span class="op-tag-num">{{ modelValue }}</span>
      <span class="op-tag-desc">{{ articuloSeleccionado }}</span>
      <button class="op-tag-clear" @click.stop="limpiar">
        <span class="material-icons" style="font-size:14px">close</span>
      </button>
    </div>
  </div>
  <!-- Dropdown -->
  <Transition name="opdrop">
    <div v-if="abierto" class="op-dropdown">
      <!-- items... -->
    </div>
  </Transition>
</div>
```

### 8.3 Errores conocidos y soluciones
- **`@keydown.arrow-down`** → NO funciona en Vue. Usar **`@keydown.down`**.
- **`:class="{ tiene-valor: ... }`** → Si la clave tiene guión, NECESITA comillas: `'tiene-valor'`.
- El endpoint `/api/gestion/ops` hace JOIN cross-table en la MISMA BD (os_integracion) — válido. No confundir con JOIN cross-DB.

### 8.4 Query SQL del endpoint

```sql
SELECT
  pe.id_orden,
  pe.estado,
  pe.vigencia,
  pe.fecha_inicial,
  pe.fecha_final,
  GROUP_CONCAT(DISTINCT ap.descripcion_articulo SEPARATOR ', ') AS articulos
FROM zeffi_produccion_encabezados pe
LEFT JOIN zeffi_articulos_producidos ap
  ON ap.id_orden = pe.id_orden AND ap.vigencia = 'Orden vigente'
WHERE pe.vigencia = 'Vigente'
  AND pe.estado != 'Procesada'
  AND (? = '' OR pe.id_orden LIKE ? OR ap.descripcion_articulo LIKE ?)
GROUP BY pe.id_orden
ORDER BY pe.fecha_final ASC
LIMIT 30
```

⚠️ **`ap.vigencia = 'Orden vigente'`** (no 'Vigente') — diferente entre encabezados y artículos.

---

## 9. FAB (Floating Action Button) — Mobile

```css
.fab {
  position: fixed;
  bottom: 24px; right: 20px;
  width: 52px; height: 52px;
  border-radius: 50%;
  background: var(--accent);
  color: #000;
  box-shadow: 0 4px 16px rgba(0,200,83,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 30;
  border: none;
  cursor: pointer;
  transition: background 100ms, transform 100ms;
}
.fab:hover { background: var(--accent-hover); transform: scale(1.05); }
.fab:active { transform: scale(0.97); }
```

FAB solo se muestra en mobile. En desktop el botón "+ Nueva tarea" está en el topbar.

---

## 10. Botones — Guía rápida

```css
/* Primario — blanco sobre oscuro (igual que Linear) */
.btn-primary {
  background: #ffffff;
  color: #111111;
  font-weight: 600;
  font-size: 13px;
  padding: 7px 14px;
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  transition: opacity 100ms;
}
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

/* Ghost — transparente con borde */
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  font-size: 13px;
  padding: 7px 14px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color 100ms, color 100ms;
}
.btn-ghost:hover { border-color: var(--border-strong); color: var(--text-primary); }

/* Ícono — solo ícono sin texto */
.btn-icon {
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex; align-items: center;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: color 80ms, background 80ms;
}
.btn-icon:hover { color: var(--text-primary); background: var(--bg-row-hover); }
```

---

## 11. Inputs y Selects

```css
.input-field {
  width: 100%;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 7px 10px;
  font-size: 13px;
  color: var(--text-primary);
  font-family: var(--font-sans);
  min-height: 36px;
  outline: none;
  transition: border-color 120ms;
}
.input-field:focus {
  border-color: var(--accent);
}
.input-field::placeholder { color: var(--text-tertiary); }

/* Select nativo — USAR CON CAUTELA — ver sección 20 */
.select-field {
  appearance: none;
  background-image: url("data:image/svg+xml,..."); /* chevron */
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 28px;
  cursor: pointer;
}
```

> ⚠️ **IMPORTANTE**: En dark mode, el `<select>` nativo tiene un problema crítico: el popup que abre el browser siempre usa fondo blanco del sistema operativo, sin importar el CSS aplicado. El texto blanco (`color: var(--text-primary)`) sobre fondo blanco es invisible. **Solución**: reemplazar cualquier `<select>` con un componente Vue custom (ver sección 20 CategoriaSelector y sección 21 ProyectoSelector).

---

## 12. Form Layout — Fila de 3 campos

Para fecha + responsable + prioridad en el formulario:

```css
.form-row-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}
@media (max-width: 768px) {
  .form-row-3 { grid-template-columns: 1fr 1fr; }
}
```

---

## 13. Dropdown genérico (autocomplete, selects custom)

```css
.dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0; right: 0;
  background: var(--bg-modal);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  overflow: hidden;
  max-height: 280px;
  overflow-y: auto;
}

/* Scrollbar mínimo */
.dropdown::-webkit-scrollbar { width: 4px; }
.dropdown::-webkit-scrollbar-track { background: transparent; }
.dropdown::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 2px; }

/* Transición */
.drop-enter-active, .drop-leave-active { transition: opacity 120ms, transform 120ms; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-4px); }
```

---

## 14. Auth — Google OAuth con GSI

### 14.1 ⚠️ Usar `renderButton`, NO slots personalizados

`vue3-google-login` con slot personalizado no devuelve `credential` correctamente en producción. Usar el SDK nativo de Google:

```javascript
// En LoginPage.vue setup()
import { googleSdkLoaded } from 'vue3-google-login'

onMounted(() => {
  googleSdkLoaded((google) => {
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleCredentialResponse,
    })
    google.accounts.id.renderButton(
      document.getElementById('google-btn-container'),
      { theme: 'filled_black', size: 'large', text: 'signin_with', width: 280 }
    )
  })
})

function handleCredentialResponse(response) {
  // response.credential = id_token de Google
  loginConGoogle(response.credential)
}
```

### 14.2 JWT doble (temporal → final)

```
1. Google id_token → POST /api/auth/google
2. Backend valida con tokeninfo?id_token=... (HTTPS request, sin librería)
3. Si 1 empresa → JWT final (tipo: 'final', empresa_activa: 'Ori_Sil_2')
4. Si >1 empresa → JWT temporal (tipo: 'temporal', empresas: [...])
5. Usuario selecciona → POST /api/auth/seleccionar_empresa → JWT final
6. JWT final se guarda en localStorage como 'gestion_jwt'
```

### 14.3 Router guard — verificar tipo JWT

```javascript
// router/index.js — beforeEach
Router.beforeEach((to) => {
  const token = localStorage.getItem('gestion_jwt')
  if (to.meta.requiresAuth && !token) return '/login'
  if (to.path === '/login' && token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      if (payload.tipo === 'final') return '/tareas'
      // Token temporal: borrarlo y quedarse en login
      localStorage.removeItem('gestion_jwt')
    } catch { localStorage.removeItem('gestion_jwt') }
  }
})
```

⚠️ **Sin verificar `payload.tipo === 'final'`** el router redirigía a /tareas con token temporal.

### 14.4 Google Cloud Console — configuración

Para que funcione OAuth en una nueva URL:
1. Ir a **Google Cloud Console** → APIs & Services → Credentials
2. Seleccionar el OAuth Client ID
3. En **Authorized JavaScript origins**: agregar `https://gestion.oscomunidad.com`
4. En **Authorized redirect URIs**: no es necesario para GSI (usa popup/redirect interno)
5. Guardar y esperar ~5 minutos para que aplique

---

## 15. Express.js — Gotchas críticos

### 15.1 Express 5: `app.get('*')` no funciona

Express 5 usa `path-to-regexp` que rechaza el wildcard `*` en `.get()`:
```javascript
// ❌ Express 5 — PathError
app.get('*', (req, res) => { res.sendFile(...) })

// ✅ Correcto — usar app.use() al final
app.use((req, res) => {
  res.sendFile(path.join(__dirname, '../app/dist/spa/index.html'))
})
```

### 15.2 Orden de middlewares

```javascript
// 1. express.json()
// 2. CORS
// 3. Logger
// 4. Rutas API (/api/...)
// 5. Static files (dist/spa)
// 6. Fallback SPA (app.use al final)
```

---

## 16. Vue 3 — Gotchas de la sesión

### 16.1 CSS clases con guión en `:class`

```html
<!-- ❌ Incorrecto — el guión es resta en JS -->
<div :class="{ tiene-valor: condicion }">

<!-- ✅ Correcto — comillas simples -->
<div :class="{ 'tiene-valor': condicion }">
```

### 16.2 Modificadores de teclado

```html
<!-- ❌ No existe este modificador en Vue -->
@keydown.arrow-down

<!-- ✅ Correcto -->
@keydown.down
@keydown.up
@keydown.left
@keydown.right
@keydown.enter
@keydown.escape
```

### 16.3 Promise.allSettled vs Promise.all

```javascript
// ❌ Promise.all — si una falla, todas fallan en silencio
const [cats, users, tareas] = await Promise.all([
  api('/categorias'), api('/usuarios'), api('/tareas')
])

// ✅ Promise.allSettled — tolerante a fallos individuales
const [rCats, rUsers, rTareas] = await Promise.allSettled([
  api('/categorias'), api('/usuarios'), api('/tareas')
])
if (rCats.status === 'fulfilled') categorias.value = rCats.value.categorias || []
if (rUsers.status === 'fulfilled') usuarios.value = rUsers.value.usuarios || []
if (rTareas.status === 'fulfilled') tareas.value = rTareas.value.tareas || []
```

---

## 17. Colores de categorías — Referencia

| Categoría | Color | Hex |
|---|---|---|
| Ventas | Azul | `#2979FF` |
| Cartera | Cian | `#00BCD4` |
| Produccion | Naranja | `#FF6D00` |
| Logistica | Verde lima | `#8BC34A` |
| Administrativo | Violeta | `#9C27B0` |
| Informes | Gris azul | `#607D8B` |
| Contenido_y_Marca | Rosa | `#E91E63` |
| Sistemas | Violeta claro | `#7C4DFF` |
| Mantenimiento | Naranja claro | `#FF9800` |
| Orden_y_Aseo | Verde | `#4CAF50` |
| Reuniones | Azul claro | `#03A9F4` |
| Varios | Marrón | `#795548` |
| Empaque | Teal | `#009688` |

---

## 18. Estructura de archivos del proyecto

```
sistema_gestion/
├── MANUAL_DISENO_HIBRIDO.md    ← este archivo
├── api/
│   ├── server.js               — Express 9300, auth, CRUD, OP lookup
│   ├── db.js                   — SSH tunnel + 3 pools MySQL
│   ├── package.json
│   └── .env                    — GOOGLE_CLIENT_ID, JWT_SECRET (NO en git)
└── app/
    ├── src/
    │   ├── boot/               — pinia.js, googleAuth.js
    │   ├── router/             — index.js + routes.js (guard requiresAuth)
    │   ├── stores/             — authStore.js
    │   ├── services/           — api.js (apiFetch + api helpers)
    │   ├── css/                — app.scss (variables CSS + overrides verdes)
    │   ├── pages/
    │   │   ├── LoginPage.vue
    │   │   └── TareasPage.vue
    │   ├── components/
    │   │   ├── TareaForm.vue        — modal/bottom-sheet crear/editar
    │   │   ├── TareaPanel.vue       — panel de detalle lateral (desktop)
    │   │   ├── TareaItem.vue        — fila compacta en la lista
    │   │   ├── Cronometro.vue       — cronómetro inline start/pause/stop
    │   │   ├── OpSelector.vue       — autocomplete OPs Effi
    │   │   ├── CategoriaSelector.vue — dropdown custom (reemplaza <select>)
    │   │   ├── ProyectoSelector.vue  — dropdown custom con crear nuevo
    │   │   ├── EtiquetasSelector.vue — multi-chip con crear nuevo
    │   │   ├── ResponsablesSelector.vue — dropdown usuarios
    │   │   ├── FiltroPersonalizado.vue — panel popover de filtros avanzados
    │   │   └── EstadoBadge.vue      — círculo de estado Linear-style
    │   └── layouts/
    │       └── MainLayout.vue  — sidebar desktop / drawer mobile
    ├── quasar.config.js        — puerto 9300 prod, 9301 dev
    └── package.json
```

---

## 19. Checklist antes de declarar feature terminada

- [ ] ¿Build Quasar sin errores? (`npx quasar build`)
- [ ] ¿Variables CSS existen en `app.scss`? (verificar todas las `var(--...)`)
- [ ] ¿Los endpoints devuelven datos correctos con curl?
- [ ] ¿Funciona en viewport mobile (375px)?
- [ ] ¿Funciona en viewport desktop (1440px)?
- [ ] ¿Los errores de API están manejados (try/catch visible al usuario)?
- [ ] ¿Se documentó en CONTEXTO_ACTIVO.md lo que se construyó?
- [ ] ¿Se usó componente custom en lugar de `<select>` nativo?
- [ ] ¿Los dropdowns custom usan `Teleport to="body"` + `calcularPosicion()`?

---

## 20. ⚠️ Custom Dropdowns — Regla obligatoria

### 20.1 Por qué NO usar `<select>` nativo en dark mode

El `<select>` nativo en dark mode tiene un comportamiento problemático que **no se puede corregir con CSS**:

1. El elemento `<select>` en sí se puede estilizar (borde, fondo, texto).
2. Pero el **popup de opciones** que abre el browser **siempre usa colores del sistema operativo** — en macOS/Windows es blanco con texto negro.
3. Cuando `color: var(--text-primary)` = blanco, las opciones quedan invisibles (texto blanco sobre fondo blanco).
4. `appearance: none` elimina el estilo nativo del `<select>` pero NO del popup de opciones.
5. `color-scheme: dark` puede ayudar en algunos browsers pero tiene comportamiento inconsistente.

**Solución definitiva**: usar componentes Vue custom con `Teleport to="body"` (ver secciones 21 y 22).

### 20.2 Patrón base — CategoriaSelector (sin búsqueda, sin crear)

Úsalo cuando: lista corta (≤20 ítems), sin búsqueda, sin opción de crear nuevo.

```vue
<template>
  <div class="cat-selector" ref="wrapRef">
    <button class="cat-btn" @click.stop="toggle" :class="{ 'has-value': modelValue }">
      <span v-if="catSeleccionada" class="cat-dot" :style="{ background: catSeleccionada.color }"></span>
      <span class="cat-btn-label">{{ catSeleccionada?.nombre?.replace(/_/g,' ') || 'Sin categoría' }}</span>
      <span class="material-icons" style="font-size:14px;color:var(--text-tertiary)">expand_more</span>
    </button>

    <Teleport to="body">
      <div v-if="abierto" class="cat-dropdown" :style="dropdownStyle" @click.stop>
        <div class="cat-lista">
          <div
            v-for="c in categorias"
            :key="c.id"
            class="cat-option"
            :class="{ selected: modelValue === c.id }"
            @click="seleccionar(c.id)"
          >
            <span class="cat-dot" :style="{ background: c.color }"></span>
            <span class="cat-nombre">{{ c.nombre.replace(/_/g,' ') }}</span>
            <span v-if="modelValue === c.id" class="material-icons"
              style="font-size:14px;margin-left:auto;color:var(--accent)">check</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
```

### 20.3 calcularPosicion() — Lógica de posicionamiento

**Obligatoria** en todos los dropdowns custom con Teleport. Detecta si hay más espacio arriba o abajo y posiciona en consecuencia:

```javascript
function calcularPosicion() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const spaceAbove = rect.top
  const spaceBelow = window.innerHeight - rect.bottom
  const goUp = spaceAbove > spaceBelow && spaceBelow < 260  // < 260px abajo → abrir arriba
  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 180)}px`,
    zIndex: 9999,
    ...(goUp
      ? { bottom: `${window.innerHeight - rect.top}px` }
      : { top: `${rect.bottom + 4}px` })
  }
}
```

### 20.4 Click outside — Patrón estándar

```javascript
function onClickOutside(e) {
  if (!wrapRef.value?.contains(e.target)) cerrar()
}
onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
```

### 20.5 CSS base del dropdown Teleported

```css
.cat-dropdown {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  max-height: 280px;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.cat-lista {
  overflow-y: auto;
  flex: 1;
}
.cat-option {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; font-size: 13px; color: var(--text-secondary);
  cursor: pointer; transition: background 60ms;
}
.cat-option:hover, .cat-option.selected {
  background: var(--bg-row-hover); color: var(--text-primary);
}
```

---

## 21. ProyectoSelector — Dropdown con búsqueda y crear nuevo

Versión avanzada del dropdown custom. Úsalo cuando: lista larga (proyectos), necesita búsqueda, permite crear nuevo ítem inline.

### 21.1 Características adicionales vs CategoriaSelector

- Input de búsqueda sticky en la parte superior del dropdown
- Opción "Sin proyecto" siempre visible (con radio implícita)
- Botón "Nuevo proyecto" sticky en la parte inferior — abre `ProyectoModal`
- Maneja proyectos externos (prop) + extras locales recién creados (sin depender del padre)
- Auto-focus en el input de búsqueda al abrir

### 21.2 Template simplificado

```html
<div class="proyecto-dropdown" :style="dropdownStyle">
  <!-- Buscar (sticky top) -->
  <div class="proyecto-search-wrap">
    <span class="material-icons">search</span>
    <input ref="searchRef" v-model="busqueda" placeholder="Buscar proyecto..."
      @keydown.escape="cerrar" />
  </div>
  <!-- Lista scrollable -->
  <div class="proyecto-lista">
    <div class="proyecto-option" :class="{ selected: !modelValue }" @click="seleccionar(null)">
      <span class="proyecto-dot" style="background:var(--border-default)"></span>
      <span>Sin proyecto</span>
    </div>
    <div v-for="p in proyectosFiltrados" :key="p.id" class="proyecto-option"
      @click="seleccionar(p.id)">
      <span class="proyecto-dot" :style="{ background: p.color }"></span>
      <span>{{ p.nombre }}</span>
    </div>
  </div>
  <!-- Crear nuevo (sticky bottom) -->
  <div class="proyecto-crear" @click="abrirModalCrear">
    <span class="material-icons">add</span>
    {{ busqueda && !coincidenciaExacta ? `Crear "${busqueda}"` : 'Nuevo proyecto' }}
  </div>
</div>
```

### 21.3 CSS de la sección de búsqueda y crear

```css
.proyecto-search-wrap {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
}
.proyecto-search {
  background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary); flex: 1;
}
.proyecto-crear {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; font-size: 13px; color: var(--accent);
  cursor: pointer; border-top: 1px solid var(--border-subtle);
  transition: background 60ms;
}
.proyecto-crear:hover { background: var(--accent-muted); }
```

### 21.4 Gestión de proyectos externos vs locales

Cuando el componente recibe `proyectos` como prop externo (el array es del padre), los proyectos recién creados NO están en ese prop aún. Solución: ref `extras` interno:

```javascript
const extras = ref([])
const proyectosData = computed(() => {
  const base = props.proyectos !== null ? props.proyectos : lista.value
  if (!extras.value.length) return base
  const ids = new Set(base.map(p => p.id))
  return [...base, ...extras.value.filter(p => !ids.has(p.id))]
})

function onProyectoCreado(p) {
  if (props.proyectos === null) lista.value.push(p)
  else extras.value.push(p)  // array externo → guardar en extras
  emit('proyecto-creado', p)
  seleccionar(p.id)
}
```

---

## 22. TareaPanel — Panel de detalle lateral

El panel de detalle de una tarea se muestra a la derecha en desktop. En mobile se convierte en pantalla completa.

### 22.1 Estructura visual

```
┌──────────────────────────────────────────────────┐
│ ← Tarea padre (breadcrumb, solo si es subtarea)  │
│ [○] Título de la tarea                      [✕]  │  ← header
│ ────────────────────────────────────────────────  │
│ Estado      [● Pendiente] [● En Progreso] [...]  │  ← chips
│ Prioridad   [● Urgente] [● Alta] [● Media] [...] │  ← chips
│ Categoría   [● Ventas ▾]                         │  ← CategoriaSelector
│ Proyecto    [● Proyecto ▾]                       │  ← ProyectoSelector
│ Etiquetas   [tag1] [tag2] [+ Agregar]            │  ← EtiquetasSelector
│ Responsable [👤 Jennifer ▾]                       │  ← ResponsablesSelector
│ Fecha est.  [📅 2026-03-20]                       │  ← input date
│ ▶ Más campos (acordeón)                          │
│   Inicio estimado / Inicio real / Fin real       │  ← solo si abierto
│ ────────────────────────────────────────────────  │
│ Cronómetro  [●] [⏸] [■] 00:32:14                │  ← Cronometro.vue inline
│ T. real     [0] h [0] m                          │  ← inputs numéricos compactos
│ T. estimado [0] h [0] m                          │
│ ────────────────────────────────────────────────  │
│ Descripción                                       │
│ [textarea 5 líneas]                              │
│ Notas                                            │
│ [textarea 3 líneas]                              │
│ ────────────────────────────────────────────────  │
│ [Eliminar]           [Cerrar]  [✓ Completar]     │  ← footer
│ [Popover: ¿cuánto te tomó? — aparece al completar]│
└──────────────────────────────────────────────────┘
```

### 22.2 Chips de estado y prioridad en el panel

Los selects de estado y prioridad usan chips pill (border-radius: 11px), NO dropdowns. Cada chip muestra un dot de color + label. El activo tiene fondo y borde coloreado:

```javascript
// Definición de estados y prioridades en TareaPanel.vue
const ESTADOS = [
  { key: 'Pendiente',   label: 'Pendiente',   color: '#6b7280' },
  { key: 'En Progreso', label: 'En Progreso', color: '#3b82f6' },
  { key: 'Completada',  label: 'Completada',  color: '#22c55e' },
  { key: 'Cancelada',   label: 'Cancelada',   color: '#ef4444' }
]
const PRIORIDADES = [
  { key: 'Urgente', color: '#ef4444' },
  { key: 'Alta',    color: '#f59e0b' },
  { key: 'Media',   color: '#6b7280' },
  { key: 'Baja',    color: '#374151' }
]
```

```html
<!-- Chip activo: fondo color + '22' (hex), borde color, texto color -->
<button
  class="prioridad-chip"
  :class="{ active: tarea.prioridad === p.key }"
  :style="tarea.prioridad === p.key
    ? { background: p.color + '22', borderColor: p.color, color: p.color }
    : {}"
  @click="actualizar('prioridad', p.key)"
>
```

```css
.prioridad-chip {
  padding: 2px 8px; height: 22px;
  border: 1px solid var(--border-subtle);
  border-radius: 11px;
  background: transparent;
  font-size: 11px; color: var(--text-tertiary);
  cursor: pointer; transition: all 80ms;
  white-space: nowrap;
}
```

### 22.3 Acordeón "Más campos"

Los campos de fechas adicionales (inicio estimado, inicio real, fin real) están en un acordeón expandible para no sobrecargar el panel por defecto.

```html
<div class="accordion-toggle" @click="mostrarFechas = !mostrarFechas">
  <span class="material-icons" style="font-size:13px">
    {{ mostrarFechas ? 'expand_more' : 'chevron_right' }}
  </span>
  <span style="font-size:10px;color:var(--text-tertiary)">Más campos</span>
</div>
<template v-if="mostrarFechas">
  <!-- campos adicionales -->
</template>
```

Los campos "Inicio real" y "Fin real" tienen `field-row-disabled` (opacity 0.45, pointer-events none) cuando la tarea no está Completada ni Cancelada.

### 22.4 Inputs de tiempo compactos (h + m)

Para los campos T. real y T. estimado se usan dos inputs numéricos pequeños en línea:

```css
.tiempos-compact {
  display: flex; align-items: center; gap: 3px; flex-wrap: nowrap;
}
.t-input {
  width: 32px !important; height: 20px !important;
  font-size: 10px !important; text-align: center; padding: 0 2px !important;
}
.t-sep {
  font-size: 10px; color: var(--text-tertiary); flex-shrink: 0;
}
```

### 22.5 Popover "¿Cuánto te tomó?" al completar

Cuando la tarea no tiene `tiempo_real_min > 0`, al hacer clic en "✓ Completar" aparece un popover inline en el footer (NO modal) preguntando el tiempo:

```css
.popover-tiempo {
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 8px 10px;
  width: 100%;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
/* Transición */
.popover-enter-active, .popover-leave-active { transition: opacity 120ms, transform 120ms; }
.popover-enter-from, .popover-leave-to { opacity: 0; transform: translateY(4px); }
```

Si ya tiene tiempo real → completar directo sin popover. Botón "Saltar" para completar sin ingresar tiempo.

### 22.6 Props del TareaPanel

```javascript
defineProps({
  tarea:      { type: Object, default: null },   // objeto tarea completo
  usuarios:   { type: Array,  default: () => [] },
  categorias: { type: Array,  default: () => [] },
  proyectos:  { type: Array,  default: () => [] },
  etiquetas:  { type: Array,  default: () => [] }
})
defineEmits(['cerrar', 'eliminar', 'actualizada', 'proyecto-creado', 'abrir-padre'])
```

### 22.7 Sincronización en tiempo real (sin modal de guardado)

Cada campo del panel guarda automáticamente al cambiar (no hay botón "Guardar"):
- Selects/chips → al hacer clic (`@click="actualizar('campo', valor)"`)
- Fecha → al cambiar (`@change`)
- Textarea → al perder foco (`@blur`)
- Tiempo real/estimado → `@change` en cada input de número

La función `actualizar(campo, valor)` hace PUT al API y emite `'actualizada'` con la tarea actualizada.

---

## 23. Cronómetro inline (Cronometro.vue)

### 23.1 Apariencia en el panel

```
[●] [⏸] [■] 00:32:14     ← cuando corriendo: dot pulsante + botón pause + botón stop + display verde
[▶]      —               ← cuando parado: solo botón play + display "—" si sin tiempo
[▶]      00:10:00        ← cuando parado con tiempo acumulado: play + tiempo previo
```

El componente se usa inline en el `field-row` del TareaPanel:
```html
<div class="field-row">
  <span class="field-label">Cronómetro</span>
  <Cronometro
    :tarea-id="tarea.id"
    :tiempo-base="tarea.tiempo_real_min"
    :cronometro-activo="!!tarea.cronometro_activo"
    :cronometro-inicio="tarea.cronometro_inicio"
    @update="onCronometroUpdate"
  />
</div>
```

### 23.2 Props

```javascript
defineProps({
  tareaId:          { type: Number, required: true },
  tiempoBase:       { type: Number, default: 0 },      // minutos acumulados históricos
  cronometroActivo: { type: Boolean, default: false }, // si hay segmento abierto
  cronometroInicio: { type: String, default: null }    // datetime ISO del inicio actual
})
defineEmits(['update'])  // emit('update', 'iniciado'|'detenido', tiempoMinutos?)
```

### 23.3 ⚠️ Bug crítico de race condition — solución con estado local

**Problema**: Al pausar y volver a arrancar, el contador reiniciaba desde 0.

**Causa raíz**: Secuencia de eventos:
1. `pausar()` llama al API → API devuelve `{tiempo_real_min: 15}`
2. `pausar()` emite `'update', 'detenido', 15` hacia TareaPanel
3. TareaPanel llama `actualizar('tiempo_real_min', 15)` → PUT al API
4. TareaPanel emite `'actualizada', { ...props.tarea, cronometro_activo: 0 }` con datos VIEJOS (antes del PUT)
5. TareasPage actualiza la tarea con `tiempo_real_min = 0` (el valor viejo)
6. Vue propaga `tiempoBase = 0` al prop de Cronometro
7. Usuario hace clic en play → `iniciar()` usa `tiempoBase = 0` → muestra 00:00

**Solución**: El cronómetro mantiene su propio `tiempoAcumulado` local que se actualiza directamente desde la respuesta del API, sin esperar que el padre propague el prop:

```javascript
// Estado local — NO esperar la propagación del prop
const tiempoAcumulado = ref(props.tiempoBase || 0)

// Solo sincronizar desde el prop cuando el cronómetro está detenido
watch(() => props.tiempoBase, v => {
  if (!activo.value) tiempoAcumulado.value = v || 0
})

// Total = acumulado local + segundos del segmento actual
const totalSegundos = computed(() => tiempoAcumulado.value * 60 + segundos.value)

async function pausar() {
  stopInterval()
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    // ← CLAVE: actualizar ANTES de que el padre propague el prop
    tiempoAcumulado.value = data.tiempo_real_min || 0
    activo.value   = false
    segundos.value = 0
    emit('update', 'detenido', data.tiempo_real_min)
  } catch (e) { console.error(e) }
}

async function iniciar() {
  try {
    await api(`/api/gestion/tareas/${props.tareaId}/iniciar`, { method: 'POST' })
    activo.value   = true
    segundos.value = 0   // nuevo segmento desde 0; tiempoAcumulado ya tiene el historial
    startInterval()
    emit('update', 'iniciado')
  } catch (e) { console.error(e) }
}
```

**Regla general**: cuando un componente hijo necesita actualizar su estado inmediatamente después de una operación async y NO puede esperar al prop del padre, usar **estado local** que se inicializa desde el prop pero se desacopla ante cambios mientras está "activo".

### 23.4 Lógica del display

```javascript
const display = computed(() => {
  const total = totalSegundos.value
  if (!activo.value && total === 0) return '—'  // sin tiempo, parado
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return h > 0
    ? `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
    : `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
})
```

### 23.5 CSS del cronómetro inline

```css
.crono-inline { display: flex; align-items: center; gap: 4px; }
.crono-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px;
  border-radius: 4px; border: 1px solid var(--border-default);
  background: transparent; color: var(--text-secondary);
  cursor: pointer; transition: all 80ms; padding: 0;
}
.crono-btn:hover { border-color: var(--border-strong); color: var(--text-primary); }
.crono-btn.activo { border-color: var(--accent-border); color: var(--accent); }
.crono-btn-stop { color: #ef4444; border-color: rgba(239,68,68,0.3); }
.crono-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.7); }
}
.crono-display {
  font-size: 12px; font-variant-numeric: tabular-nums;
  color: var(--text-secondary); min-width: 36px;
}
.crono-display.corriendo { color: var(--accent); font-weight: 500; }
```

### 23.6 Flujo completo del cronómetro en la BD

```
CREAR tarea → estado: pendiente
INICIAR     → POST /api/gestion/tareas/:id/iniciar
              → INSERT g_tarea_tiempo(inicio=NOW, fin=NULL)
              → UPDATE g_tareas SET cronometro_activo=1, cronometro_inicio=NOW, estado='En Progreso'
PAUSAR      → POST /api/gestion/tareas/:id/detener
              → UPDATE g_tarea_tiempo SET fin=NOW, duracion_min=TIMESTAMPDIFF
              → UPDATE g_tareas SET cronometro_activo=0, cronometro_inicio=NULL, tiempo_real_min=SUM
              → Devuelve { tiempo_real_min: N }
REANUDAR    → POST /api/gestion/tareas/:id/iniciar (igual que iniciar — nuevo segmento)
COMPLETAR   → POST /api/gestion/tareas/:id/completar
              → Si hay segmento abierto: cierra segmento primero
              → UPDATE g_tareas SET estado='Completada', tiempo_real_min=SUM total
```

---

## 24. FiltroPersonalizado — Panel de filtros avanzados

### 24.1 Cómo se muestra

Popup flotante posicionado debajo del botón "Filtros" en el topbar. En mobile: bottom sheet (slide desde abajo). Usa `Teleport to="body"` para evitar clipping.

```
Desktop:
  [Botón Filtros] → popup 320px de ancho, debajo del botón

Mobile:
  [Botón Filtros] → bottom sheet 100% ancho, 75vh max-height,
                    border-radius: 12px 12px 0 0
```

### 24.2 Secciones del filtro

| Sección | Tipo | Descripción |
|---|---|---|
| Fechas | Dos inputs date | Rango desde/hasta para fecha_limite |
| Prioridad | Multi-chip | Urgente / Alta / Media / Baja |
| Categoría | Multi-chip con dots de color | Todas las categorías |
| Etiquetas | Multi-chip | Solo visible si hay etiquetas |
| Proyecto | Chips | "Sin proyecto" + lista de proyectos |
| Responsable | Multi-chip con color accent | Solo visible si hay usuarios |
| OP Effi | Input texto | Búsqueda parcial (LIKE %) en id_op |

### 24.3 Comportamiento de chips en el filtro

Chips multi-select: clic alterna activo/inactivo. Al estar activo:
- Prioridades y categorías: `borderColor`, `color`, `background: color + '18'` (del color de la entidad)
- Responsables: usa `var(--accent)` (verde) independiente del usuario
- Proyectos: color del proyecto

```javascript
function toggleArr(arr, val) {
  const i = arr.indexOf(val)
  if (i === -1) arr.push(val)
  else arr.splice(i, 1)
}
```

### 24.4 Props y emits

```javascript
defineProps({
  categorias: { type: Array, default: () => [] },
  etiquetas:  { type: Array, default: () => [] },
  proyectos:  { type: Array, default: () => [] },
  usuarios:   { type: Array, default: () => [] },
  anchorEl:   { type: Object, default: null },  // ref del botón para posicionar
  valor:      { type: Object, default: () => ({}) }  // filtro actual (para pre-seleccionar)
})
defineEmits(['aplicar', 'cerrar'])
// emit('aplicar', filtroObj) — o emit('aplicar', null) al limpiar
```

### 24.5 Objeto filtro emitido

```javascript
{
  fecha_desde:  '2026-03-01' | null,
  fecha_hasta:  '2026-03-31' | null,
  prioridades:  ['Urgente', 'Alta'],     // array vacío = sin filtro
  categorias:   [1, 3, 5],              // ids de categoría
  etiquetas:    [2, 4],                 // ids de etiqueta
  proyecto_id:  5 | 'null' | null,      // 'null' (string) = filtrar sin proyecto
  sinProyecto:  false,
  responsables: ['jen@example.com'],    // array de emails
  id_op:        'OP-123' | null
}
```

### 24.6 Cómo TareasPage aplica los filtros

```javascript
// En cargarTareas() — parámetros del filtro personalizado
if (f.fecha_desde)         params.set('fecha_desde', f.fecha_desde)
if (f.fecha_hasta)         params.set('fecha_hasta', f.fecha_hasta)
if (f.prioridades?.length) params.set('prioridades', f.prioridades.join(','))
if (f.categorias?.length)  params.set('categorias',  f.categorias.join(','))
if (f.etiquetas?.length)   params.set('etiquetas',   f.etiquetas.join(','))
if (f.proyecto_id != null) params.set('proyecto_id', f.proyecto_id)
if (f.responsables?.length) params.set('responsables', f.responsables.join(','))
if (f.id_op)               params.set('id_op', f.id_op)
```

### 24.7 CSS del popup

```css
.fpop {
  position: fixed;
  z-index: 300;
  width: 320px;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--bg-elevated, var(--bg-card));
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex; flex-direction: column;
}
@media (max-width: 768px) {
  .fpop {
    width: 100%;
    max-height: 75vh;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
  }
}
```

---

## 25. Patrones de Vue 3 — Lecciones aprendidas

### 25.1 Props reactivos y race conditions

En operaciones async que implican: hijo hace API call → emite al padre → padre actualiza prop del hijo:

```
Problema: hijo emite → padre actualiza estado → Vue propaga prop → pero el valor es viejo
          porque el padre lo tomó ANTES de que el hijo recibiera la respuesta del API

Solución: usar ref local en el hijo que se actualiza directamente desde la respuesta del API,
          y solo sincronizar desde el prop cuando el componente está "en reposo"
```

Ejemplo de guard en el watch:
```javascript
watch(() => props.tiempoBase, v => {
  if (!activo.value) tiempoAcumulado.value = v || 0  // solo sincroniza cuando no está activo
})
```

### 25.2 Orden de declaración con `defineProps` + `defineEmits`

```javascript
// Correcto: props y emits ANTES de cualquier ref/computed/watch
const props = defineProps({ ... })
const emit = defineEmits([...])
const miRef = ref(props.algoProp)  // puede usar props aquí
```

### 25.3 `watch` con immediate para cargar datos dependientes del prop

```javascript
watch(() => props.tarea?.parent_id, async (parentId) => {
  if (!parentId) { padreNombre.value = ''; return }
  const data = await api(`/api/gestion/tareas/${parentId}`)
  padreNombre.value = data.tarea?.titulo || ''
}, { immediate: true })  // immediate: corre en el mount también
```

### 25.4 Eventos personalizados multi-argumento

```javascript
// Emitir con múltiples argumentos
emit('update', 'detenido', 15)

// Recibir en el padre
function onCronometroUpdate(evento, tiempoMin) {
  if (evento === 'detenido') actualizar('tiempo_real_min', tiempoMin)
}
```

```html
<!-- En el template del padre -->
@update="onCronometroUpdate"
```

### 25.5 `v-if` vs `v-show` en secciones del panel

Usar `v-if` para secciones condicionales (acordeón, popover) — más limpio que `v-show` para contenido que no se necesita al renderizar. Usar `v-show` solo cuando el toggle es muy frecuente (>10 veces/segundo) y el re-render tiene costo.

### 25.6 Números en inputs de tipo `number`

```html
<!-- Para evitar strings cuando se lee .value -->
v-model.number="tiempoFinalH"
<!-- O en @change: parseInt($event.target.value) || 0 -->
@change="actualizarTiempoReal('h', $event.target.value)"
```

```javascript
function actualizarTiempoReal(parte, val) {
  const h = parte === 'h' ? parseInt(val)||0 : Math.floor((props.tarea.tiempo_real_min||0)/60)
  const m = parte === 'm' ? parseInt(val)||0 : (props.tarea.tiempo_real_min||0)%60
  actualizar('tiempo_real_min', h*60+m)
}
```

---

## 26. Endpoints API — Referencia completa (actualizada)

### 26.1 GET /api/gestion/tareas — Filtros disponibles

| Parámetro | Tipo | Descripción |
|---|---|---|
| `filtro` | string | `hoy`, `manana`, `ayer`, `semana`, `mis_tareas`, `pendientes`, `en_progreso`, `todo` |
| `fecha_desde` | date | Rango inicio (fecha_limite >=) |
| `fecha_hasta` | date | Rango fin (fecha_limite <=) |
| `prioridades` | string CSV | ej: `Urgente,Alta` |
| `categorias` | string CSV | ej: `1,3,5` (ids) |
| `etiquetas` | string CSV | ej: `2,4` (ids) |
| `proyecto_id` | int o `'null'` | id proyecto, o `null` para tareas sin proyecto |
| `responsables` | string CSV | ej: `user@a.com,user2@b.com` |
| `id_op` | string | búsqueda parcial LIKE en id_op |

### 26.2 POST /api/gestion/tareas/:id/iniciar

Inicia nuevo segmento de cronómetro:
- INSERT en `g_tarea_tiempo` (inicio=NOW, fin=NULL)
- UPDATE `g_tareas` SET `cronometro_activo=1`, `cronometro_inicio=NOW()`, `estado='En Progreso'`
- Devuelve: `{ ok: true, inicio: "2026-03-18T15:30:00.000Z" }`

### 26.3 POST /api/gestion/tareas/:id/detener

Cierra el segmento activo:
- UPDATE `g_tarea_tiempo` SET `fin=NOW()`, `duracion_min=TIMESTAMPDIFF(MINUTE, inicio, NOW())`
- UPDATE `g_tareas` SET `cronometro_activo=0`, `cronometro_inicio=NULL`, `tiempo_real_min=SUM(duracion_min)`
- Devuelve: `{ ok: true, tiempo_real_min: N }` ← el cronómetro usa este valor directamente

### 26.4 POST /api/gestion/tareas/:id/completar

- Body opcional: `{ tiempo_real_min: N }` — si se pasa, actualiza el tiempo real
- Si hay segmento abierto: lo cierra primero (igual que /detener)
- UPDATE `g_tareas` SET `estado='Completada'`, `fecha_completada=NOW()`
- Devuelve: `{ ok: true, tarea: {...} }`

---

*Manual actualizado el 2026-03-18. Versión 1.2.*
*Crear nuevas secciones numeradas secuencialmente. Nunca modificar secciones existentes sin documentar el cambio.*
