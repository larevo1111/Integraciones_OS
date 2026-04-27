---
name: quasar-layout
description: >
  MANDATORY for any UI/layout/styling/maquetación task in this project.
  Triggers on: layout, page, vista, formulario, tabla, sidebar, drawer, header,
  footer, responsive, spacing, grid, card, dialog, toolbar, menu, maquetación,
  diseño, componente visual, UI, interfaz, estilo, CSS.
  Use when creating, editing or fixing any .vue file that contains template markup.
---

# Quasar Framework Layout Rules — MANDATORY

YOU ARE WORKING WITH QUASAR FRAMEWORK (Vue 3 + Composition API).
Quasar has its own complete layout system, component library, and utility classes.

**CRITICAL RULE: DO NOT reinvent what Quasar already provides.**

---

## 1. Layout Hierarchy — ALWAYS follow this structure

```
QLayout
├── QHeader → QToolbar → QToolbarTitle, QBtn
├── QDrawer → QList > QItem > QItemSection
├── QPageContainer
│   └── QPage (class="q-pa-md")
│       └── Your content here
└── QFooter (optional)
```

- Every page MUST be inside `<q-page>` within a `<q-layout>`
- NEVER create a page without QLayout/QPage structure
- Use `QPageSticky` for floating action buttons, NOT custom CSS position:fixed

---

## 2. Spacing — USE QUASAR CLASSES ONLY

| Need | Quasar Class | DO NOT USE |
|------|-------------|------------|
| Padding | `q-pa-md`, `q-pt-sm`, `q-px-lg` | `padding: 16px` |
| Margin | `q-ma-md`, `q-mt-sm`, `q-mx-auto` | `margin: 8px` |
| Gap between items | `q-gutter-md` on parent row | `gap: 16px` |
| No padding | `q-pa-none` | `padding: 0` |

Sizes: `none`, `xs` (4px), `sm` (8px), `md` (16px), `lg` (24px), `xl` (48px)

Directions: `a` (all), `t` (top), `b` (bottom), `l` (left), `r` (right), `x` (horizontal), `y` (vertical)

---

## 3. Grid System — QUASAR FLEX CLASSES

### Row + Columns
```html
<div class="row q-gutter-md">
  <div class="col-12 col-md-6">Left</div>
  <div class="col-12 col-md-6">Right</div>
</div>
```

### Alignment
| Need | Class |
|------|-------|
| Center horizontally | `justify-center` |
| Center vertically | `items-center` |
| Space between | `justify-between` |
| Stretch height | `items-stretch` |
| Full height | `fit` or `full-height` |
| Full width | `full-width` |

### DO NOT:
- Write `display: flex` — use `class="row"` or `class="column"`
- Write `flex-wrap: wrap` — rows wrap by default
- Write `align-items: center` — use `items-center`
- Write `justify-content: space-between` — use `justify-between`
- Write `@media (min-width: 768px)` — use `col-xs-12 col-sm-6 col-md-4`

### Breakpoints
| Prefix | Min Width |
|--------|-----------|
| xs | 0px |
| sm | 600px |
| md | 1024px |
| lg | 1440px |
| xl | 1920px |

---

## 4. Components — USE QUASAR, NOT RAW HTML

| Need | Use | NOT |
|------|-----|-----|
| Button | `<q-btn>` | `<button>` |
| Input | `<q-input>` | `<input>` |
| Select | `<q-select>` | `<select>` |
| Checkbox | `<q-checkbox>` | `<input type="checkbox">` |
| Table | `<q-table>` | `<table>` |
| Card | `<q-card>` > `<q-card-section>` | `<div class="card">` |
| Dialog/Modal | `<q-dialog>` | custom modal div |
| List | `<q-list>` > `<q-item>` | `<ul>` / `<li>` |
| Tabs | `<q-tabs>` > `<q-tab>` | custom tabs |
| Expansion | `<q-expansion-item>` | custom accordion |
| Separator | `<q-separator>` | `<hr>` |
| Icon | `<q-icon>` | `<i>` or `<svg>` |
| Badge | `<q-badge>` | custom badge span |
| Spinner | `<q-spinner>` | custom loading div |
| Tooltip | `<q-tooltip>` | `title=""` attribute |
| Menu | `<q-menu>` | custom dropdown |
| Banner | `<q-banner>` | custom alert div |
| Breadcrumbs | `<q-breadcrumbs>` | custom breadcrumb |
| Form wrapper | `<q-form>` | `<form>` |

