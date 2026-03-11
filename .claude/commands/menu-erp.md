# Skill: Diseño de Menú — ERP Origen Silvestre

> Guía completa del sidebar de navegación del ERP.
> Referencia visual: Linear.app sidebar (modo claro).
> Componente: `frontend/app/src/components/AppSidebar.vue`
> Datos: tabla `sys_menu` en Hostinger `u768061575_os_integracion`

---

## 1. ESTRUCTURA DEL SIDEBAR

```
┌──────────────────────────────┐  232px fijo
│ [OS] Origen Silvestre  🔍 ＋ │  48px — header workspace
├──────────────────────────────┤  1px border-subtle
│  Dashboard                   │  30px — nav-item fijo
├──────────────────────────────┤  divider
│  • TERCEROS          ›       │  28px — módulo (uppercase, 11px, dot de color)
│    Clientes                  │  30px — sub-item (indent 22px)
│    Proveedores               │
│    Empleados                 │
│  • VENTAS            ›       │  módulo expandido
│    Resumen Facturación  ←    │  sub-item activo (negrita, bg sutil)
│    ...                       │
├──────────────────────────────┤  divider
│  Análisis de datos           │  nav-item fijo (herramientas)
│  Agente IA                   │
├──────────────────────────────┤  border-top
│  [S] Santiago        ⚙️      │  30px — footer perfil
└──────────────────────────────┘
```

---

## 2. TABLA EN HOSTINGER: `sys_menu`

BD: `u768061575_os_integracion`

```sql
CREATE TABLE sys_menu (
  id              BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  uid             VARCHAR(60)      NOT NULL,          -- slug único: 'ventas_facturas'
  empresa         VARCHAR(50)      NOT NULL DEFAULT 'Ori_Sil_2',
  id_padre        BIGINT UNSIGNED  NULL DEFAULT NULL, -- NULL = categoría raíz
  titulo          VARCHAR(100)     NOT NULL,
  icono           VARCHAR(80)      NULL,              -- nombre ícono Lucide
  ruta_vue        VARCHAR(255)     NULL,              -- solo en hojas: '/ventas/facturas'
  orden           SMALLINT         NOT NULL DEFAULT 0,
  activo          TINYINT(1)       NOT NULL DEFAULT 1,
  color           VARCHAR(20)      NULL,              -- hex del dot de categoría
  usuario_creador VARCHAR(100)     NOT NULL DEFAULT 'Santi',
  usuario_ult_mod VARCHAR(100)     NULL,
  fecha_creacion  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_ult_mod   DATETIME         NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_uid_empresa (uid, empresa),
  KEY idx_id_padre (id_padre),
  KEY idx_empresa_activo (empresa, activo, orden)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Registros actuales**: 36 (7 módulos raíz + 29 submenús), empresa `Ori_Sil_2`

---

## 3. MÓDULOS Y SUBMENÚS ACTUALES

| Módulo | Color | Submenús |
|---|---|---|
| Terceros | `#60a5fa` | Clientes, Proveedores, Empleados |
| Ventas | `#4ade80` | Resumen Facturación, Resumen Remisiones, Mercancía en consignación, Pedidos pendientes, Facturas, Remisiones, Cotizaciones |
| Tareas | `#f59e0b` | Registrar, Esta semana, Hoy, Mañana, Ayer, Todas las mías, Todo el equipo |
| CRM | `#a78bfa` | Oportunidades, Tareas CRM, Notas |
| Producción | `#fb923c` | Resumen producción, Órdenes de producción |
| Compras | `#34d399` | Resumen facturas, Resumen remisiones, Órdenes, Remisiones, Facturas |
| Herramientas | `#94a3b8` | Análisis de datos (Metabase), Hablar con agente IA |

---

## 4. ÍCONOS USADOS (Lucide)

| Módulo | Ícono |
|---|---|
| Terceros | `Users` |
| Ventas | `TrendingUp` |
| Tareas | `CheckSquare` |
| CRM | `Target` |
| Producción | `Factory` |
| Compras | `ShoppingCart` |
| Herramientas | `Wrench` |
| Dashboard | `LayoutDashboard` |
| Buscar | `Search` |
| Nueva tarea | `Plus` |
| Settings | `Settings` |

Librería: `lucide-vue-next`. Tamaño en sidebar: **15px**.

---

## 5. CSS CLAVE DEL SIDEBAR

