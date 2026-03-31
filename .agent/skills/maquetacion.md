---
description: Reglas obligatorias de maquetación y CSS responsive para apps web del proyecto. Previene errores comunes en tablas, móvil, Vue reactivity y layout.
---

# Skill: Maquetación y CSS Responsive

> **Por qué existe este documento:** Durante el desarrollo de la app de Inventario Físico (marzo 2026), se perdieron 10+ iteraciones en bugs de CSS móvil y layout. La mayoría por errores de especificidad CSS, `table-layout: fixed`, y reactividad Vue. Este manual documenta cada lección para no repetirlas.

---

## Regla #1 — NUNCA inline styles en elementos dinámicos

**El error:** Poner `style="width:60px"` en `<col>` o `<td>`. Los estilos inline tienen especificidad máxima y **no se pueden sobreescribir con media queries**.

```html
<!-- MAL: media query no puede cambiar este width -->
<col style="width: 60px">

<!-- BIEN: usa clase CSS, media query la sobreescribe -->
<col class="col-status">
```

```css
.col-status { width: 60px; }

@media (max-width: 600px) {
  .col-status { width: 40px; } /* Funciona */
}
```

**Regla:** Usar clases CSS para dimensiones. Inline styles solo para valores calculados dinámicamente en JS que no necesitan media queries.

---

## Regla #2 — table-layout: fixed — NO usar display: none

**El error:** En `table-layout: fixed`, cada `<col>` asigna ancho fijo. Si ocultas un `<td>` con `display: none`, la fila pierde una celda y las restantes se desplazan — ya no coinciden con sus columnas.

```css
/* MAL: desalinea col vs td */
@media (max-width: 600px) {
  td.col-id { display: none; }
}

/* BIEN: colapsa visualmente sin eliminar la celda */
@media (max-width: 600px) {
  .col-id { width: 0; }
  td.col-id {
    font-size: 0;
    padding: 0;
    overflow: hidden;
    border: none;
  }
}
```

**Regla:** Para ocultar columnas en tablas con `table-layout: fixed`, usar `width: 0` + `font-size: 0` + `padding: 0`. NUNCA `display: none`.

---

## Regla #3 — Presupuesto de píxeles en móvil

Antes de escribir CSS móvil, **calcular el presupuesto de píxeles explícitamente**.

Ejemplo para viewport 400px:
```
Total disponible:     400px
- padding body:       -16px (8+8)
- borde tabla:        -2px
= Espacio útil:       382px

Distribución:
  Status:   28px
  Artículo: 150px (flex)
  Categ:    35px
  Stock:    40px
  Conteo:   75px
  Acción:   40px
  ---
  Total:    368px ✓ (14px margen)
```

**Regla:** Documentar el cálculo antes de implementar. Si las columnas suman más que el viewport, el diseño se rompe. No improvisar anchos "a ojo".

---

## Regla #4 — Vue: refs reactivos + setInterval = re-render destructivo

**El error:** Un reloj que actualiza `reloj.value` cada segundo con `setInterval` causa re-render de todo el componente Vue. Esto borra valores de inputs que usan `:value` binding.

```javascript
// MAL: cada tick re-renderiza todo
const reloj = ref('')
setInterval(() => {
  reloj.value = new Date().toLocaleTimeString() // Re-render completo
}, 1000)

// BIEN: DOM directo, sin tocar reactividad
setInterval(() => {
  const el = document.getElementById('inv-clock')
  if (el) el.textContent = new Date().toLocaleTimeString()
}, 1000)
```

**Regla:** Para actualizaciones periódicas (relojes, timers, contadores) que NO necesitan afectar el layout, usar `document.getElementById()` directo. Reservar `ref()` solo para datos que necesitan trigger de render.

---

## Regla #5 — Input numérico: actualizar estado ANTES del await

**El error:** Al guardar un conteo, el `await fetch()` tarda ~200ms. Si Vue re-renderiza durante ese await (por cualquier otro ref que cambie), el input vuelve al valor anterior.