---

## 5. Common ERP Patterns

### Page with filters + table
```html
<q-page class="q-pa-md">
  <div class="row q-gutter-sm q-mb-md items-end">
    <q-input v-model="filters.search" label="Buscar" dense outlined class="col-12 col-md-3" />
    <q-select v-model="filters.status" :options="statusOpts" label="Estado" dense outlined class="col-12 col-md-2" />
    <q-btn label="Filtrar" color="primary" dense @click="applyFilters" />
  </div>
  <q-table
    :rows="rows"
    :columns="columns"
    row-key="id"
    :loading="loading"
    :pagination="pagination"
    @request="onRequest"
  />
</q-page>
```

### Form layout (create/edit)
```html
<q-page class="q-pa-md">
  <q-form @submit="onSubmit" class="q-gutter-md" style="max-width: 600px">
    <q-input v-model="form.name" label="Nombre" outlined :rules="[val => !!val || 'Requerido']" />
    <q-input v-model="form.email" label="Email" outlined type="email" />
    <div class="row q-gutter-sm">
      <q-input v-model="form.phone" label="Teléfono" outlined class="col" />
      <q-input v-model="form.city" label="Ciudad" outlined class="col" />
    </div>
    <div>
      <q-btn label="Guardar" type="submit" color="primary" />
      <q-btn label="Cancelar" flat class="q-ml-sm" @click="goBack" />
    </div>
  </q-form>
</q-page>
```

### Detail view with sections
```html
<q-page class="q-pa-md">
  <q-card flat bordered>
    <q-card-section>
      <div class="text-h6">Detalle de Pedido #{{ order.id }}</div>
    </q-card-section>
    <q-separator />
    <q-card-section>
      <div class="row q-gutter-md">
        <div class="col-12 col-md-6">
          <div class="text-caption text-grey">Cliente</div>
          <div>{{ order.client }}</div>
        </div>
        <div class="col-12 col-md-6">
          <div class="text-caption text-grey">Fecha</div>
          <div>{{ order.date }}</div>
        </div>
      </div>
    </q-card-section>
  </q-card>
</q-page>
```

---

## 6. Typography — QUASAR CLASSES

| Class | Usage |
|-------|-------|
| `text-h4` to `text-h6` | Page/section titles |
| `text-subtitle1`, `text-subtitle2` | Subtitles |
| `text-body1`, `text-body2` | Body text |
| `text-caption` | Labels, small text |
| `text-overline` | Category labels |
| `text-bold`, `text-italic` | Emphasis |
| `text-grey`, `text-primary` | Color |
| `text-center`, `text-right` | Alignment |

---

## 7. Colors — QUASAR SYSTEM

Use Quasar color props and classes:
- `color="primary"` on components
- `class="text-primary"`, `class="bg-grey-2"`
- `class="text-positive"` / `text-negative` / `text-warning` / `text-info`

DO NOT write custom color CSS unless it's a project-specific brand color defined in `quasar.config.js`.

---

## 8. Visibility & Responsive Helpers

| Class | Meaning |
|-------|---------|
| `gt-sm` | Show only above sm breakpoint |
| `lt-md` | Show only below md breakpoint |
| `xs-only`, `md-only` | Show only on that breakpoint |
| `hidden` | Hide element |

Use these instead of media queries for show/hide logic.

---

## 9. STOP Rules — When to STOP and reassess

- If you've written more than 5 lines of custom CSS for layout → STOP. Use Quasar classes.
- If you're creating a custom component that looks like a Quasar component → STOP. Use the Quasar one.
- If you're spending more than 3 iterations fixing visual alignment → STOP. Simplify structure.
- If you're nesting more than 4 div levels for layout → STOP. Flatten with Quasar grid.
- If you're writing a media query → STOP. Use responsive col classes or visibility helpers.

---

## 10. Allowed Custom CSS

Custom CSS is ONLY acceptable for:
- Specific brand colors not in Quasar theme
- Animations/transitions not covered by Quasar
- Very specific visual effects (shadows, gradients) on individual elements
- Print styles
- Third-party component overrides

