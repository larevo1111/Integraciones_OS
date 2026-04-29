# Inventario Fisico OS — Contexto del Subproyecto

**Creado**: 2026-03-30
**Actualizado**: 2026-04-28
**Estado**: Operativo — auditoría stocks negativos completada + módulo Inconsistencias/Histórico ajustes desplegado + apps migradas al VPS

---

## Regla crítica — Ajustes e inventario teórico

**El ajuste se calcula SIEMPRE contra la fecha de corte, NUNCA contra el stock del día de aplicación.**

- ajuste = físico_al_corte - teórico_al_corte
- Si negativo → egreso. Si positivo → ingreso.
- Se aplica en cualquier fecha posterior y el resultado es correcto.
- Los movimientos entre el corte y la aplicación NO afectan el ajuste — son operación normal.
- Un artículo negativo POST-ajuste NO significa que el ajuste fue mal hecho. Significa que hay un error de registro posterior, o que el conteo físico estuvo mal, o que hay consumos sin stock real.

## Estado actual

- **Inventario marzo 2026**: cerrado, ajustado, informe PDF generado, análisis IA con Gemini
- **Valor inventario físico marzo**: $15.682.482 (costo manual)
- **Ajustes marzo aplicados**: 361 (Principal, 170 art.) + 362 (PNC, 16 art.) + 363 (corrección Almendra 55)
- **Correcciones documentadas**: 11 costos manuales, error Nibs (358→178), Almendra maquila (0→118kg)
- **Inventario parcial 20 abril 2026**: completado, 28→33 artículos (con esterilizados), ajustes aplicados, cero artículos negativos en Effi
- **Inventario parcial 28 abril 2026**: 120 artículos (chocobeetal, nibs, mani, bombones, granulado, envases vidrio esteril+UNICOR, almendra + 16 negativos previos + infusiones 238/497)
- **Auditoría stocks negativos 28-abr-2026**: 22 artículos analizados (18 Principal + 4 No Conformes), causa raíz documentada en `analisis_de_inventario/2026-04-28/`, ajustes Effi #369 (306 und) + #370 (56 und) — todos los negativos a 0
- **Inventarios parciales**: operativos con preselección inteligente (`/api/inventario/sugerir-articulos`)
- **Costo**: migrado de costo_promedio a costo_manual en todo el sistema
- **App**: corre desde VPS Contabo (`inv.oscomunidad.com`), API en puerto 9600 (Producción) y 9401 (Inventario), BD `inventario_produccion_effi` en modo `direct`

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

Carpeta `analisis_de_inventario/<YYYY-MM-DD>/` (versionada en git):
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