```javascript
// MAL: el re-render durante await restaura el valor previo
async function guardarConteo(articulo, valor) {
  await fetch('/api/...', { body: JSON.stringify({ valor }) })
  articulo.inventario_fisico = valor // Tarde: ya se re-renderizó
}

// BIEN: actualizar primero, luego fetch
async function guardarConteo(articulo, valor) {
  articulo.inventario_fisico = valor // Inmediato
  await fetch('/api/...', { body: JSON.stringify({ valor }) })
}
```

**Regla:** Siempre actualizar el estado reactivo del objeto ANTES del `await`. El usuario ve el cambio instantáneo.

---

## Regla #6 — Input decimal: type="text" + inputmode="decimal"

**El error:** `type="number"` no acepta comas como separador decimal, y en algunos navegadores móviles no muestra el teclado correcto.

```html
<!-- MAL: no acepta comas, teclado inconsistente -->
<input type="number" step="0.01">

<!-- BIEN: teclado numérico + acepta comas y puntos -->
<input type="text" inputmode="decimal"
       @blur="guardarConteo(articulo, $event.target.value)">
```

```javascript
function parseDecimal(val) {
  if (typeof val === 'number') return val
  return parseFloat(String(val).replace(',', '.')) || 0
}
```

**Regla:** Para inputs de conteo/medición, usar `type="text"` + `inputmode="decimal"` y parsear manualmente.

---

## Regla #7 — Móvil: flex-wrap en celdas de tabla

**El error:** `flex-wrap: wrap` en una celda de tabla hace que las etiquetas (badges, tags) se apilen verticalmente, duplicando la altura de la fila y rompiendo el layout.

```css
/* MAL: tags se apilan verticalmente */
td .tags { display: flex; flex-wrap: wrap; gap: 4px; }

/* BIEN: todo en una línea, truncar si no cabe */
td .tags { display: flex; flex-wrap: nowrap; gap: 2px; overflow: hidden; }
```

**Excepción:** Si la celda de categoría necesita multilinea en móvil (porque el texto es corto, 2-3 chars), se puede usar `word-break: break-all` en el texto directamente, no flex-wrap.

---

## Regla #8 — Usar Playwright para validar móvil

**NUNCA** confiar en que el CSS móvil "se ve bien" sin verificar. Tomar screenshot con Playwright antes de deployar.

```python
# Script rápido para preview móvil
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(
        viewport={'width': 400, 'height': 800},
        device_scale_factor=2
    )
    page.goto('http://127.0.0.1:9401')
    page.wait_for_timeout(2000)
    page.screenshot(path='/tmp/movil_preview.png', full_page=False)
    browser.close()
```

**Regla:** Después de cada cambio CSS significativo en responsive, tomar screenshot Playwright con viewport 400x800 y revisar antes de reportar al usuario.

---

## Regla #9 — Orden de capas CSS

Mantener esta estructura en el `<style>` del componente:

```
1. Variables CSS (:root / .dark)
2. Reset y base (body, *, table)
3. Layout desktop (default)
4. Componentes (modal, popup, panel)
5. @media tablet (max-width: 900px)
6. @media móvil (max-width: 600px)
7. @media extra-small (max-width: 380px)
```

**Regla:** Las media queries van AL FINAL del bloque `<style>`. Nunca mezclar media queries entre las reglas desktop.

---

## Regla #10 — Stepper buttons en móvil

Los botones stepper (+/-) de 44px consumen espacio valioso en móvil. En pantallas < 600px, ocultarlos y dejar que el usuario escriba directamente.

```css
@media (max-width: 600px) {
  .stepper-btn { display: none; }
  .conteo-input { width: 100%; text-align: center; }
}
```

---

## Checklist pre-deploy responsive

Antes de considerar terminado cualquier layout responsive:

- [ ] **Sin inline styles** en elementos que necesitan media queries
- [ ] **Presupuesto de píxeles** calculado y documentado para 400px
- [ ] **table-layout: fixed**: ningún `display: none` en celdas
- [ ] **Screenshot Playwright** a 400x800 revisado
- [ ] **Inputs numéricos**: estado actualizado antes de await
- [ ] **Sin refs reactivos** en setInterval/timers visuales
- [ ] **flex-wrap: nowrap** en celdas de tabla
- [ ] **Media queries** al final del `<style>`, no mezcladas