Even then, keep it minimal and scoped (`<style scoped>`).

---

## 11. Mobile Input — REGLA CRÍTICA (IME / Teclado Virtual)

**NUNCA usar `@keydown.enter` ni `@keyup.enter` en inputs que se usen en móvil.**

El teclado virtual (IME) de Android/iOS mantiene la composición activa durante autocompletar/predicción. `@keydown.enter` se dispara ANTES de que el IME confirme el texto, causando:
- Última palabra cortada
- Texto duplicado en el input
- Comportamiento inconsistente entre desktop y móvil

### Patrón CORRECTO: `<form>` con `@submit.prevent`

```html
<form @submit.prevent="guardar()">
  <input v-model="texto" placeholder="..." />
  <button type="submit">✓</button>
  <button type="button" @click="cancelar">×</button>
</form>
```

**Por qué funciona:** Al presionar Enter dentro de un `<form>`, el navegador primero le dice al IME "confirmá el texto", el IME confirma la composición completa, y DESPUÉS dispara el evento `submit`. Es el estándar HTML.

### Beneficios:
- Funciona en desktop Y móvil sin cambios
- Compatible con Capacitor (WebView)
- El botón ✓ da alternativa visual al Enter
- Cero hacks: sin `@blur` auto-save, sin flags, sin setTimeout, sin compositionstart/end

### NUNCA hacer:
- `@keydown.enter.prevent="guardar()"` — corta texto en móvil
- `@keyup.enter="guardar()"` — timing inconsistente
- `@blur="guardar()"` — causa race conditions con Enter
- `el.blur(); el.value = ''` — rompe v-model y composición IME
- `event.isComposing` checks — no funciona en todos los teclados móviles

---

## 12. Bottombar móvil — REGLA CRÍTICA (no tapar contenido)

Sistema Gestión tiene un **`q-footer` móvil fijo** (`MainLayout.vue` con `class="bottom-tab-bar lt-md"`) con tabs de navegación: Tareas / Equipo / Jornadas / Proyectos / Más. **Alto efectivo: ~53px + `safe-area-inset-bottom`**, z-index 2000.

**Cualquier elemento posicionado abajo en móvil queda tapado por ese bottombar si no se compensa.**

Casos donde aplica:
- Floating action bars (`position: fixed; bottom: …`) — ej. `MultiActionBar`
- Botones de acción al final de un panel scrollable que ocupa 100vh — ej. `OpPanel`, `TareaPanel`
- FABs (floating action buttons), banners de notificación pegados abajo
- Modals tipo sheet que se abren desde abajo

### Patrón CORRECTO

**Si el elemento está fijado al fondo** (`position: fixed; bottom: …`):
```scss
@media (max-width: 768px) {
  .mi-elemento {
    /* bottombar ~53px + safe-area + 12px margen */
    bottom: calc(65px + env(safe-area-inset-bottom, 0));
  }
}
```

**Si el elemento es un panel scrollable que ocupa 100vh** (Teleport a body, body overflow-y:auto):
```scss
@media (max-width: 768px) {
  .mi-panel-body {
    /* deja espacio abajo para que el último contenido no quede tapado */
    padding-bottom: calc(80px + env(safe-area-inset-bottom, 0));
  }
}
```

### NUNCA hacer:
- `bottom: 16px` o `bottom: 24px` hardcoded para mobile FABs/bars — quedan tapados
- Subir `z-index` por encima del footer (2000+) para "ganarle" — el contenido sigue cubriendo el footer pero el footer es navegación útil; mejor compensar la posición
- Esconder el bottombar cuando se abre un panel — rompe la navegación

### Casos resueltos (referencia)
- `OpPanel.vue` — botones Procesar/Validar tapados (v2.9.4): `padding-bottom: calc(80px + env(safe-area-inset-bottom, 0))` en `.op-body` mobile
- `MultiActionBar.vue` — bar de selección múltiple tapada: `bottom: calc(65px + env(safe-area-inset-bottom, 0))` en mobile

### Aplicabilidad
Esta regla aplica al **Sistema Gestión** (que tiene bottombar móvil). Otros módulos (ERP, ia-admin, Inventario) pueden tener o no bottombar — verificar `MainLayout.vue` del módulo antes de aplicar.
