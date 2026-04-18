# Inventario Fisico OS — Contexto del Subproyecto

**Creado**: 2026-03-30
**Actualizado**: 2026-04-17
**Estado**: Operativo — inventario marzo cerrado, parciales habilitados

---

## Regla crítica — Ajustes e inventario teórico

**El ajuste se calcula SIEMPRE contra la fecha de corte, NUNCA contra el stock del día de aplicación.**

- ajuste = físico_al_corte - teórico_al_corte
- Si negativo → egreso. Si positivo → ingreso.
- Se aplica en cualquier fecha posterior y el resultado es correcto.
- Los movimientos entre el corte y la aplicación NO afectan el ajuste — son operación normal.
- Un artículo negativo POST-ajuste NO significa que el ajuste fue mal hecho. Significa que hay un error de registro posterior, o que el conteo físico estuvo mal, o que hay consumos sin stock real.

## Estado actual

- **Inventario marzo 2026**: cerrado, ajustado, informe PDF generado
- **Valor inventario físico**: $15.682.482 (costo manual)
- **Ajustes aplicados**: 361 (Principal, 170 art.) + 362 (PNC, 16 art.) + 363 (corrección Almendra 55)
- **Correcciones documentadas**: 11 costos manuales, error Nibs (358→178), Almendra maquila (0→118kg)
- **Inventarios parciales**: habilitados con preselección inteligente

## Módulos implementados

1. Conteo físico (app inv.oscomunidad.com)
2. Cálculo teórico (stock - trazabilidad + materiales OPs - productos OPs)
3. Gestión de inconsistencias (dashboard + análisis IA)
4. Auditoría de OPs
5. Pestaña Costos (OsDataTable dark, valorización completa)
6. Informe PDF automático (6 secciones + anexo)
7. Observaciones en BD (automáticas + manuales)
8. Ajustes en Effi via Playwright
9. Inventarios parciales con preselección inteligente
