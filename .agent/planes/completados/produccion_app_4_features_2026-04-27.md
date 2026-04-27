# Plan — Producción OS app: 4 features (2026-04-27)

## Contexto
Inv.oscomunidad.com sirve la app `produccion/` (React + Vite + Shadcn). Backend FastAPI en puerto 9600 (`scripts/produccion/api.py`). Santi pidió 4 mejoras post-renombrado del catálogo de mieles.

## Decisión arquitectónica clave
**Grupos de productos viven en `effi_data.catalogo_articulos.grupo_producto`** — misma tabla que consume `menu.oscomunidad.com`. NO crear tabla nueva de grupos.

## Fases (en orden de ejecución)

### Fase 0 — Limpieza grupos catálogo
- UPDATE en `effi_data.catalogo_articulos`:
  - `Miel Os Vidrio` → `Miel Os San Carlos`
  - `Miel OS Carmen Cristalizada` → `Miel OS Carmen`
- Re-sync a `os_integracion` VPS

### Fase 4 — Sync Effi expandido
- Backend `POST /api/refresh-effi` orquesta: export+import de inventario, produccion_encabezados, articulos_producidos, materiales_produccion, otros_costos_produccion + sync VPS
- Frontend [inventarios-layout.jsx:316](produccion/src/pages/inventarios-layout.jsx#L316) usa el nuevo endpoint con progress

### Fase 2 — Botón único Programar
- Renombrar `"Programar juntas"` → `"Programar"` en [solicitudes.jsx:148](produccion/src/pages/solicitudes.jsx#L148)
- `disabled={selectedIds.length < 1}` (antes `< 2`)
- Backend `/api/produccion/compatibilidad` permitir 1 sola solicitud

### Fase 1 — Selección por grupo en nueva solicitud
- Backend: `GET /api/articulos/grupos`, `GET /api/articulos/grupos/{nombre}`
- Frontend [nueva-solicitud-sheet.jsx]: toggle "Por producto / Por grupo"

### Fase 3 — Preview editable de OP al programar
- Backend: `POST /api/produccion/preview-op` → estructura completa OP basada en `prod_recetas` + `zeffi_inventario` actual
- Frontend [programar-grupo-dialog.jsx]: 3 tablas editables (materiales, productos, costos) + botón "Crear OP en Effi"

## Tests obligatorios cada fase
- Web (1280×800) + móvil (375×812) con Chrome DevTools MCP
- API endpoints con curl

## Estado actual
- Fase 0: en progreso
- Demás: pendientes
