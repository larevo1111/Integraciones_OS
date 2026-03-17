# Manual de Diseño — Aplicaciones Híbridas OS (Web + Mobile)

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

/* Select */
.select-field {
  appearance: none;
  background-image: url("data:image/svg+xml,..."); /* chevron */
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 28px;
  cursor: pointer;
}
```

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
    │   │   ├── TareaForm.vue   — modal/bottom-sheet crear/editar
    │   │   └── OpSelector.vue  — autocomplete OPs Effi
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

---

*Manual creado el 2026-03-16. Actualizar cuando se definan nuevos patrones de diseño con Santi.*
