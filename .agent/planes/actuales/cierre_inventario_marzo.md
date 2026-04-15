# Plan: Cierre de Inventario Marzo 2026

**Fecha**: 2026-04-14
**Objetivo**: Cerrar el inventario físico del 31 de marzo con valorización correcta, informe para contabilidad, y dejar el sistema listo para inventarios parciales periódicos.

---

## Estado actual (verificado)

- **Conteo**: 314 artículos contados (295 Principal + 19 Productos No Conformes), 190 sin contar (no aplican)
- **Teórico**: 504 artículos con inventario teórico calculado (verificado idéntico al original)
- **Coincidencias**: 125 artículos coinciden exacto físico = teórico
- **Diferencias**: 189 artículos difieren
  - 68 sobrantes → $4.7M
  - 103 faltantes → $12.3M
  - Neto: -$7.6M (faltante)
- **Costos**: 148 artículos sin costo_promedio → valorización incompleta
- **Bodega Desarrollo**: ya en 0 (no requiere traslado)
- **11 artículos duplicados**: existen en Principal Y Productos No Conformes con teórico duplicado (se inflan diferencias)

---

## Módulo 1 — Corregir costos (pre-requisito)

**Problema**: 148 artículos en inv_conteos tienen costo_promedio = 0. La valorización actual es incorrecta.

**Acción**:
1. Actualizar inv_conteos.costo_promedio desde zeffi_inventario.costo_promedio para todos los artículos
2. Verificar que la valorización total cambie significativamente
3. Para artículos sin costo en Effi (si los hay): marcar para revisión manual

**Archivos**: `scripts/inventario/calcular_inventario_teorico.py` (agregar actualización de costos) o query directa

---

## Módulo 2 — Consolidar bodegas en reporte

**Problema**: Artículos como Miel 150g (cod 13) aparecen con físico=17 en Principal y físico=0 en PNC, pero teórico=18 en AMBOS. Eso genera -1 + -18 = -19 de diferencia cuando la real es -1 (o +17-18 combinado).

**Acción**:
1. Para el reporte, consolidar: físico = SUM(físico de todas las bodegas), teórico = valor de bodega Principal (una sola vez)
2. Recalcular diferencia consolidada
3. Decidir: ¿PNC se suma o se reporta aparte? → **Preguntar a Santi**

---

## Módulo 3 — Pestaña "Costos" en la app

**Qué tiene hoy**: La pantalla de gestión muestra inconsistencias pero con valores truncados ("25k").

**Qué necesita**:
- Nueva pestaña/vista "Costos" o "Valorización" en la app de inventario
- Tabla con: artículo, físico, teórico, diferencia, costo unitario, valor diferencia ($)
- Totales: sobrante total, faltante total, neto
- Filtros: por categoría, por rango de diferencia, solo faltantes/sobrantes
- Formato de pesos completo (no abreviado): $1.529.841 en vez de $1.5M

**Archivos**: `inventario/frontend/src/App.vue`, posiblemente endpoint nuevo en `scripts/inventario/api.py`

---

## Módulo 4 — Informe PDF

**Dos fases**:

### Fase A: Informe manual (Claude analiza y genera)
- Analizar TODAS las inconsistencias
- Clasificar por tipo: faltante real, error de conteo probable, producto en tránsito, producto no conforme
- Identificar patrones (ej: todos los chocolates 73% sin empacar faltan → ¿están empacados ya?)
- Generar PDF con:
  - Resumen ejecutivo (1 página)
  - Valorización por categoría
  - Top 20 diferencias con análisis
  - Recomendación: qué ajustar, qué recontar
  - Decisión del director: aceptar como nueva línea base

### Fase B: Generación automática (futuro)
- Endpoint que genere PDF automáticamente
- Usar librería Python (reportlab o weasyprint)
- Plantilla con logo OS, fecha, firmas

---

## Módulo 5 — Ajustes en Effi (post-informe)

**Objetivo**: Una vez Santi apruebe el informe, generar los ajustes de inventario en Effi para que el stock del sistema coincida con el físico.

**Proceso**:
1. Generar plantilla de ajuste (Excel compatible con importación Effi)
2. Ajuste de salida para faltantes
3. Ajuste de entrada para sobrantes
4. Validar en Effi que el stock quede igual al conteo físico
5. Esto ya lo tenemos parcialmente implementado con Playwright

**Dependencia**: Aprobación de Santi sobre qué diferencias aceptar

---

## Módulo 6 — Inventarios parciales periódicos

**Objetivo**: No volver a pasar meses sin inventario. Sistema de conteos cíclicos.

**Propuesta**:
- Inventario parcial semanal: rotación por categoría (ej: semana 1 = mieles, semana 2 = chocolates...)
- O por método ABC: artículos A (alto valor) cada 2 semanas, B cada mes, C cada 2 meses
- La app ya soporta crear inventarios nuevos con fecha y selección de artículos
- Agregar: programación automática, notificación por Telegram cuando toca contar

**Decisión pendiente**: ¿Rotación por categoría o por ABC? → **Preguntar a Santi**

---

## Orden de ejecución

```
1. Corregir costos (10 min) ← PRIMERO
2. Consolidar bodegas duplicadas (20 min)
3. Análisis completo de inconsistencias → Informe PDF manual (1-2 horas)
4. Pestaña Costos en la app (30 min)
5. → Santi revisa informe → decide qué ajustar
6. Ajustes en Effi (con Playwright)
7. Diseñar inventarios parciales periódicos
```

---

## Preguntas para Santi antes de ejecutar

1. **Productos No Conformes**: ¿se suman al conteo de Principal o se reportan aparte?
2. **Los 190 artículos sin contar** (bodega "—"): ¿son artículos que realmente no están en bodega física? ¿Se ignoran?
3. **Inventarios parciales**: ¿preferencia por rotación por categoría o por valor (ABC)?
4. **¿Quién firma el informe?** ¿Solo Santi o también alguien de contabilidad?