```css
/* Contenedor */
.sidebar {
  width: 232px; height: 100vh;
  background: var(--bg-sidebar);           /* #f9f9f9 modo claro */
  border-right: 1px solid var(--border-subtle);
  display: flex; flex-direction: column; overflow: hidden; flex-shrink: 0;
}

/* Header workspace */
.sidebar-header {
  display: flex; align-items: center; justify-content: space-between;
  height: 48px; padding: 0 12px;
  border-bottom: 1px solid var(--border-subtle);
}

/* Logo workspace */
.ws-logo {
  width: 22px; height: 22px; border-radius: var(--radius-sm);
  background: var(--accent); color: white;
  font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}

/* Nav items (dashboard, herramientas fijas) */
.nav-item {
  display: flex; align-items: center; gap: 7px;
  height: 30px; padding: 0 8px; border-radius: var(--radius-md);
  font-size: 13px; font-weight: 400; color: var(--text-secondary);
  cursor: pointer; text-decoration: none; border: none; background: transparent;
  transition: background 70ms, color 70ms;
}
.nav-item:hover, .nav-item.active {
  background: rgba(0,0,0,0.05);   /* modo claro */
  color: var(--text-primary);
}
.nav-item.active { font-weight: 500; }

/* Módulo header (categoría) */
.nav-module-header {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; height: 28px; padding: 0 8px;
  border-radius: var(--radius-md); border: none; background: transparent; cursor: pointer;
  transition: background 70ms;
}
.nav-module-titulo {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--text-tertiary);
}

/* Dot de color del módulo */
.nav-module-dot { width: 7px; height: 7px; border-radius: 9999px; flex-shrink: 0; }

/* Chevron animado */
.nav-chevron { transition: transform 150ms ease-out; }
.nav-module-header.expanded .nav-chevron { transform: rotate(90deg); }

/* Sub-items */
.nav-sub-item {
  display: flex; align-items: center; gap: 9px;
  height: 30px; padding: 0 8px 0 22px;   /* indent 22px desde la izquierda */
  border-radius: var(--radius-md);
  font-size: 13px; color: var(--text-secondary); text-decoration: none;
  transition: background 70ms, color 70ms;
}
.nav-sub-item:hover   { background: rgba(0,0,0,0.04); color: var(--text-primary); }
.nav-sub-item.active  { background: rgba(0,0,0,0.06); color: var(--text-primary); font-weight: 500; }

/* Dot del sub-item */
.nav-sub-dot { width: 4px; height: 4px; border-radius: 9999px; background: var(--text-tertiary); }

/* Animación de apertura de submenú */
.submenu-enter-active, .submenu-leave-active {
  transition: opacity 120ms ease-out, transform 120ms ease-out;
}
.submenu-enter-from, .submenu-leave-to { opacity: 0; transform: translateY(-4px); }

/* Footer perfil */
.sidebar-footer { padding: 6px; border-top: 1px solid var(--border-subtle); flex-shrink: 0; }
```

---

## 6. ESTADO LOCAL DEL MENÚ

```javascript
// Módulos expandidos (array de UIDs)
const expandidos = ref(['terceros'])  // primero expandido por defecto

function toggleModulo(uid) {
  const idx = expandidos.value.indexOf(uid)
  if (idx === -1) expandidos.value.push(uid)
  else expandidos.value.splice(idx, 1)
}
```

El estado se guarda en memoria (se resetea al recargar). Si se necesita persistencia, usar `localStorage`.

---

## 7. AGREGAR UN NUEVO MÓDULO O SUBMENÚ

### En la BD (Hostinger):

```python
# Insertar módulo raíz
INSERT INTO sys_menu (uid, empresa, id_padre, titulo, icono, ruta_vue, orden, activo, color, usuario_creador)
VALUES ('nuevo_modulo', 'Ori_Sil_2', NULL, 'Nuevo Módulo', 'IconName', NULL, 8, 1, '#hexcolor', 'Santi');

# Insertar submenú
INSERT INTO sys_menu (uid, empresa, id_padre, titulo, icono, ruta_vue, orden, activo, usuario_creador)
VALUES ('nuevo_modulo_vista', 'Ori_Sil_2', ID_PADRE, 'Nueva Vista', 'IconName', '/nuevo/ruta', 1, 1, 'Santi');
```

### En el frontend:

1. Agregar al array `MENU` en `frontend/app/src/data/menu.js`
2. Agregar ruta en `frontend/app/src/router/routes.js`
3. Crear la página en `frontend/app/src/pages/modulo/NombrePage.vue`
4. Correr `bash frontend/deploy.sh`

---

## 8. DATOS EN ARCHIVO LOCAL (menu.js)

El menú actualmente usa datos hardcodeados en `frontend/app/src/data/menu.js` sincronizados con la BD.
**Si se modifica la BD `sys_menu`, actualizar también `menu.js`.**
En el futuro se puede conectar al API para carga dinámica.

---

## 9. DISEÑO: REGLAS INAMOVIBLES

- **Ancho**: exactamente 232px. No cambiar.
- **Módulos**: siempre uppercase, 11px, `letter-spacing: 0.07em`
- **Sub-items**: siempre indent 22px, 13px, sin uppercase
- **Dot de color**: 7px × 7px, circular, por módulo
- **Hover**: `rgba(0,0,0,0.05)` sobre fondo blanco (modo claro)
- **Activo**: `rgba(0,0,0,0.06)` + `font-weight: 500`
- **Íconos**: Lucide, 15px, sin fill (outline)
- **Transición**: `70ms ease-out` para hover, `150ms ease-out` para chevron y apertura
