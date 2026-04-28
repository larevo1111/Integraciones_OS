# Auditoría de inventarios negativos — 2026-04-28

## Objetivo
Identificar TODOS los artículos vigentes con stock negativo en alguna bodega de Effi, analizar la causa raíz por artículo+bodega, llevar cada negativo a 0 mediante ajuste de Effi, y dejar registro persistente del análisis y los ajustes hechos.

## Reglas
- Análisis y ajustes son **por bodega**, no global. Un cod puede tener -80 en bodega A y +90 en B; el total da +10 pero el inventario está mal. Tratar cada bodega como caso independiente.
- El análisis debe contemplar: si el artículo está mal codificado, si figura en una bodega pero se saca de otra, si hay OPs sin registrar, ajustes mal cargados, traslados fantasma, etc.
- Todo ajuste y análisis queda en BD para histórico consultable, además del .md detallado en disco.

## Fase 0 — Infraestructura
1. Carpeta `analisis_de_inventario/2026-04-28/` (versionada en git).
2. Tabla `inv_analisis_inconsistencias` en VPS `inventario_produccion_effi`:
   - `id, fecha, id_effi, nombre, bodega, stock_antes, problema, causa_raiz, evidencias_json, archivo_md, created_at`
3. Tabla `inv_ajustes_historico` en VPS:
   - `id, analisis_id (FK), fecha, id_effi, bodega, tipo (ingreso/egreso), cantidad, stock_antes, stock_despues, op_ajuste_effi, motivo, ejecutado_por, created_at`

## Fase 1 — Detección
Query a `zeffi_inventario` para listar todos los `(cod, bodega)` con stock < 0. Listar las ~14 columnas `stock_bodega_*_sucursal_principal`.

## Fase 2 — Análisis profundo
Por cada `(cod, bodega)` con negativo:
1. Sacar trazabilidad completa (`zeffi_trazabilidad WHERE id_articulo=X AND bodega=Y`).
2. Buscar conteos físicos previos (`inv_conteos`) y auditorías (`inv_auditorias`).
3. Detectar patrones:
   - Ajuste mal cargado (teórico inflado vs trazabilidad real)
   - Traslado en una dirección sin contraparte
   - OP que consumió de bodega equivocada
   - Sobreconsumo (egreso mayor al stock)
4. Escribir `analisis_de_inventario/2026-04-28/<cod>_<slug>_<bodega>.md` con:
   - Encabezado: cod, nombre, bodega, stock actual
   - Cronología completa
   - Causa raíz identificada
   - Recomendación / ajuste a aplicar
5. Insertar fila en `inv_analisis_inconsistencias`.

## Fase 3 — Ajustes en Effi
Por cada negativo, generar ajuste de **Ingreso** (cantidad = |stock|) en la bodega correspondiente.
- Excel + `import_ajuste_inventario.js` con observación que linkea al .md del análisis.
- Insertar fila en `inv_ajustes_historico` con FK al análisis.
- Refresh Effi al final para verificar.

## Fase 4 — Frontend
Sub-páginas en módulo Inventario (Producción app):
- `/inventarios/historico-ajustes` — tabla con filtros fecha/cod/bodega
- `/inventarios/inconsistencias` — listado de análisis, click abre el .md

## Tareas para Subagentes
- Posible: 1 subagente que analice los ~10-20 negativos en paralelo (cada uno escribe su .md).

## Tareas para Antigravity
- Ninguna en esta tarea.

## Estado
- Iniciado 2026-04-28
