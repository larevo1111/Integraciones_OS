# Inventario Fisico OS — Contexto del Subproyecto

**Creado**: 2026-03-30
**Actualizado**: 2026-05-03
**Estado**: Operativo — inventario 30-abr en preparación (snapshot teórico Effi guardado) + nuevos cods cacao San Luis (593-596) + auditoría stocks negativos + depuración 94 artículos inactivos en Effi + módulo Inconsistencias/Histórico ajustes con campos nuevos (estado/snapshot/costo) + scripts artículos POST directo (anular/crear/modificar)

---

## Regla crítica — Ajustes e inventario teórico

**El ajuste se calcula SIEMPRE contra la fecha de corte, NUNCA contra el stock del día de aplicación.**

- ajuste = físico_al_corte - teórico_al_corte
- Si negativo → egreso. Si positivo → ingreso.
- Se aplica en cualquier fecha posterior y el resultado es correcto.
- Los movimientos entre el corte y la aplicación NO afectan el ajuste — son operación normal.
- Un artículo negativo POST-ajuste NO significa que el ajuste fue mal hecho. Significa que hay un error de registro posterior, o que el conteo físico estuvo mal, o que hay consumos sin stock real.

## Estado actual

- **Inventario 30 abril 2026 (en preparación)**:
  - Snapshot teórico Effi al 1-may guardado en `inventario/snapshots/inventario_2026-04-30_teorico.xlsx` (export crudo, 372 artículos vigentes, 68 columnas con stocks por 15 bodegas + costos)
  - Físico **pendiente de capturar** — debe incluir adicionales fuera del export Effi: 97.5 kg NIBS DE CACAO SL (cod 593) + 16 kg CASCARILLA DE CACAO SL (cod 594) en bodega Principal
  - Cods nuevos cacao San Luis creados 03-may (ver §Hitos abajo): 593, 594, 595, 596
- **Inventario marzo 2026**: cerrado, ajustado, informe PDF generado, análisis IA con Gemini
- **Valor inventario físico marzo**: $15.682.482 (costo manual)
- **Ajustes marzo aplicados**: 361 (Principal, 170 art.) + 362 (PNC, 16 art.) + 363 (corrección Almendra 55)
- **Correcciones documentadas**: 11 costos manuales, error Nibs (358→178), Almendra maquila (0→118kg)
- **Inventario parcial 20 abril 2026**: completado, 28→33 artículos (con esterilizados), ajustes aplicados, cero artículos negativos en Effi
- **Inventario parcial 28 abril 2026**: 120 artículos (chocobeetal, nibs, mani, bombones, granulado, envases vidrio esteril+UNICOR, almendra + 16 negativos previos + infusiones 238/497)
- **Auditoría stocks negativos 28-abr-2026**: 22 artículos analizados (18 Principal + 4 No Conformes), causa raíz documentada en `inventario/analisis_de_inventario/2026-04-28/`, ajustes Effi #369 (306 und) + #370 (56 und) — todos los negativos a 0
- **Depuración catálogo Effi 29-abr-2026**: query a `os_integracion` detectó 297 artículos vigentes sin uso desde 2025-04-29 ($4.066.140 valor inventario; 216 nunca usados). Listado en `inventario/analisis_de_inventario/2026-04-29/depuracion_articulos_inactivos.{md,csv}`. Santi marcó 94 con X en el CSV → ejecutados via `scripts/import_articulo_anular_post.py` (POST directo, NO Playwright). 94/94 anulados en Effi (reversibles vía "Reactivar"). Distribución: 64 ya etiquetados T999, 14 sin uso >1 año, 8 nunca usados, 8 con stock pero obsoletos.
- **Inventarios parciales**: operativos con preselección inteligente (`/api/inventario/sugerir-articulos`)
- **Costo**: migrado de costo_promedio a costo_manual en todo el sistema
- **App**: corre desde VPS Contabo (`inv.oscomunidad.com`), API en puerto 9600 (Producción) y 9401 (Inventario), BD `inventario_produccion_effi` en modo `direct`

## Hitos

### 2026-05-08 — Línea Mieles Urrao: cadena completa creada en Effi + recetas
4 cods nuevos creados via `scripts/import_articulo_crear_post.py` (POST directo, ~0.3s c/u). Paralelo total a las líneas SC y Carmen post-rename 2026-04-27:

| Cod | Nombre | Tipo | Categoría | Costo manual |
|---|---|---|---|---:|
| **600** | MIEL FILTRADA URRAO x KG (cruda, ya existía) | PP (2) | T01.03 (3) | $22.000 |
| **601** | MIEL FILTRADA PASTEURIZADA URRAO x KG | PP (2) | T01.03 (3) | $23.000 |
| **602** | Miel Os Urrao 150 grs | PP (2) | TPT.01 (1) | $4.589 |
| **603** | Miel Os Urrao 640 grs | PP (2) | TPT.01 (1) | $13.690 |
| **604** | Miel Os Urrao 1000 grs | PP (2) | TPT.01 (1) | $20.337 |

