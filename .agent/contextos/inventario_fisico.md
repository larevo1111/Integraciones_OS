# Inventario Fisico OS — Contexto del Subproyecto

**Creado**: 2026-03-30
**Actualizado**: 2026-04-20
**Estado**: Operativo — inventario marzo cerrado + parcial abril completado

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
- **Inventarios parciales**: operativos con preselección inteligente (`/api/inventario/sugerir-articulos`)
- **Costo**: migrado de costo_promedio a costo_manual en todo el sistema

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
