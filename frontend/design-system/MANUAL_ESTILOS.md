# Manual de Estilos — ERP Origen Silvestre
### Basado en Linear.app · Versión 2.0 · 2026-03-11
### ✅ Verificado con 88 capturas reales de Linear.app

> **Para agentes IA**: Este documento es la fuente de verdad absoluta del estilo visual del ERP.
> Antes de crear cualquier componente frontend, consultar este manual.
> Stack de implementación: **Vue 3 + Quasar Framework**.
> Las capturas de referencia están en `screenshots/` (88 imágenes). Ver `screenshots/INDEX.md`.

---

## ÍNDICE

1. [Filosofía de Diseño](#1-filosofía-de-diseño)
2. [Colores](#2-colores)
3. [Tipografía](#3-tipografía)
4. [Espaciado y Layout](#4-espaciado-y-layout)
5. [Bordes y Sombras](#5-bordes-y-sombras)
6. [Estructura de la App](#6-estructura-de-la-app)
7. [Navegación — Sidebar](#7-navegación--sidebar)
8. [Topbar y Tabs](#8-topbar-y-tabs)
9. [Tablas y Listas de Issues](#9-tablas-y-listas-de-issues)
10. [Panel de Detalle](#10-panel-de-detalle)
11. [Botones](#11-botones)
12. [Formularios e Inputs](#12-formularios-e-inputs)
13. [Badges y Estados](#13-badges-y-estados)
14. [Cards / Tarjetas](#14-cards--tarjetas)
15. [Modales y Paneles](#15-modales-y-paneles)
16. [Avatares e Imágenes](#16-avatares-e-imágenes)
17. [Íconos](#17-íconos)
18. [Menús Contextuales y Dropdowns](#18-menús-contextuales-y-dropdowns)
19. [Command Palette](#19-command-palette)
20. [Notificaciones y Toasts](#20-notificaciones-y-toasts)
21. [Animaciones y Transiciones](#21-animaciones-y-transiciones)
22. [Estados de Carga](#22-estados-de-carga)
23. [Tooltips](#23-tooltips)
24. [Scrollbar](#24-scrollbar)
25. [Responsive y Breakpoints](#25-responsive-y-breakpoints)
26. [Elementos Pendientes de Definir](#26-elementos-pendientes-de-definir)

---

## 1. FILOSOFÍA DE DISEÑO

### Principios fundamentales — observados en capturas reales

| Principio | Descripción |
|---|---|
| **Ultra-dark first** | El fondo es casi negro puro (#0d0d0d). NO dark-gray, sino negro real. |
| **Sin color innecesario** | Texto en blanco/gris. El único color de acento es violeta (#5E6AD2) para estados y controles. |
| **Botón primario = blanco** | ⚠️ Contraintuitivo: el CTA principal es BLANCO con texto oscuro, no azul. |
| **Densidad alta** | Filas de 36-38px, texto 13-14px. Máxima info en pantalla. |
| **Jerarquía por opacidad** | No por color. El texto primario es blanco puro, secundario es gris medio, terciario es gris oscuro. |
| **Íconos lineales** | Siempre stroke, nunca filled. Tamaño 16px en 99% de los casos. |
| **Velocity** | Todo ≤ 150ms. Ni un ms más lento. |

### Lo que NO existe en Linear (y no hacemos)
- Fondos de color en headers o sidebars
- Gradientes decorativos en la UI funcional (solo en marketing)
- Sombras de color
- Borders gruesos
- Texto centrado en contenido (siempre left-aligned)
- Animaciones bounce o spring
- Colores vibrantes para elementos no-estados

---

## 2. COLORES

> ✅ Verificado visualmente contra capturas reales de Linear.app

### 2.1 Fondos — Modo Oscuro (DEFAULT)

```css
/* ─── FONDOS ─────────────────────────────────────── */
--bg-app:          #0d0d0f;   /* Fondo principal — casi negro con leve tinte azul */
--bg-sidebar:      #141418;   /* Sidebar — gris muy oscuro */
--bg-card:         #1c1c1e;   /* Cards, modales, paneles */
--bg-card-hover:   #242428;   /* Card al hacer hover */
--bg-row-hover:    #1a1a1e;   /* Hover sobre filas de tabla */
--bg-row-selected: rgba(94,106,210,0.08); /* Fila seleccionada — tinte acento */
--bg-input:        #161618;   /* Fondo de inputs en la app */
--bg-input-mkt:    #1c1c1e;   /* Fondo de inputs en forms de marketing */
--bg-modal:        #1c1c1e;   /* Fondo de modales */
--bg-overlay:      rgba(0,0,0,0.65); /* Overlay — oscuro pero no opaco total */

/* ─── TEXTOS ──────────────────────────────────────── */
--text-primary:    #ffffff;   /* Texto principal — blanco puro */
--text-secondary:  #8a8f98;   /* Texto secundario — gris medio */
--text-tertiary:   #5a5f6a;   /* Metadata, placeholders — gris oscuro */
--text-disabled:   #3a3f4a;   /* Deshabilitado */
--text-inverse:    #0d0d0f;   /* Texto sobre fondos claros (botón blanco) */
--text-link:       #5e6ad2;   /* Links — color acento */
--text-mono:       #8a8f98;   /* IDs de issues, código — gris, fuente mono */

/* ─── BORDES ──────────────────────────────────────── */
--border-subtle:   rgba(255,255,255,0.06);  /* Borde casi invisible */
--border-default:  rgba(255,255,255,0.10);  /* Borde estándar */
--border-strong:   rgba(255,255,255,0.18);  /* Borde visible (inputs, cards) */
--border-focus:    #5e6ad2;                 /* Foco en inputs */

/* ─── ACENTO — Violeta Linear ─────────────────────── */
--accent:          #5e6ad2;   /* Violeta/índigo — color de acento principal */
--accent-hover:    #6e7ae2;   /* Hover del acento */
--accent-active:   #4e5ac2;   /* Click del acento */
--accent-muted:    rgba(94,106,210,0.12); /* Fondo suave de acento */
--accent-border:   rgba(94,106,210,0.35); /* Borde suave de acento */

/* ─── ESTADOS SEMÁNTICOS ──────────────────────────── */
--color-success:   #4ade80;   /* Verde */
--color-warning:   #f59e0b;   /* Amarillo/naranja (In Progress) */
--color-error:     #f87171;   /* Rojo */
--color-info:      #60a5fa;   /* Azul info */

/* ─── SOMBRAS ─────────────────────────────────────── */
--shadow-xs:  0 1px 2px rgba(0,0,0,0.4);
--shadow-sm:  0 2px 8px rgba(0,0,0,0.5);
--shadow-md:  0 4px 20px rgba(0,0,0,0.6);
--shadow-lg:  0 8px 40px rgba(0,0,0,0.7);
--shadow-xl:  0 20px 80px rgba(0,0,0,0.8);
```

---

### 2.2 Paleta — Modo Claro

```css
[data-theme="light"] {
  --bg-app:         #f5f5f5;
  --bg-sidebar:     #ebebeb;
  --bg-card:        #ffffff;
  --bg-card-hover:  #f8f8f8;
  --bg-row-hover:   #f2f2f2;
  --bg-input:       #ffffff;
  --bg-modal:       #ffffff;
  --bg-overlay:     rgba(0,0,0,0.45);

  --text-primary:   #111111;
  --text-secondary: #666b75;
  --text-tertiary:  #9ca3af;
  --text-disabled:  #d1d5db;
  --text-inverse:   #ffffff;

  --border-subtle:  rgba(0,0,0,0.05);
  --border-default: rgba(0,0,0,0.09);
  --border-strong:  rgba(0,0,0,0.16);

  --shadow-xs: 0 1px 2px rgba(0,0,0,0.06);
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 20px rgba(0,0,0,0.10);
  --shadow-lg: 0 8px 40px rgba(0,0,0,0.14);
  --shadow-xl: 0 20px 80px rgba(0,0,0,0.18);
}
```

---

### 2.3 Colores semánticos de estado de issues

> ✅ Observados en capturas reales: `15_lista_issues.png`, `13_panel_detalle_issue.png`, `46_badges_tags.png`

Cada estado tiene un **ícono circular con color de relleno** + texto. NO solo texto.

| Estado | Color del ícono | Hex | Forma del ícono |
|---|---|---|---|
| Todo / Backlog | Gris | `#6b7280` | Círculo vacío (outline) |
| In Progress | Naranja/amarillo | `#f59e0b` | Círculo con relleno parcial (medio) |
| In Review | Verde claro | `#4ade80` | Círculo con check |
| Done | Verde | `#22c55e` | Círculo relleno con check |
| Cancelled | Gris tachado | `#6b7280` | Círculo con X |
| Urgent | Rojo | `#ef4444` | Ícono de alerta |
| High | Naranja | `#f97316` | Barras (3 barras, todas rellenas) |
| Medium | Amarillo | `#f59e0b` | Barras (2 barras rellenas) |
| Low | Gris | `#9ca3af` | Barras (1 barra rellena) |
| No priority | Gris muy tenue | `#4b5563` | Barras vacías |

---

## 3. TIPOGRAFÍA

### 3.1 Fuentes

> ✅ Confirmado visualmente en todas las capturas

```css
/* Fuente principal */
--font-sans: 'Inter', 'Inter var', -apple-system, BlinkMacSystemFont, sans-serif;

/* Para headings de marketing (hero sections) */
--font-display: 'Inter', sans-serif;
/* Nota: Linear usa Inter a peso 800 en heroes, NO una fuente display diferente */

/* Monoespaciada (IDs de issues, código) */
--font-mono: 'Fragment Mono', 'JetBrains Mono', 'Fira Code', monospace;
```

---

### 3.2 Escala tipográfica

| Token | px | Weight | Line-height | Letter-spacing | Uso observado |
|---|---|---|---|---|---|
| `text-2xs` | 10px | 500 | 1.4 | +0.05em | Micro labels, contadores |
| `text-xs` | 12px | 400 | 1.4 | 0 | Timestamps, metadata (`ago`, fechas) |
| `text-sm` | 13px | 400 | 1.5 | 0 | Sidebar items, labels de sección |
| `text-base` | 14px | 400 | 1.5 | 0 | **Texto principal de la app** |
| `text-md` | 15px | 400 | 1.6 | -0.01em | Cuerpo en paneles de detalle |
| `text-lg` | 16px | 600 | 1.4 | -0.01em | Título de sección, modal title |
| `text-xl` | 20px | 700 | 1.3 | -0.02em | Título de página / issue title |
| `text-2xl` | 28px | 700 | 1.2 | -0.02em | Headings de dashboard |
| `text-hero` | 62–80px | 800 | 1.05 | -0.04em | Hero de marketing (MUY tight) |

**Reglas observadas:**
- El texto de la app vive en 13–15px, casi nunca más
- IDs de issues (ENG-139) → `font-mono`, `text-xs`, `color: var(--text-secondary)`
- Labels de sección en sidebar → 11px, uppercase, weight 600, letter +0.08em
- Título de issue en el panel → 20px, weight 600–700, color blanco
- Hero marketing → Inter 800 con letter-spacing muy negativo (-0.04em)

---

### 3.3 Jerarquía visual en pantalla (app)

```
[TOPBAR — breadcrumb 13px gris → título 14px blanco]
  │
  ├─ [GROUP HEADER — "In Review  12" → 13px, weight 500, gris]
  │    ├─ [FILA ISSUE — 14px blanco, ID gris mono 12px]
  │    ├─ [FILA ISSUE]
  │    └─ [FILA ISSUE]
  │
  └─ [PANEL DETALLE (derecha)]
       ├─ [Título issue — 20px, weight 600]
       ├─ [Descripción — 14px, color secondary]
       └─ [Metadata label — 13px gris | valor — 13px blanco]
```

---

## 4. ESPACIADO Y LAYOUT

### 4.1 Unidad base: 4px

```
4px  → gap entre ícono y texto en items
8px  → padding lateral de items de sidebar
12px → padding lateral del sidebar
16px → padding estándar de secciones
20px → margen entre grupos
24px → padding de modales y paneles
32px → separación de secciones grandes
```

---

### 4.2 Layout principal — 3 columnas observadas

> ✅ Confirmado en `15_lista_issues.png` y `46_badges_tags.png`

```
┌──────────────────────────────────────────────────────────────────┐
│  SIDEBAR (220–240px)  │  MAIN CONTENT           │  DETAIL PANEL  │
│  ────────────────────  │  ─────────────────────  │  (320–400px)  │
│  Logo + workspace      │  TOPBAR (tabs, filtros)  │  Issue title   │
│  ────────────────────  │  ─────────────────────  │  Metadata      │
│  Inbox            [1]  │  [group header]          │  Status        │
│  My Issues             │    □ ENG-139 Título...   │  Priority      │
│  Reviews               │    □ ENG-416 Título...   │  Assignee      │
│  ────────────────────  │  [group header]          │  Labels        │
│  Workspace ▼           │    ─── ENG-811 Título... │  Cycle         │
│    Initiatives         │    ─── ENG-810 Título... │  ──────────── │
│    Projects            │                          │  Activity      │
│    Views               │                          │  Comments      │
│    More                │                          │               │
│  ────────────────────  │                          │               │
│  Your teams ▼          │                          │               │
│    Engineering ▼  [39] │                          │               │
│    Triage              │                          │               │
└──────────────────────────────────────────────────────────────────┘
```

| Zona | Dimensión |
|---|---|
| Sidebar | 220–240px fijo |
| Sidebar padding | 12px horizontal, 8px vertical |
| Topbar altura | 44–48px |
| Item de sidebar | 32px alto |
| Fila de issue | 36–38px alto |
| Panel de detalle | 320–400px |
| Content padding | 0 (sin padding, tabla edge-to-edge) |

---

### 4.3 Colores por zona

```css
.app-shell     { background: var(--bg-app); }          /* #0d0d0f */
.sidebar       { background: var(--bg-sidebar);         /* #141418 */
                 border-right: 1px solid var(--border-subtle); }
.topbar        { background: var(--bg-sidebar);
                 border-bottom: 1px solid var(--border-subtle); }
.content-area  { background: var(--bg-app); }
.detail-panel  { background: var(--bg-sidebar);
                 border-left: 1px solid var(--border-subtle); }
```

---

## 5. BORDES Y SOMBRAS

### 5.1 Border-radius

> ✅ Observado en capturas: inputs ~6px, cards ~8-10px, modales ~10-12px

| Token | Valor | Uso |
|---|---|---|
| `radius-xs` | 3px | Badges pequeños inline |
| `radius-sm` | 4px | Tags de una palabra |
| `radius-md` | 6px | Inputs, botones, items |
| `radius-lg` | 8px | Cards pequeñas, dropdowns |
| `radius-xl` | 10px | Cards grandes, pricing cards |
| `radius-2xl` | 12px | Modales |
| `radius-full` | 9999px | Avatares, toggles, pills |

---

### 5.2 Bordes

```css
/* Borde por defecto de cards y paneles */
border: 1px solid var(--border-default);   /* rgba(255,255,255,0.10) */

/* Borde de inputs (más visible) */
border: 1px solid var(--border-strong);    /* rgba(255,255,255,0.18) */

/* Borde de foco */
border: 1px solid var(--border-focus);     /* #5e6ad2 */
```

**Regla absoluta**: Los bordes son siempre **1px**. Sin excepción.

---

### 5.3 Sombras — contexto de uso

```css
/* Tooltip */
box-shadow: var(--shadow-xs);   /* 0 1px 2px rgba(0,0,0,0.4) */

/* Dropdown, menú contextual */
box-shadow: var(--shadow-md);   /* 0 4px 20px rgba(0,0,0,0.6) */

/* Modal flotante */
box-shadow: var(--shadow-lg);   /* 0 8px 40px rgba(0,0,0,0.7) */

/* Modal grande / command palette */
box-shadow: var(--shadow-xl);   /* 0 20px 80px rgba(0,0,0,0.8) */
```

---

## 6. ESTRUCTURA DE LA APP

```html
<div id="app" class="app-shell">
  <!-- Sidebar izquierdo -->
  <aside class="sidebar">
    <div class="sidebar-header">   <!-- logo + workspace switcher -->
    <nav class="sidebar-nav">      <!-- items de navegación -->
    <div class="sidebar-footer">   <!-- perfil + settings -->
  </aside>

  <!-- Área principal -->
  <div class="main-area">
    <header class="topbar">        <!-- breadcrumb + tabs + acciones -->
    <div class="content-wrapper">
      <main class="content-area">  <!-- tabla / lista principal -->
      <aside class="detail-panel"> <!-- panel de detalle (opcional, condicional) -->
    </div>
  </div>
</div>
```

---

## 7. NAVEGACIÓN — SIDEBAR

> ✅ Verificado con `15_lista_issues.png` y `46_badges_tags.png`

### 7.1 Estructura observada real

```
[Logo Linear + "Vast.craft" ▼]    ← workspace switcher, 14px, con dropdown
[🔍 ícono búsqueda] [✏️ ícono compose]   ← actions top-right del sidebar header

Inbox                              ← nav item + badge "1" (rojo)
My Issues                          ← nav item
Reviews                            ← nav item

── (divider) ──

Workspace ▼                        ← section collapsible, label gris
  Initiatives
  Projects
  Views
  More

── (divider) ──

Favoritos ▼                        ← section
  ★ Faster app launch              ← item favorito (estrella amarilla)
  × Agent tasks
  × UI Refresh
  × Agents Insights

── (divider) ──

Your teams ▼                       ← section
  Engineering ▼       [39]         ← team con badge de count
  Triage                           ← subitem
```

### 7.2 Estilos de items del sidebar

```css
/* ─── ITEM BASE ───────────────────────────────────── */
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 8px;
  margin: 0 4px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);      /* gris #8a8f98 */
  cursor: pointer;
  transition: background 80ms ease-out, color 80ms ease-out;
  user-select: none;
}

/* Hover */
.sidebar-item:hover {
  background: rgba(255,255,255,0.05);
  color: var(--text-primary);
}

/* Activo */
.sidebar-item.active {
  background: rgba(255,255,255,0.08);
  color: var(--text-primary);
  font-weight: 500;
}

/* Ícono */
.sidebar-item .icon {
  width: 16px;
  height: 16px;
  opacity: 0.5;
  flex-shrink: 0;
}
.sidebar-item:hover .icon,
.sidebar-item.active .icon { opacity: 0.85; }

/* Badge de count (ej: "39", "1") */
.sidebar-item .count-badge {
  margin-left: auto;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary);
  background: rgba(255,255,255,0.06);
  padding: 1px 5px;
  border-radius: 9999px;
}

/* ─── LABEL DE SECCIÓN ─────────────────────────────── */
.sidebar-section-label {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  cursor: pointer;
  user-select: none;
}
.sidebar-section-label .chevron {
  width: 12px;
  height: 12px;
  opacity: 0.5;
  transition: transform 150ms;
}
.sidebar-section-label.collapsed .chevron {
  transform: rotate(-90deg);
}

/* ─── DIVIDER ──────────────────────────────────────── */
.sidebar-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 4px 12px;
}

/* ─── HEADER DEL SIDEBAR ───────────────────────────── */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.workspace-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  border-radius: 6px;
  padding: 4px 6px;
  margin: -4px -6px;
}
.workspace-switcher:hover {
  background: rgba(255,255,255,0.05);
}
```

---

## 8. TOPBAR Y TABS

> ✅ Observado en `15_lista_issues.png`

### 8.1 Estructura del topbar

```
[← →] [breadcrumb: Engineering › Active issues]    [iconos de acción →]
─────────────────────────────────────────────────────────────────────
[Engineering] [All issues] [Active ●] [Backlog] [Recent]   [≡ Filter]
```

### 8.2 Estilos

```css
/* Topbar completo */
.topbar {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-sidebar);
}

/* Fila de breadcrumb */
.topbar-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 44px;
  padding: 0 16px;
  font-size: 13px;
  color: var(--text-secondary);
}
.topbar-breadcrumb .separator { opacity: 0.4; }
.topbar-breadcrumb .current   { color: var(--text-primary); font-weight: 500; }

/* Fila de tabs */
.topbar-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 12px;
  height: 36px;
}

/* Tab individual */
.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 80ms, color 80ms;
  user-select: none;
}
.tab:hover {
  background: rgba(255,255,255,0.05);
  color: var(--text-primary);
}
.tab.active {
  background: rgba(255,255,255,0.08);
  color: var(--text-primary);
  font-weight: 500;
}
```

---

## 9. TABLAS Y LISTAS DE ISSUES

> ✅ Verificado con `15_lista_issues.png` — es la pantalla más importante de la app

### 9.1 Anatomía de una fila de issue

```
[checkbox] [priority-icon] [status-icon] [issue-id] [título issue] ......... [tag] [asignado]
   16px        16px            16px        60px       flex: 1                  tag    avatar
```

### 9.2 Estilos

```css
/* ─── CONTENEDOR ──────────────────────────────────── */
.issue-list {
  width: 100%;
  font-size: 13px;
}

/* ─── HEADER DE GRUPO ("In Review  12") ───────────── */
.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}
.group-header .count {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 400;
  margin-left: 2px;
}
.group-header .chevron {
  width: 14px;
  height: 14px;
  opacity: 0.4;
  transition: transform 150ms;
}

/* ─── FILA DE ISSUE ────────────────────────────────── */
.issue-row {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 60ms ease-out;
}

.issue-row:hover {
  background: var(--bg-row-hover);    /* #1a1a1e */
}

.issue-row.selected {
  background: var(--bg-row-selected); /* rgba(94,106,210,0.08) */
}

/* Checkbox (visible solo en hover/selected) */
.issue-row .checkbox {
  width: 16px;
  height: 16px;
  opacity: 0;
  transition: opacity 80ms;
  flex-shrink: 0;
}
.issue-row:hover .checkbox,
.issue-row.selected .checkbox { opacity: 1; }

/* Ícono de prioridad (barras) */
.issue-row .priority-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  opacity: 0.6;
}

/* Ícono de estado (círculo con color) */
.issue-row .status-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* ID de issue — monospace, gris */
.issue-row .issue-id {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-tertiary);
  flex-shrink: 0;
  width: 58px;
}

/* Título del issue */
.issue-row .title {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Tag de categoría (derecha) */
.issue-row .tag {
  font-size: 11px;
  color: var(--text-tertiary);
  background: rgba(255,255,255,0.05);
  padding: 2px 7px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ─── ESTADO VACÍO ─────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 24px;
  gap: 12px;
}
.empty-state .icon    { width: 32px; height: 32px; opacity: 0.25; }
.empty-state .message { font-size: 14px; color: var(--text-secondary); }
.empty-state .hint    { font-size: 13px; color: var(--text-tertiary); }
```

---

## 10. PANEL DE DETALLE

> ✅ Observado en `13_panel_detalle_issue.png` y `46_badges_tags.png`

### 10.1 Estructura del panel

```
[← →  nombre-issue  ★  ···]     [02/145 ↑↓]     [ENG-2749  🔗  📋  ⤢]
──────────────────────────────────────────────────────────────────────
TÍTULO DEL ISSUE (20px, bold)
Descripción / body (14px, secondary)

Activity
  [avatar] karri created the issue · 5min ago
  [avatar] karri 4 min ago: ...
  [avatar] Cursor...

[Message Cursor...]  [📎] [→]
──────────────────────────────────────────────────────────────────── (borde)
PANEL DERECHO (metadata):
  ○ In Progress               ← status con ícono circular
  ↑↑ Medium                   ← priority con ícono de barras
  [avatar] jori               ← asignado
  [avatar] Codex              ← asignado 2

  Labels:
  [• Maps]                    ← tag con dot de color

  Cycle:
  [ Cycle 144 ]               ← referencia al sprint
```

### 10.2 Estilos del panel

```css
.detail-panel {
  width: 360px;
  flex-shrink: 0;
  border-left: 1px solid var(--border-subtle);
  background: var(--bg-sidebar);
  overflow-y: auto;
}

/* Header del panel */
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 13px;
  color: var(--text-secondary);
}

/* Título del issue */
.detail-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  padding: 20px 16px 8px;
  line-height: 1.3;
}

/* Fila de metadata */
.meta-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  transition: background 80ms;
}
.meta-row:hover { background: rgba(255,255,255,0.04); }
.meta-row .icon { width: 16px; height: 16px; opacity: 0.7; }
.meta-row .value { color: var(--text-primary); }

/* Label de sección dentro del panel */
.detail-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  padding: 12px 16px 4px;
}

/* Activity */
.activity-item {
  display: flex;
  gap: 10px;
  padding: 8px 16px;
  font-size: 13px;
  color: var(--text-secondary);
}
.activity-item strong { color: var(--text-primary); }
.activity-item .time  { font-size: 12px; color: var(--text-tertiary); }

/* Input de mensaje */
.message-input {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 16px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-tertiary);
  cursor: text;
}
```

---

## 11. BOTONES

> ⚠️ CORRECCIÓN CRÍTICA verificada en capturas reales:
> **El botón primario de Linear es BLANCO con texto oscuro, NO azul/violeta.**
> El violeta (#5E6AD2) se usa solo para: toggles, checkboxes, focus rings, badges de acento.

### 11.1 Variantes

```css
/* ─── BASE ────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 6px;
  font-family: var(--font-sans);
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
  transition: background 100ms ease-out, opacity 100ms ease-out;
  border: none;
  outline: none;
}

/* ─── TAMAÑOS ─────────────────────────────────────── */
.btn-xs { height: 24px; padding: 0 8px;  font-size: 12px; border-radius: 4px; }
.btn-sm { height: 28px; padding: 0 10px; font-size: 13px; }
.btn-md { height: 32px; padding: 0 12px; font-size: 14px; } /* DEFAULT APP */
.btn-lg { height: 36px; padding: 0 14px; font-size: 14px; }
.btn-xl { height: 40px; padding: 0 18px; font-size: 15px; } /* MARKETING */

/* ─── PRIMARIO ─────────────────────────────────────── */
/* Fondo blanco, texto negro. El CTA principal. */
.btn-primary {
  background: #ffffff;
  color: #111111;
}
.btn-primary:hover {
  background: #f0f0f0;
}
.btn-primary:active { opacity: 0.85; }

/* ─── SECUNDARIO ──────────────────────────────────── */
/* Borde visible, fondo transparente o muy sutil */
.btn-secondary {
  background: rgba(255,255,255,0.06);
  color: var(--text-primary);
  border: 1px solid var(--border-strong);
}
.btn-secondary:hover {
  background: rgba(255,255,255,0.10);
}

/* ─── GHOST ──────────────────────────────────────── */
/* Sin borde ni fondo. Para acciones secundarias. */
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: none;
}
.btn-ghost:hover {
  background: rgba(255,255,255,0.06);
  color: var(--text-primary);
}

/* ─── ACENTO (uso muy específico) ────────────────── */
/* Solo para estados de acción importante no-CTA */
.btn-accent {
  background: var(--accent);
  color: #ffffff;
}
.btn-accent:hover { background: var(--accent-hover); }

/* ─── DESTRUCTIVO ─────────────────────────────────── */
.btn-danger {
  background: rgba(248,113,113,0.12);
  color: var(--color-error);
  border: 1px solid rgba(248,113,113,0.25);
}
.btn-danger:hover {
  background: rgba(248,113,113,0.20);
}

/* ─── ÍCONO SOLO ──────────────────────────────────── */
.btn-icon {
  padding: 0;
  width: 28px;
  height: 28px;
  background: transparent;
  color: var(--text-tertiary);
  border: none;
  border-radius: 6px;
}
.btn-icon:hover {
  background: rgba(255,255,255,0.06);
  color: var(--text-primary);
}

/* ─── DISABLED (todos los tipos) ─────────────────── */
.btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
  pointer-events: none;
}
```

---

## 12. FORMULARIOS E INPUTS

> ✅ Verificado con `51_contact_form.png` — formulario real de Linear

### 12.1 Input de texto

```css
/* ─── BASE ────────────────────────────────────────── */
.input {
  width: 100%;
  height: 36px;
  padding: 0 12px;
  background: var(--bg-input);              /* #161618 */
  border: 1px solid var(--border-strong);   /* rgba(255,255,255,0.18) */
  border-radius: 6px;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
  transition: border-color 100ms, box-shadow 100ms;
  -webkit-appearance: none;
}

/* Placeholder */
.input::placeholder {
  color: var(--text-tertiary);
}

/* Hover */
.input:hover:not(:focus):not(:disabled) {
  border-color: rgba(255,255,255,0.25);
}

/* Focus */
.input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-muted);
}

/* Error */
.input.is-error {
  border-color: var(--color-error);
  box-shadow: 0 0 0 3px rgba(248,113,113,0.15);
}

/* Disabled */
.input:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ─── TAMAÑOS ─────────────────────────────────────── */
.input-sm  { height: 28px; font-size: 13px; padding: 0 8px; }
.input-md  { height: 36px; font-size: 14px; padding: 0 12px; } /* DEFAULT */
.input-lg  { height: 44px; font-size: 15px; padding: 0 14px; } /* marketing forms */
```

### 12.2 Textarea

```css
.textarea {
  /* mismo estilo que .input */
  height: auto;
  min-height: 100px;
  padding: 10px 12px;
  resize: vertical;
  line-height: 1.6;
}
/* La textarea de Linear tiene resize handle visible en esquina inferior derecha */
```

### 12.3 Select (dropdown nativo)

```css
.select {
  /* mismo estilo que .input */
  cursor: pointer;
  /* Flecha nativa reemplazada con ícono SVG */
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,..."); /* chevron-down */
  background-repeat: no-repeat;
  background-position: right 10px center;
  background-size: 14px;
  padding-right: 32px;
}
```

### 12.4 Label

```css
.form-label {
  display: block;
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

/* Nota: en Linear el label está ENCIMA del input, sin asterisco visible */
/* El label es pequeño (13px) y gris — no blanco */
```

### 12.5 Form group

```css
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.form-hint  { font-size: 12px; color: var(--text-tertiary); }
.form-error { font-size: 12px; color: var(--color-error); margin-top: 4px; }
```

### 12.6 Checkbox

```css
.checkbox {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: transparent;
  cursor: pointer;
  appearance: none;
  transition: background 100ms, border-color 100ms;
  flex-shrink: 0;
}
.checkbox:checked {
  background: var(--accent);              /* violeta cuando activo */
  border-color: var(--accent);
  /* checkmark blanco via background-image SVG */
}
.checkbox:hover:not(:checked) {
  border-color: rgba(255,255,255,0.35);
}
```

### 12.7 Toggle Switch

> ✅ Observado en `62_pricing.png`: toggle azul/violeta cuando ON

```css
.toggle-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.toggle {
  position: relative;
  width: 36px;
  height: 20px;
  border-radius: 9999px;
  background: rgba(255,255,255,0.12);    /* OFF: gris muy suave */
  transition: background 150ms ease-out;
  flex-shrink: 0;
}

.toggle.is-on {
  background: var(--accent);             /* ON: violeta #5e6ad2 */
}

.toggle::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 9999px;
  background: white;
  top: 2px;
  left: 2px;
  transition: transform 150ms ease-out;
  box-shadow: 0 1px 3px rgba(0,0,0,0.4);
}

.toggle.is-on::after {
  transform: translateX(16px);
}
```

---

## 13. BADGES Y ESTADOS

> ✅ Observado en `46_badges_tags.png`, `15_lista_issues.png`, `13_panel_detalle_issue.png`

### 13.1 Badge base

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  user-select: none;
}

/* Pill (más redondeado) */
.badge-pill { border-radius: 9999px; }
```

### 13.2 Badges de estado con ícono circular

El estado en Linear se muestra como **ícono SVG circular + texto**, no solo texto en un badge.

```css
/* Contenedor estado */
.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-primary);
}

/* El ícono es un SVG circular de 16x16 con el color del estado */
.status-icon-todo        { color: #6b7280; }  /* círculo outline */
.status-icon-inprogress  { color: #f59e0b; }  /* círculo half-filled */
.status-icon-inreview    { color: #4ade80; }  /* círculo con check tenue */
.status-icon-done        { color: #22c55e; }  /* círculo filled con check */
.status-icon-cancelled   { color: #6b7280; }  /* círculo con X */
```

### 13.3 Tags / etiquetas de color

```css
/* Tag con dot de color (observado: "• Maps", "Performance", "iOS") */
.label-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary);
  cursor: pointer;
}
.label-tag:hover {
  background: rgba(255,255,255,0.10);
  color: var(--text-primary);
}
.label-tag .dot {
  width: 7px;
  height: 7px;
  border-radius: 9999px;
  flex-shrink: 0;
  /* background-color: [color dinámico del label] */
}
```

### 13.4 Notification count badge (número rojo)

```css
.notif-badge {
  position: absolute;
  top: -3px; right: -3px;
  min-width: 15px; height: 15px;
  padding: 0 3px;
  border-radius: 9999px;
  background: var(--color-error);
  color: white;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--bg-sidebar);
}
```

---

## 14. CARDS / TARJETAS

> ✅ Verificado en `62_pricing.png` (pricing cards reales)

### 14.1 Card estándar

```css
.card {
  background: var(--bg-card);              /* #1c1c1e */
  border: 1px solid var(--border-default); /* rgba(255,255,255,0.10) */
  border-radius: 10px;
  padding: 20px;
  transition: border-color 150ms, transform 150ms;
}

.card:hover {
  border-color: var(--border-strong);
}

/* Card elevada (pricing destacado, observado en Business card) */
.card-elevated {
  background: #1e1e24;
  border-color: rgba(255,255,255,0.18);
  box-shadow: var(--shadow-md);
}
```

### 14.2 Card de feature (homepage)

```css
.feature-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 28px 24px;
  cursor: pointer;
  transition: border-color 150ms;
  position: relative;
  overflow: hidden;
}
.feature-card:hover {
  border-color: var(--border-strong);
}

/* Label de categoría encima del título */
.feature-card .category {
  font-size: 12px;
  font-weight: 500;
  color: var(--accent);
  margin-bottom: 10px;
}

/* Título del feature card */
.feature-card .title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.35;
}

/* Flecha de navegación (→) en esquina inferior derecha */
.feature-card .arrow {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 20px;
  height: 20px;
  opacity: 0.4;
}
```

---

## 15. MODALES Y PANELES

> ✅ Observado en `13_panel_detalle_issue.png`

### 15.1 Overlay

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);   /* rgba(0,0,0,0.65) */
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fade-in 120ms ease-out;
}
```

### 15.2 Modal

```css
.modal {
  background: var(--bg-modal);             /* #1c1c1e */
  border: 1px solid var(--border-default);
  border-radius: 12px;
  box-shadow: var(--shadow-xl);
  width: 560px;
  max-width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  animation: slide-up 150ms ease-out;
}

.modal-sm { width: 400px; }
.modal-lg { width: 720px; }

/* Header */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
}
.modal-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

/* Body */
.modal-body { padding: 20px; }

/* Footer */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-subtle);
}
```

### 15.3 Drawer (panel lateral deslizable)

```css
.drawer {
  position: fixed;
  top: 0; right: 0;
  height: 100vh;
  width: 480px;
  max-width: 92vw;
  background: var(--bg-card);
  border-left: 1px solid var(--border-default);
  box-shadow: var(--shadow-xl);
  overflow-y: auto;
  z-index: 40;
  animation: slide-in-right 180ms ease-out;
}
```

---

## 16. AVATARES E IMÁGENES

### 16.1 Avatar

```css
/* Tamaños */
.avatar-xs  { width: 18px; height: 18px; font-size: 8px;  }
.avatar-sm  { width: 24px; height: 24px; font-size: 10px; }
.avatar-md  { width: 28px; height: 28px; font-size: 11px; } /* app — observado */
.avatar-lg  { width: 36px; height: 36px; font-size: 13px; }
.avatar-xl  { width: 48px; height: 48px; font-size: 16px; }

/* Base */
.avatar {
  border-radius: 9999px;
  overflow: hidden;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  user-select: none;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }

/* Sin foto — iniciales */
.avatar-initials {
  background: var(--accent-muted);
  color: var(--accent);
}

/* Grupo de avatares apilados */
.avatar-group { display: flex; }
.avatar-group .avatar { margin-left: -6px; border: 2px solid var(--bg-sidebar); }
.avatar-group .avatar:first-child { margin-left: 0; }
```

### 16.2 Thumbnail de imagen

```css
.thumbnail {
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-card);
  object-fit: cover;
  border: 1px solid var(--border-subtle);
}
.thumbnail-sm { width: 40px;  height: 40px;  }
.thumbnail-md { width: 80px;  height: 60px;  }
.thumbnail-lg { width: 160px; height: 120px; }

/* Hover */
.thumbnail { transition: opacity 100ms; }
.thumbnail:hover { opacity: 0.8; cursor: zoom-in; }
```

### 16.3 Galería

```css
.image-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 6px;
}
.image-gallery .thumbnail { width: 100%; aspect-ratio: 1; }
```

---

## 17. ÍCONOS

### 17.1 Librería

**Usar: Lucide Icons** (`lucide-vue-next` para Vue 3)
- Siempre stroke, nunca filled
- `stroke-width="1.5"` (default Lucide)
- NO usar Heroicons, FontAwesome ni Material Icons

### 17.2 Tamaños

| Contexto | Tamaño |
|---|---|
| En badges inline | 12px |
| Sidebar, filas de tabla | 16px ← ESTÁNDAR |
| Topbar, botones de acción | 16–18px |
| Empty state, ilustración | 28–32px |

### 17.3 Color y opacidad

```css
/* Default — en sidebar, filas */
color: var(--text-tertiary);
opacity: 0.55;

/* Hover / activo */
color: var(--text-primary);
opacity: 0.85;

/* Acento */
color: var(--accent);
opacity: 1;

/* Destructivo */
color: var(--color-error);
opacity: 1;
```

---

## 18. MENÚS CONTEXTUALES Y DROPDOWNS

> ✅ Observado en `20_menu_contextual_workspace.png` y `15_nav_product_dropdown.png`

```css
.dropdown {
  background: var(--bg-card);             /* #1c1c1e */
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  padding: 4px;
  min-width: 180px;
  animation: fade-in-scale 100ms ease-out;
  z-index: 100;
}

/* Item */
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  padding: 0 8px;
  border-radius: 5px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 60ms, color 60ms;
}
.dropdown-item:hover {
  background: rgba(255,255,255,0.07);
  color: var(--text-primary);
}

/* Ícono en item */
.dropdown-item .icon {
  width: 14px; height: 14px; opacity: 0.6;
}

/* Shortcut key hint */
.dropdown-item .shortcut {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

/* Destructivo */
.dropdown-item.danger { color: var(--color-error); }
.dropdown-item.danger:hover { background: rgba(248,113,113,0.08); }

/* Separador */
.dropdown-separator {
  height: 1px;
  background: var(--border-subtle);
  margin: 4px 0;
}

/* Label de sección */
.dropdown-section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  padding: 8px 8px 3px;
}
```

---

## 19. COMMAND PALETTE

> ✅ Observado en `17_command_palette.png` — muy minimalista

```css
.command-palette {
  position: fixed;
  top: 18%;
  left: 50%;
  transform: translateX(-50%);
  width: 540px;
  max-width: 90vw;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  z-index: 200;
  animation: fade-in-scale 120ms ease-out;
}

/* Input de búsqueda */
.command-palette-input {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
}
.command-palette-input .search-icon {
  width: 16px; height: 16px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}
.command-palette-input input {
  border: none;
  background: transparent;
  font-size: 15px;
  color: var(--text-primary);
  flex: 1;
  outline: none;
}
.command-palette-input input::placeholder {
  color: var(--text-tertiary);
}

/* Lista de resultados */
.command-results {
  max-height: 340px;
  overflow-y: auto;
  padding: 4px;
}

/* Item de resultado */
.command-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 34px;
  padding: 0 10px;
  border-radius: 6px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 60ms;
}
.command-item:hover,
.command-item.selected {
  background: rgba(255,255,255,0.07);
  color: var(--text-primary);
}
```

---

## 20. NOTIFICACIONES Y TOASTS

```css
/* Posición */
.toast-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 300;
}

/* Toast */
.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 240px;
  max-width: 360px;
  padding: 12px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  font-size: 13px;
  color: var(--text-primary);
  animation: slide-up 200ms ease-out;
}

/* Variantes — borde lateral de color */
.toast-success { border-left: 3px solid var(--color-success); }
.toast-error   { border-left: 3px solid var(--color-error);   }
.toast-warning { border-left: 3px solid var(--color-warning);  }
.toast-info    { border-left: 3px solid var(--color-info);     }
```

---

## 21. ANIMACIONES Y TRANSICIONES

### Reglas absolutas

| Tipo de movimiento | Duración | Easing |
|---|---|---|
| Hover simple (bg, color) | 60–80ms | `ease-out` |
| Aparición de dropdown/tooltip | 100–120ms | `ease-out` |
| Modal, fade-in | 120–150ms | `ease-out` |
| Drawer, slide | 180–200ms | `ease-out` |
| Toggle, checkbox | 150ms | `ease-out` |

**Regla de oro**: Nada supera 200ms. Linear se percibe instantáneo.
**NO usar**: `ease-in-out` (demasiado lerdo en el inicio), `spring`, `bounce`, `cubic-bezier` complejos.

### Keyframes

```css
@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes fade-in-scale {
  from { opacity: 0; transform: scale(0.97); }
  to   { opacity: 1; transform: scale(1); }
}
@keyframes slide-up {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes slide-in-right {
  from { opacity: 0; transform: translateX(16px); }
  to   { opacity: 1; transform: translateX(0); }
}
```

---

## 22. ESTADOS DE CARGA

### Skeleton screen

```css
.skeleton {
  background: linear-gradient(
    90deg,
    rgba(255,255,255,0.04) 25%,
    rgba(255,255,255,0.08) 50%,
    rgba(255,255,255,0.04) 75%
  );
  background-size: 200% 100%;
  border-radius: 4px;
  animation: shimmer 1.4s ease-in-out infinite;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-row     { height: 36px; margin-bottom: 1px; }
.skeleton-text    { height: 13px; margin-bottom: 6px; }
.skeleton-title   { height: 18px; width: 55%; margin-bottom: 10px; }
.skeleton-avatar  { width: 28px; height: 28px; border-radius: 9999px; }
```

### Spinner

```css
.spinner {
  width: 14px; height: 14px;
  border: 1.5px solid rgba(255,255,255,0.15);
  border-top-color: var(--text-secondary);
  border-radius: 9999px;
  animation: spin 500ms linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

---

## 23. TOOLTIPS

> ✅ Observado en `25_tooltip_new_issue.png`

```css
.tooltip {
  position: absolute;
  bottom: calc(100% + 5px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 5px;
  padding: 5px 9px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  pointer-events: none;
  z-index: 500;
  box-shadow: var(--shadow-sm);
  animation: fade-in 80ms ease-out;
}

/* Shortcut key dentro del tooltip */
.tooltip .kbd {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  background: rgba(255,255,255,0.06);
  padding: 1px 5px;
  border-radius: 3px;
  margin-left: 6px;
}
```

---

## 24. SCROLLBAR

```css
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.10);
  border-radius: 9999px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.18);
}

/* Firefox */
* { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.10) transparent; }
```

---

## 25. RESPONSIVE Y BREAKPOINTS

| Nombre | Valor | Sidebar |
|---|---|---|
| `sm` | < 768px | Drawer overlay (oculto por defecto) |
| `md` | 768–1024px | Colapsado (solo íconos 44px) |
| `lg` | > 1024px | Expandido 220–240px (default) |

---

## 26. ELEMENTOS PENDIENTES DE DEFINIR

> Requieren cuenta trial de Linear o investigación adicional.

| Elemento | Prioridad | Notas |
|---|---|---|
| Date picker | Alta | Usar Vue Datepicker con estilos del manual |
| Rich text editor | Alta | Tiptap con dark theme custom |
| Gráficos / charts | Alta | ECharts con colores del manual |
| File upload drag & drop | Media | Crear con nuestro propio estilo |
| Progress bar / steps | Media | Basado en principios de este manual |
| Tabs avanzados con contenido | Media | Basado en estilos de topbar tabs |
| Breadcrumbs expandibles | Baja | Basado en topbar breadcrumb |
| Filtros avanzados (Linear tiene sistema complejo) | Alta | Requiere pantallazos con login |
| Modal de creación de registro | Alta | Requiere login Linear |
| Loading states internos de la app | Media | Requiere login Linear |

---

## APÉNDICE A — globals.css completo (pegar en el proyecto)

```css
/* ─── RESET MÍNIMO ─────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; padding: 0; }
button { cursor: pointer; }
a { color: inherit; text-decoration: none; }

/* ─── VARIABLES MODO OSCURO (default) ──────────────── */
:root {
  /* Fondos */
  --bg-app:          #0d0d0f;
  --bg-sidebar:      #141418;
  --bg-card:         #1c1c1e;
  --bg-card-hover:   #242428;
  --bg-row-hover:    #1a1a1e;
  --bg-row-selected: rgba(94,106,210,0.08);
  --bg-input:        #161618;
  --bg-modal:        #1c1c1e;
  --bg-overlay:      rgba(0,0,0,0.65);

  /* Textos */
  --text-primary:    #ffffff;
  --text-secondary:  #8a8f98;
  --text-tertiary:   #5a5f6a;
  --text-disabled:   #3a3f4a;
  --text-inverse:    #0d0d0f;
  --text-mono:       #8a8f98;

  /* Bordes */
  --border-subtle:   rgba(255,255,255,0.06);
  --border-default:  rgba(255,255,255,0.10);
  --border-strong:   rgba(255,255,255,0.18);
  --border-focus:    #5e6ad2;

  /* Acento */
  --accent:          #5e6ad2;
  --accent-hover:    #6e7ae2;
  --accent-active:   #4e5ac2;
  --accent-muted:    rgba(94,106,210,0.12);
  --accent-border:   rgba(94,106,210,0.35);

  /* Estados */
  --color-success:   #4ade80;
  --color-warning:   #f59e0b;
  --color-error:     #f87171;
  --color-info:      #60a5fa;

  /* Sombras */
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.4);
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.5);
  --shadow-md: 0 4px 20px rgba(0,0,0,0.6);
  --shadow-lg: 0 8px 40px rgba(0,0,0,0.7);
  --shadow-xl: 0 20px 80px rgba(0,0,0,0.8);

  /* Tipografía */
  --font-sans:  'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono:  'Fragment Mono', 'JetBrains Mono', monospace;

  /* Radios */
  --radius-xs:   3px;
  --radius-sm:   4px;
  --radius-md:   6px;
  --radius-lg:   8px;
  --radius-xl:   10px;
  --radius-2xl:  12px;
  --radius-full: 9999px;

  /* Scrollbar */
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.10) transparent;
}

/* ─── BASE DE LA APP ────────────────────────────────── */
body {
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  background: var(--bg-app);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ─── SCROLLBAR ─────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.10);
  border-radius: 9999px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.18);
}

/* ─── MODO CLARO ────────────────────────────────────── */
[data-theme="light"] {
  --bg-app:          #f5f5f5;
  --bg-sidebar:      #ebebeb;
  --bg-card:         #ffffff;
  --bg-card-hover:   #f8f8f8;
  --bg-row-hover:    #f2f2f2;
  --bg-row-selected: rgba(94,106,210,0.06);
  --bg-input:        #ffffff;
  --bg-modal:        #ffffff;
  --bg-overlay:      rgba(0,0,0,0.45);
  --text-primary:    #111111;
  --text-secondary:  #666b75;
  --text-tertiary:   #9ca3af;
  --text-disabled:   #d1d5db;
  --text-inverse:    #ffffff;
  --border-subtle:   rgba(0,0,0,0.05);
  --border-default:  rgba(0,0,0,0.09);
  --border-strong:   rgba(0,0,0,0.16);
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.06);
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 20px rgba(0,0,0,0.10);
  --shadow-lg: 0 8px 40px rgba(0,0,0,0.14);
  --shadow-xl: 0 20px 80px rgba(0,0,0,0.18);
}
```

---

## APÉNDICE B — Fuentes de referencia

- Capturas reales: `screenshots/` (88 imágenes) — ver `screenshots/INDEX.md`
- [Linear Blog — Redesign](https://linear.app/now/how-we-redesigned-the-linear-ui)
- [Linear Brand](https://linear.app/brand)
- [Linear Changelog — New UI](https://linear.app/changelog/2024-03-20-new-linear-ui)
- [Linear Design: SaaS Trend — LogRocket](https://blog.logrocket.com/ux-design/linear-design/)
- [Rise of Linear Style Design — Medium](https://medium.com/design-bootcamp/the-rise-of-linear-style-design-origins-trends-and-techniques-4fd96aab7646)
- [Linear Design System — Figma Community](https://www.figma.com/community/file/1222872653732371433/linear-design-system)
- [Linear Typography — Typ.io](https://typ.io/s/2jmp)

> **Versión**: 2.0 — Actualizado con datos reales de 88 capturas de Linear.app
> **Pendiente**: Sección 26 — requiere cuenta trial de Linear para capturar elementos internos