**3 recetas creadas en `prod_recetas`** (ids 111/112/113, estado validada, familia mieles, patrón escalable) clonando estructura de SC (ids 33/20/19), reemplazando solo material 373→601:

- 150 grs (id 111): 0.150 kg miel 601 + envase 553 + etiqueta 290 + tapa 90 + M.O. 0.03h
- 640 grs (id 112): 0.640 kg miel 601 + envase 555 + etiqueta 262 + tapa 90 + M.O. 0.03h
- 1000 grs (id 113): 1.000 kg miel 601 + envase 552 + etiqueta 263 + tapa 90 + M.O. 0.03h

Costos manuales productos finales = idénticos a SC (decisión Santi). Skill `produccion-recetas` actualizada §4.bis con la 3ra línea.

### 2026-05-03 — Cacao San Luis: cadena completa creada en Effi
4 cods nuevos creados via `scripts/import_articulo_crear_post.py` (POST directo, ~0.2s c/u). Paralelos al patrón LT (La Tierrita), tipo=2 (Producto en proceso), categoria=3 (T01.03. AGROECOLOGICOS GRAL):

| Cod | Nombre | Costo manual | Lógica |
|---|---|---|---|
| 585 | ALMENDRA DE CACAO SAN LUIS x KG | $11.000 | (ya existía, MP tipo=1) |
| **593** | NIBS DE CACAO SL x KG | $19.000 | (1.25 kg almendra × $11.000) + ~$5.250 servicios maquila |
| **594** | CASCARILLA DE CACAO SL x KG | $3.300 | $4.500 LT × (11.000/15.000) — proporcional a costo almendra |
| **595** | COBERTURA CHOCOLATE CPM 73% TEMPLADA SL x KG | $43.432 | igual LT (cobertura usa cod 319 + manteca templada, no escala con almendra cruda) |
| **596** | COBERTURA CHOCOLATE 100% TEMPLADA SL x KG | $43.432 | igual LT (mismo motivo) |

Convenciones aplicadas en nombres:
- Origen al final + unidad al final: `xxxxx SL x KG`
- Cascarilla corregida: `x KG` (no `x KL` como tenía LT por error)

**Pendientes**:
- Aparecen en `os_integracion.zeffi_inventario` tras próximo refresh pipeline (1h) o "Sync Effi" en app
- Recetas en `prod_recetas` para los nuevos PP — replicar de las LT (cod 178/80) cuando se pidan

## Módulos nuevos (2026-04-28)

### Histórico de ajustes e inconsistencias
2 tablas nuevas en VPS `inventario_produccion_effi`:

```sql
inv_analisis_inconsistencias (id, fecha, id_effi, nombre, bodega, stock_antes,
  problema, causa_raiz, evidencias_json, archivo_md, creado_por, created_at)

inv_ajustes_historico (id, analisis_id FK, fecha, id_effi, nombre, bodega,
  tipo enum(ingreso/egreso), cantidad, stock_antes, stock_despues, costo_unitario,
  op_ajuste_effi, motivo, ejecutado_por, created_at)
```

Frontend (módulo Inventarios del sidebar):
- `/inconsistencias` — listado de análisis con búsqueda
- `/inconsistencias/:id` — detalle (problema, causa raíz, ajustes asociados, contenido del .md)
- `/historico-ajustes` — tabla completa de ajustes con FK al análisis

Backend (`scripts/inventario/api.py`):
- `GET /api/inventario/inconsistencias?fecha=&cod=&bodega=&limit=`
- `GET /api/inventario/inconsistencias/{id}` (con `contenido_md` cargado)
- `GET /api/inventario/historico-ajustes?fecha=&cod=&bodega=&limit=`

Carpeta `inventario/analisis_de_inventario/<YYYY-MM-DD>/` (versionada en git):
- Un `.md` por caso con trazabilidad completa, conteos previos, causa identificada
- `RESUMEN.md` índice de la fecha

## Módulos implementados

1. Conteo físico (app inv.oscomunidad.com)
2. Cálculo teórico (stock - trazabilidad + materiales OPs - productos OPs) — soporta `--hora HH:MM:SS` para corte intra-día
3. Gestión de inconsistencias (dashboard + análisis IA)
4. Auditoría de OPs
5. Pestaña Costos (OsDataTable dark, valorización completa)
6. Informe PDF automático (6 secciones + anexo, WeasyPrint)
7. Análisis IA ejecutivo (Gemini via `/ia/simple`, genera PDF)
8. Observaciones en BD (`inv_observaciones`): automáticas + manuales (tipos: error_conteo, correccion_costo, hallazgo, manual)
9. Ajustes en Effi via Playwright — regla: siempre contra fecha de corte
10. Inventarios parciales con preselección inteligente + soporte envases esterilizados (mapeo normal→esterilizado)
11. Timezone: toda effi_data uniformizada en UTC-5 (import_all.js convierte cambios_estado)
