# Skill: Estándar de Tablas — Origen Silvestre

> Aplica a AMBAS apps: menu.oscomunidad.com (ERP, modo claro) y gestion.oscomunidad.com (Gestión, modo oscuro).
> Componentes: `OsDataTable.vue` (ERP) · `GestionTable.vue` (Gestión)
> La diferencia entre apps es SOLO los valores de las variables CSS. Los nombres de variables son idénticos.

---

## REGLA ABSOLUTA

Cualquier vista con tabla en cualquiera de las dos apps DEBE seguir este estándar, a menos que Santi indique explícitamente lo contrario.

---

## 1. ESTRUCTURA VISUAL OBLIGATORIA

```
┌─────────────────────────────────────────────┐
│ TOOLBAR (44px)                               │
│  [Título] [N] [🔴2] [Σ1]  [Desde] [Hasta] [Campos] │
├─────────────────────────────────────────────┤
│ TH  TH  TH  TH  TH  TH  (sticky top:0)    │
├─────────────────────────────────────────────┤
│ Fila subtotales (sticky top:36px, si activa)│
├─────────────────────────────────────────────┤
│ fila · fila · fila · fila                   │
└─────────────────────────────────────────────┘
```

---

## 2. TOOLBAR

- **Izquierda**: Título (font-weight 600, 13px) + badge count de filas + badges de filtros activos (clickeables para limpiar)
- **Derecha** (en este orden): controles de carga de datos (fechas, etc.) + botón "Campos"
- Altura fija: 44px
- Sin filtros de columna en toolbar — esos van en el popup del header

## 3. HEADERS DE COLUMNA

- Click en header → abre popup anclado debajo con:
  1. **Filtro**: select operador (Igual a, Contiene, Mayor que, Menor que, Mayor o igual, Menor o igual, Entre) + input(s)
  2. **Ordenar**: botones Ascendente / Descendente
  3. **Subtotal** (solo numéricas): Σ Suma · x̄ Promedio · ↑ Máximo · ↓ Mínimo
  4. Footer "Limpiar todo" si hay algo activo
- Popup usa `Teleport to="body"` con overlay transparente que cierra al hacer click fuera
- Header muestra: punto verde si tiene filtro activo, flecha si está ordenado

## 4. FILAS

- Altura: 36px
- `cursor: pointer` siempre (click abre detalle)
- Hover: `background: var(--bg-row-hover)`
- `border-bottom: 1px solid var(--border-subtle)`
- Texto: `color: var(--text-secondary)`, 13px

## 5. FILA DE SUBTOTALES

- Solo visible si hay ≥1 columna con aggregate activo
- Posición: primera fila del tbody, sticky `top: 36px; z-index: 4`
- Background: `rgba(16,185,129,0.06)`, border-bottom: `2px solid rgba(16,185,129,0.25)`

## 6. SELECTOR DE CAMPOS ("Campos")

- Botón en toolbar derecha
- Popup con pills toggleables (una por columna)
- Botones "Mostrar todos" / "Ocultar todos"

## 7. POPUP DE DETALLE (click en fila)

- Modal centrado con backdrop oscuro
- Estructura: header (título + botón cerrar X) + cuerpo con secciones
- Secciones con label uppercase 11px + contenido
- Campos de auditoría (datetime reales) siempre en texto pequeño, nunca editables
- Admin: campos editables solo las horas manuales (hora_inicio, hora_fin) y observaciones

## 8. CSS BASE (idéntico en ambas apps — usa variables CSS)

```css
.os-table-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: visible; /* CRÍTICO: no ocultar popups */
  position: relative;
}
.table-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  height: 44px; padding: 0 14px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-card);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.th {
  text-align: left; padding: 0 12px; height: 36px;
  font-size: 11px; font-weight: 600; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-card);
  position: sticky; top: 0; z-index: 5;
  cursor: pointer; user-select: none; white-space: nowrap;
}
.th:hover { color: var(--text-secondary); }
.th-sorted { color: var(--accent) !important; }
.th-filtered::after { content: '●'; font-size: 6px; color: var(--accent); margin-left: 4px; vertical-align: super; }
.td {
  padding: 0 12px; height: 36px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary); vertical-align: middle; white-space: nowrap;
}
.data-row { cursor: pointer; transition: background 60ms; }
.data-row:hover .td { background: var(--bg-row-hover); }
```

## 9. IMPLEMENTACIÓN

- **ERP** (menu.oscomunidad.com): usar `OsDataTable.vue` en `frontend/app/src/components/`
- **Gestión** (gestion.oscomunidad.com): usar `GestionTable.vue` en `sistema_gestion/app/src/components/`

`GestionTable.vue` es idéntico en lógica a `OsDataTable.vue` pero:
- Usa Material Icons (`<span class="material-icons">`) en lugar de Lucide
- Sin botón Exportar (no hay endpoint de export en Gestión)
- Sin carga automática de tooltips

## 10. NO HACER

- NO poner filtros de columna en el toolbar — van en el popup del header
- NO usar `overflow: hidden` en `.os-table-wrapper` — los popups quedan ocultos
- NO filtrar datos en el API por columnas — los filtros de columna son client-side
- NO marcar tarea frontend como lista sin haber hecho el rebuild Quasar

---

## BUILDS

```bash
# ERP (menu.oscomunidad.com)
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/frontend/app && npx quasar build

# Gestión (gestion.oscomunidad.com)
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/sistema_gestion/app && npx quasar build
sudo systemctl restart os-gestion.service
```
